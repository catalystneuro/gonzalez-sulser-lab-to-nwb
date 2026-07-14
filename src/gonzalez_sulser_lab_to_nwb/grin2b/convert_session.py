"""Convert a single GRIN2B baseline session (BL1 or BL2) to NWB.

Usage
-----
From the command line (after installing the package):

    python -m gonzalez_sulser_lab_to_nwb.grin2b.convert_session \\
        --data-dir "H:/Gonzalez-Sulser-CN-data-share" \\
        --output-dir "/path/to/nwb_output" \\
        --animal-id 129 \\
        --baseline BL1 \\
        [--stub-test]

Or call session_to_nwb() directly from Python.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import openpyxl
import yaml
from neuroconv.utils import dict_deep_update, load_dict_from_file
from pynwb import NWBFile

from gonzalez_sulser_lab_to_nwb.grin2b.grin2bnwbconverter import Grin2bNWBConverter

# Edinburgh timezone (UTC+0 / BST UTC+1 depending on DST)
_TZ = ZoneInfo("Europe/London")

# Paths relative to the data share root
_EEG_DIR = "Chronic EEG recordings"
_SLEEP_DIR = "Sleep state classifications"
_SEIZURE_DIR = "Seizure timestamps"
_WINDOWS_XLSX = "Light cycle timing metadata/Sample_start_end_GRIN2B.xlsx"

_FS = 250.4  # Hz, confirmed by inspection


def _load_bl_windows(data_dir: Path) -> dict[tuple[int, str], dict]:
    """Parse Sample_start_end_GRIN2B.xlsx → {(animal_id, baseline): {file, start, end}}."""
    wb = openpyxl.load_workbook(
        data_dir / _WINDOWS_XLSX, read_only=True, data_only=True
    )
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    windows = {}
    for row in rows[1:]:
        if row[0] is None:
            continue
        d = dict(zip(header, row))
        key = (int(d["Animal ID"]), str(d["Baseline"]))
        windows[key] = {
            "file": d["File"],
            "start": int(d["Start"]),
            "end": int(d["End"]),
        }
    return windows


_LIGHTS_ON_HOUR = 7  # Zeitgeber time 07:00 ("lights-on"), confirmed by the lab.


def _compute_session_start_time(
    dat_filename: str, windows: dict[tuple[int, str], dict], animal_id: int
) -> datetime:
    """Compute the absolute timestamp of sample 0 of the .dat file.

    Filename pattern: TAINI_<dev>_<band>_<line>_<id>_<cond>-<YYYY_MM_DD>-0000.dat
    The filename date is the recording start date.
    BL1 always starts at Zeitgeber time 07:00 (lights-on)
    the day after the animal was connected — i.e. the day after the filename
    date. session_start_time (sample 0) is therefore back-computed from that
    anchor using BL1's sample offset for this animal:

        session_start_time = (filename_date + 1 day, 07:00) - bl1_start_sample / fs

    Any other baseline window (e.g. BL2) for the same animal shares this same
    session_start_time, since it is the same .dat file / same clock — its own
    BL sample offset (added elsewhere via starting_time / t_start annotations)
    lands on the correct absolute time automatically.
    """
    import re

    m = re.search(r"-(\d{4})_(\d{2})_(\d{2})-", dat_filename)
    if not m:
        raise ValueError(f"Cannot parse date from filename: {dat_filename}")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    recording_date = datetime(y, mo, d, tzinfo=_TZ)

    bl1_window = windows.get((animal_id, "BL1"))
    if bl1_window is None:
        # No BL1 window for this animal (single-baseline session) — the 07:00
        # anchor can't be back-computed, so fall back to midnight of the
        # recording date (time-of-day unknown for this animal).
        return recording_date

    lights_on = (recording_date + timedelta(days=1)).replace(
        hour=_LIGHTS_ON_HOUR, minute=0, second=0
    )
    bl1_start_s = bl1_window["start"] / _FS
    return lights_on - timedelta(seconds=bl1_start_s)


def session_to_nwb(
    data_dir: str | Path,
    output_dir: str | Path,
    animal_id: int,
    baseline: Literal["BL1", "BL2"],
    stub_test: bool = False,
) -> Path:
    """Convert one baseline session for one animal to NWB.

    Parameters
    ----------
    data_dir : str or Path
        Root of the Gonzalez-Sulser data share (contains "Chronic EEG recordings/", etc.)
    output_dir : str or Path
        Directory where the .nwb file will be written.
    animal_id : int
        Animal ID number (e.g. 129 for GRIN2B_129).
    baseline : "BL1" or "BL2"
        Which 24-hour baseline window to convert.
    stub_test : bool
        If True, convert only a small data slice to validate the pipeline.

    Returns
    -------
    Path
        Path to the written NWB file.
    """

    subject_id = f"GRIN2B_{animal_id}"
    session_id = f"{baseline}"

    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    if stub_test:
        output_dir = output_dir / "nwb_stub"
    output_dir = output_dir / subject_id
    output_dir.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir / f"{session_id}.nwb"

    # ---- Look up BL window ----
    windows = _load_bl_windows(data_dir)
    key = (animal_id, baseline)
    if key not in windows:
        raise KeyError(
            f"No BL window found for animal {animal_id} {baseline} in "
            f"{_WINDOWS_XLSX}. Check xlsx for this animal."
        )
    win = windows[key]
    dat_filename = win["file"]
    bl_start_sample = win["start"]
    bl_stop_sample = win["end"]

    # ---- Resolve file paths ----
    dat_path = data_dir / _EEG_DIR / dat_filename
    if not dat_path.exists():
        raise FileNotFoundError(
            f"Raw .dat file not found: {dat_path}\n"
            f"Only 21 of 37 animals' .dat files are in the current share. "
            f"Contact lab to obtain missing files."
        )

    subject_dir = data_dir / _SLEEP_DIR / subject_id
    sleep_csv = subject_dir / f"{subject_id}_{baseline}-dge_ok.csv"
    seizure_csv = data_dir / _SEIZURE_DIR / f"{subject_id}_{baseline}_Seizures.csv"
    swd_csv = subject_dir / "seiz" / f"{subject_id}_{baseline}_DGE_SWDs.csv"
    totals_csv = subject_dir / "seiz" / f"{subject_id}_{baseline}_Seiz_Totals.csv"
    psd_csv = subject_dir / f"{subject_id}_{baseline}-pw_spectrum.csv"

    # ---- Build source_data ----
    source_data: dict = {}
    conversion_options: dict = {}

    source_data["EEGRecording"] = dict(
        file_path=str(dat_path),
        bl_start_sample=bl_start_sample,
        bl_stop_sample=bl_stop_sample,
        signal_type="EEG",
        baseline_name=baseline,
    )
    conversion_options["EEGRecording"] = dict(stub_test=stub_test)

    source_data["EMGRecording"] = dict(
        file_path=str(dat_path),
        bl_start_sample=bl_start_sample,
        bl_stop_sample=bl_stop_sample,
        signal_type="EMG",
        baseline_name=baseline,
    )
    conversion_options["EMGRecording"] = dict(stub_test=stub_test)

    if sleep_csv.exists():
        source_data["SleepStates"] = dict(
            file_path=str(sleep_csv),
            bl_start_sample=bl_start_sample,
        )
        conversion_options["SleepStates"] = dict(stub_test=stub_test)

    if seizure_csv.exists():
        source_data["Seizures"] = dict(
            file_path=str(seizure_csv),
            bl_start_sample=bl_start_sample,
        )
        conversion_options["Seizures"] = dict(stub_test=stub_test)

    if swd_csv.exists():
        source_data["SwdCounts"] = dict(
            file_path=str(swd_csv),
            bl_start_sample=bl_start_sample,
        )
        conversion_options["SwdCounts"] = dict(stub_test=stub_test)

    if totals_csv.exists():
        source_data["SeizureTotals"] = dict(file_path=str(totals_csv))
        conversion_options["SeizureTotals"] = dict(stub_test=stub_test)

    if psd_csv.exists():
        source_data["StatePowerSpectrum"] = dict(file_path=str(psd_csv))
        conversion_options["StatePowerSpectrum"] = dict(stub_test=stub_test)

    # ---- Converter ----
    converter = Grin2bNWBConverter(source_data=source_data)

    # ---- Metadata ----
    metadata = converter.get_metadata()

    general_yaml = Path(__file__).parent / "metadata" / "grin2b_general_metadata.yaml"
    editable_metadata = load_dict_from_file(general_yaml)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Session-specific fields
    session_start_time = _compute_session_start_time(dat_filename, windows, animal_id)
    metadata["NWBFile"]["session_start_time"] = session_start_time
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_description"] = (
        f"Chronic wireless EEG/EMG recording, subject {subject_id}, {baseline} window "
        f"(24 h starting ~{bl_start_sample / _FS / 3600:.1f} h into the raw recording). "
        f"Raw .dat file: {dat_filename}."
    )

    # Subject metadata
    subjects_yaml = Path(__file__).parent / "metadata" / "grin2b_subjects_metadata.yaml"
    with open(subjects_yaml) as f:
        all_subjects = yaml.safe_load(f)

    subj_meta = all_subjects.get(subject_id, {})
    metadata.setdefault("Subject", {})
    metadata["Subject"].update(
        {k: v for k, v in subj_meta.items() if not str(v).startswith("TODO")}
    )
    metadata["Subject"]["subject_id"] = subject_id
    # Ensure required fields are always set (NWB schema requires subject_id, sex, species)
    metadata["Subject"].setdefault("species", "Rattus norvegicus")
    metadata["Subject"].setdefault(
        "sex", "U"
    )  # Unknown until lab provides per-animal table

    # ---- Run conversion ----
    converter.run_conversion(
        nwbfile_path=str(nwbfile_path),
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=True,
    )

    print(f"Wrote: {nwbfile_path}")
    return nwbfile_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(
    #     description="Convert one GRIN2B baseline session to NWB."
    # )
    # parser.add_argument("--data-dir", required=True, help="Root of the data share.")
    # parser.add_argument("--output-dir", required=True, help="Directory for NWB output.")
    # parser.add_argument(
    #     "--animal-id", type=int, required=True, help="Animal ID (e.g. 129)."
    # )
    # parser.add_argument(
    #     "--baseline", choices=["BL1", "BL2"], required=True, help="Baseline window."
    # )
    # parser.add_argument(
    #     "--stub-test", action="store_true", help="Convert small stub only."
    # )
    # args = parser.parse_args()

    session_to_nwb(
        data_dir="H:/Gonzalez-Sulser-CN-data-share",  # args.data_dir,
        output_dir="H:/gonzalez-nwbfiles",  # args.output_dir,
        animal_id=129,  # args.animal_id,
        baseline="BL1",
        stub_test=False,
    )

    session_to_nwb(
        data_dir="H:/Gonzalez-Sulser-CN-data-share",  # args.data_dir,
        output_dir="H:/gonzalez-nwbfiles",  # args.output_dir,
        animal_id=129,  # args.animal_id,
        baseline="BL2",
        stub_test=False,
    )
