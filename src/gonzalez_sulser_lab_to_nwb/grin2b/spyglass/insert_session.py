"""Insert all already-converted GRIN2B NWB files into Spyglass, unmodified.

Targets the draft common_eeg/ImportedEEG schema (LorenFrankLab/spyglass PR #1638,
branch feature/eeg-ingestion). Per the empirical dry run (2026-09-11, see
dry_run_insertion.py / plan Part 6.2), the gap for this schema is effectively zero:
insert_sessions() + ImportedEEG.populate() succeed on the DANDI:001888 files exactly
as published -- no NWB transformation step is needed.

Run inside the `spyglass-eeg` conda env (installs spyglass from the PR branch):

    conda activate spyglass-eeg
    cd /mnt/c/Users/algab/CatalystNeuro/gonzalez-sulser-lab-to-nwb/spyglass
    python insert_session.py                  # all subjects in the raw dir
    python insert_session.py sub-GRIN2B-129    # one subject (matches by substring)
"""

import sys
import traceback
from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")

dj.config.load(str(CONF))  # BEFORE any spyglass import
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_eeg import ImportedEEG  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

RAW_DIR = Path(raw_dir)


def discover_nwb_files(filter_substr: str = "") -> list[Path]:
    """Original (non-copy) NWB files in the Spyglass raw dir, sorted.

    Excludes Spyglass's own "<stem>_.nwb" link-copies, which live in the same
    raw dir and would otherwise be double-counted.
    """
    files = sorted(
        p
        for p in RAW_DIR.glob("*.nwb")
        if not p.stem.endswith("_") and filter_substr in p.name
    )
    return files


def clean_db_entry(nwb_file_name: str) -> None:
    """Remove all Spyglass entries for a session so re-insertion is idempotent."""
    copy_name = get_nwb_copy_filename(nwb_file_name)
    entry = sgc.Nwbfile() & {"nwb_file_name": copy_name}
    if entry:
        entry.delete(safemode=False)


def insert_one(nwbfile_path: Path) -> dict:
    """Insert one NWB file and populate ImportedEEG. Returns a status dict."""
    nwb_file_name = nwbfile_path.name
    copy_name = get_nwb_copy_filename(nwb_file_name)
    copy_dict = {"nwb_file_name": copy_name}

    clean_db_entry(nwb_file_name)

    sgi.insert_sessions(str(nwbfile_path), rollback_on_fail=True, raise_err=True)

    if not (sgc.Session() & copy_dict):
        raise RuntimeError(
            f"Session was not populated for {copy_name}. Nwbfile entry may exist "
            "from a previous failed run without a matching Session row."
        )

    ImportedEEG.populate(copy_dict)

    return {
        "session": nwb_file_name,
        "electrode_group": len(sgc.ElectrodeGroup() & copy_dict),
        "electrode": len(sgc.Electrode() & copy_dict),
        "imported_eeg": len(ImportedEEG() & copy_dict),
        "imported_eeg_electrode": len(ImportedEEG.Electrode() & copy_dict),
        "data_acquisition_device": len(sgc.DataAcquisitionDevice() & copy_dict),
    }


def main() -> None:
    filter_substr = sys.argv[1] if len(sys.argv) > 1 else ""
    nwb_files = discover_nwb_files(filter_substr)
    if not nwb_files:
        print(f"No NWB files found in {RAW_DIR} matching {filter_substr!r}")
        return

    print(f"Found {len(nwb_files)} subject(s) to insert:")
    for f in nwb_files:
        print(f"  {f.name}")

    results = []
    failures = []
    for nwbfile_path in nwb_files:
        print(f"\n{'=' * 70}\n{nwbfile_path.name}\n{'=' * 70}")
        try:
            result = insert_one(nwbfile_path)
            results.append(result)
            print(f"OK: {result}")
        except Exception as exc:  # noqa: BLE001 -- record and keep going, like convert_all_sessions.py
            failures.append((nwbfile_path.name, exc))
            print(f"FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    print(f"\n{'=' * 70}\nSUMMARY: {len(results)}/{len(nwb_files)} inserted\n{'=' * 70}")
    for r in results:
        print(
            f"  {r['session']}: ElectrodeGroup={r['electrode_group']} "
            f"Electrode={r['electrode']} ImportedEEG={r['imported_eeg']} "
            f"ImportedEEG.Electrode={r['imported_eeg_electrode']} "
            f"DataAcquisitionDevice={r['data_acquisition_device']}"
        )
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for name, exc in failures:
            print(f"  {name}: {type(exc).__name__}: {exc}")

    report_path = Path(__file__).parent / "insertion_report.txt"
    with open(report_path, "w") as f:
        f.write(f"{len(results)}/{len(nwb_files)} inserted\n\n")
        for r in results:
            f.write(f"{r}\n")
        if failures:
            f.write(f"\n{len(failures)} failure(s):\n")
            for name, exc in failures:
                f.write(f"  {name}: {type(exc).__name__}: {exc}\n")
    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
