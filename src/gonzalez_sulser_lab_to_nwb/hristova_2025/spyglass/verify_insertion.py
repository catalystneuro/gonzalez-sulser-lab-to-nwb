"""Verify Spyglass database entries against the source NWB files for all
inserted GRIN2B subjects: table row counts + a data-integrity read-back
(first N samples of ImportedEEG series vs. the same slice read directly from
the NWB file).

Run inside the `spyglass-eeg` conda env:

    conda activate spyglass-eeg
    cd /mnt/c/Users/algab/CatalystNeuro/gonzalez-sulser-lab-to-nwb/spyglass
    python verify_insertion.py
"""

from pathlib import Path

import numpy as np
import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")

dj.config.load(str(CONF))
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
from spyglass.common.common_eeg import ImportedEEG  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402
from pynwb import NWBHDF5IO  # noqa: E402

RAW_DIR = Path(raw_dir)
N_CHECK = 1000  # samples to compare per series -- cheap, no need to load full arrays


def log_table(table, restriction=True) -> str:
    return f"=== {table.__name__} ===\n{table & restriction}\n"


def print_tables(nwb_file_name: str) -> str:
    copy_dict = {"nwb_file_name": get_nwb_copy_filename(nwb_file_name)}
    sections = [
        log_table(sgc.Nwbfile, copy_dict),
        log_table(sgc.Session, copy_dict),
        log_table(sgc.DataAcquisitionDevice, copy_dict),
        log_table(sgc.ElectrodeGroup, copy_dict),
        log_table(sgc.Electrode, copy_dict),
        log_table(ImportedEEG, copy_dict),
        log_table(ImportedEEG.Electrode, copy_dict),
        log_table(sgc.IntervalList, copy_dict),
    ]
    return "\n".join(sections)


def validate_data_integrity(nwbfile_path: Path) -> list[str]:
    """Compare the first N_CHECK samples of each ImportedEEG series against a
    direct read of the source NWB file. Returns a list of PASS/FAIL messages.
    """
    nwb_file_name = nwbfile_path.name
    copy_dict = {"nwb_file_name": get_nwb_copy_filename(nwb_file_name)}
    messages = []

    with NWBHDF5IO(str(nwbfile_path), "r") as io:
        nwbfile = io.read()
        for row in (ImportedEEG() & copy_dict).fetch(as_dict=True):
            series_name = row["name"]
            spyglass_series = ImportedEEG().nwb_object(
                {"nwb_file_name": copy_dict["nwb_file_name"], "eeg_object_id": row["eeg_object_id"]}
            )
            source_series = nwbfile.acquisition[series_name]
            spyglass_data = np.asarray(spyglass_series.data[:N_CHECK])
            source_data = np.asarray(source_series.data[:N_CHECK])
            try:
                np.testing.assert_array_equal(spyglass_data, source_data)
                messages.append(f"  {series_name}: PASS ({spyglass_data.shape})")
            except AssertionError as exc:
                messages.append(f"  {series_name}: FAIL -- {exc}")
    return messages


def main() -> None:
    nwb_files = sorted(
        p for p in RAW_DIR.glob("*.nwb") if not p.stem.endswith("_")
    )
    print(f"Verifying {len(nwb_files)} subject(s)\n")

    tables_out = []
    all_messages = []
    for nwbfile_path in nwb_files:
        print(f"--- {nwbfile_path.name} ---")
        tables_out.append(f"##### {nwbfile_path.name} #####\n")
        tables_out.append(print_tables(nwbfile_path.name))
        messages = validate_data_integrity(nwbfile_path)
        for m in messages:
            print(m)
        all_messages.extend([f"{nwbfile_path.name}{m}" for m in messages])

    (Path(__file__).parent / "tables.txt").write_text("\n".join(tables_out))

    n_fail = sum(1 for m in all_messages if "FAIL" in m)
    print(f"\n{'=' * 70}\nIntegrity check: {len(all_messages) - n_fail}/{len(all_messages)} series PASS")
    if n_fail:
        print(f"{n_fail} FAILURE(S):")
        for m in all_messages:
            if "FAIL" in m:
                print(f"  {m}")
    print(f"{'=' * 70}\nTables written to tables.txt")


if __name__ == "__main__":
    main()
