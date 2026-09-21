"""Empirical dry run (plan Part 6.2): insert an UNMODIFIED, already-converted GRIN2B
NWB file and see exactly what succeeds/fails against the draft common_eeg/ImportedEEG
schema (LorenFrankLab/spyglass PR #1638, branch feature/eeg-ingestion).

This deliberately does NOT change the NWB file first — the whole point is to observe
real behavior instead of guessing from source reading. Run inside the `spyglass-eeg`
WSL env (installs spyglass from the PR branch; the plain `spyglass` env stays on the
verified PyPI release as a fallback).

    conda activate spyglass-eeg
    cd /mnt/c/Users/algab/CatalystNeuro/gonzalez-sulser-lab-to-nwb/spyglass
    python dry_run_insertion.py
"""

from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")
NWB_FILE_NAME = "sub-GRIN2B-129_ses-2021-03-26_ecephys.nwb"

dj.config.load(str(CONF))  # BEFORE any spyglass import
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_eeg import ImportedEEG  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    nwbfile_path = Path(raw_dir) / NWB_FILE_NAME
    if not nwbfile_path.exists():
        raise FileNotFoundError(f"Expected NWB file at {nwbfile_path}")

    nwb_dict = {"nwb_file_name": NWB_FILE_NAME}
    copy_name = get_nwb_copy_filename(NWB_FILE_NAME)
    copy_dict = {"nwb_file_name": copy_name}

    # Clean up any partial run from before. Nwbfile is keyed on the COPY filename
    # (stem + "_.nwb"), not the original -- using the original name here silently
    # matches nothing, insert_sessions() then warns "already in Nwbfile table" and
    # skips, leaving Session at 0 rows with no error (a documented Spyglass gotcha).
    entry = sgc.Nwbfile() & copy_dict
    if entry:
        section("Cleaning up existing Nwbfile entry from a previous run")
        entry.delete(safemode=False)

    section("STEP 1: sgi.insert_sessions() -- UNMODIFIED file, as-is")
    try:
        sgi.insert_sessions(str(nwbfile_path), rollback_on_fail=True, raise_err=True)
        print("insert_sessions() completed with no exception.")
    except Exception as exc:  # noqa: BLE001 -- we want to see and report everything
        print(f"insert_sessions() RAISED: {type(exc).__name__}: {exc}")

    section("STEP 2: what actually populated")
    for table in (
        sgc.Nwbfile,
        sgc.Session,
        sgc.DataAcquisitionDevice,
        sgc.ElectrodeGroup,
        sgc.Electrode,
        sgc.IntervalList,
    ):
        rows = table() & copy_dict
        print(f"{table.__name__:<24} {len(rows)} row(s)")

    session_exists = bool(sgc.Session() & copy_dict)
    if not session_exists:
        print("\nSession did not populate -- stopping before ImportedEEG.")
        return

    section("STEP 3: explicitly populate ImportedEEG")
    try:
        ImportedEEG.populate(copy_dict)
        print("ImportedEEG.populate() completed with no exception.")
    except Exception as exc:  # noqa: BLE001
        print(f"ImportedEEG.populate() RAISED: {type(exc).__name__}: {exc}")

    eeg_rows = ImportedEEG() & copy_dict
    eeg_elec_rows = ImportedEEG.Electrode() & copy_dict
    print(f"\nImportedEEG            {len(eeg_rows)} row(s)")
    print(f"ImportedEEG.Electrode   {len(eeg_elec_rows)} row(s)")
    if eeg_rows:
        print("\nImportedEEG rows:")
        print(eeg_rows)

    if eeg_rows:
        section("STEP 4: read-back sanity check via fetch_nwb()")
        for row in eeg_rows.fetch(as_dict=True):
            series = ImportedEEG().nwb_object(
                {"nwb_file_name": copy_name, "eeg_object_id": row["eeg_object_id"]}
            )
            print(
                f"  {row['name']!r}: shape={series.data.shape}, "
                f"rate={series.rate}, unit={series.unit}"
            )

    section("DRY RUN DONE")


if __name__ == "__main__":
    main()
