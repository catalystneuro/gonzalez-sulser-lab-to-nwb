"""Convert one GRIN2B subject to NWB (one file per subject).

The output NWB file contains the subject's *full* raw EEG/EMG recording,
with the BL1 and BL2 baseline windows marked in the NWB epochs table rather
than split across separate files. Sleep/seizure/SWD/power-spectrum streams
are written once per available baseline window, each named with a
`_baseline_window_1` / `_baseline_window_2` suffix so both baselines coexist
in the same file's processing["behavior"] / processing["ecephys"] modules.

Usage
-----
From the command line (after installing the package):

    python -m gonzalez_sulser_lab_to_nwb.grin2b.convert_session \\
        --data-dir "H:/Gonzalez-Sulser-CN-data-share" \\
        --output-dir "/path/to/nwb_output" \\
        --animal-id 129 \\
        [--stub-test]

Or call session_to_nwb() directly from Python.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
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

# (baseline key in xlsx/filenames, NWB object-name suffix)
_BASELINE_LABELS = {"BL1": "baseline_window_1", "BL2": "baseline_window_2"}


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


def _parse_dat_date(dat_filename: str) -> datetime:
    """Extract the recording start date from a .dat filename (midnight, Edinburgh time).

    Filename pattern: TAINI_<dev>_<band>_<line>_<id>_<cond>-<YYYY_MM_DD>-0000.dat
    """
    m = re.search(r"-(\d{4})_(\d{2})_(\d{2})-", dat_filename)
    if not m:
        raise ValueError(f"Cannot parse date from filename: {dat_filename}")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(y, mo, d, tzinfo=_TZ)


def _compute_session_start_time(
    dat_filename: str, windows: dict[tuple[int, str], dict], animal_id: int
) -> datetime:
    """Compute the absolute timestamp of sample 0 of the .dat file.

    The filename date is the recording start date.
    BL1 always starts at Zeitgeber time 07:00 (lights-on)
    the day after the animal was connected — i.e. the day after the filename
    date. session_start_time (sample 0) is therefore back-computed from that
    anchor using BL1's sample offset for this animal:

        session_start_time = (filename_date + 1 day, 07:00) - bl1_start_sample / fs

    BL2 (and the full raw recording written by TainiRecordingInterface) share
    this same session_start_time, since it is the same .dat file / same clock
    — BL2's own sample offset lands on the correct absolute time automatically.
    """
    recording_date = _parse_dat_date(dat_filename)

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
    stub_test: bool = False,
) -> Path:
    """Convert one GRIN2B subject to NWB.

    Parameters
    ----------
    data_dir : str or Path
        Root of the Gonzalez-Sulser data share (contains "Chronic EEG recordings/", etc.)
    output_dir : str or Path
        Directory where the .nwb file will be written.
    animal_id : int
        Animal ID number (e.g. 129 for GRIN2B_129).
    stub_test : bool
        If True, convert only a small data slice to validate the pipeline.

    Returns
    -------
    Path
        Path to the written NWB file.
    """

    # ---- Look up BL windows (an animal may have BL1, BL2, or both) ----
    data_dir = Path(data_dir)
    windows = _load_bl_windows(data_dir)
    bl1_window = windows.get((animal_id, "BL1"))
    bl2_window = windows.get((animal_id, "BL2"))
    if bl1_window is None and bl2_window is None:
        raise KeyError(
            f"No BL1 or BL2 window found for animal {animal_id} in "
            f"{_WINDOWS_XLSX}. Check xlsx for this animal."
        )

    baseline_windows = {"BL1": bl1_window, "BL2": bl2_window}
    dat_filename = (bl1_window or bl2_window)["file"]

    # ---- Resolve file paths ----
    dat_path = data_dir / _EEG_DIR / dat_filename
    if not dat_path.exists():
        raise FileNotFoundError(
            f"Raw .dat file not found: {dat_path}\n"
            f"Only 21 of 37 animals' .dat files are in the current share. "
            f"Contact lab to obtain missing files."
        )

    animal_key = f"GRIN2B_{animal_id}"
    subject_dir = data_dir / _SLEEP_DIR / animal_key

    # ---- Build source_data ----
    source_data: dict = {}
    conversion_options: dict = {}

    source_data["EEGRecording"] = dict(file_path=str(dat_path), signal_type="EEG")
    conversion_options["EEGRecording"] = dict(stub_test=stub_test)

    source_data["EMGRecording"] = dict(file_path=str(dat_path), signal_type="EMG")
    conversion_options["EMGRecording"] = dict(stub_test=stub_test)

    source_data["BaselineEpochs"] = dict(
        bl1_start_sample=bl1_window["start"] if bl1_window else None,
        bl1_stop_sample=bl1_window["end"] if bl1_window else None,
        bl2_start_sample=bl2_window["start"] if bl2_window else None,
        bl2_stop_sample=bl2_window["end"] if bl2_window else None,
    )
    conversion_options["BaselineEpochs"] = dict(stub_test=stub_test)

    for baseline_key, baseline_label in _BASELINE_LABELS.items():
        win = baseline_windows[baseline_key]
        if win is None:
            continue
        bl_start_sample = win["start"]

        sleep_csv = subject_dir / f"{animal_key}_{baseline_key}-dge_ok.csv"
        seizure_csv = (
            data_dir / _SEIZURE_DIR / f"{animal_key}_{baseline_key}_Seizures.csv"
        )
        swd_csv = subject_dir / "seiz" / f"{animal_key}_{baseline_key}_DGE_SWDs.csv"
        totals_csv = (
            subject_dir / "seiz" / f"{animal_key}_{baseline_key}_Seiz_Totals.csv"
        )
        psd_csv = subject_dir / f"{animal_key}_{baseline_key}-pw_spectrum.csv"

        if sleep_csv.exists():
            key = f"SleepStates_{baseline_key}"
            source_data[key] = dict(
                file_path=str(sleep_csv),
                bl_start_sample=bl_start_sample,
                baseline_label=baseline_label,
            )
            conversion_options[key] = dict(stub_test=stub_test)

        if seizure_csv.exists():
            key = f"Seizures_{baseline_key}"
            source_data[key] = dict(
                file_path=str(seizure_csv),
                bl_start_sample=bl_start_sample,
                baseline_label=baseline_label,
            )
            conversion_options[key] = dict(stub_test=stub_test)

        if swd_csv.exists():
            key = f"SwdCounts_{baseline_key}"
            source_data[key] = dict(
                file_path=str(swd_csv),
                bl_start_sample=bl_start_sample,
                baseline_label=baseline_label,
            )
            conversion_options[key] = dict(stub_test=stub_test)

        if totals_csv.exists():
            key = f"SeizureTotals_{baseline_key}"
            source_data[key] = dict(
                file_path=str(totals_csv), baseline_label=baseline_label
            )
            conversion_options[key] = dict(stub_test=stub_test)

        if psd_csv.exists():
            key = f"StatePowerSpectrum_{baseline_key}"
            source_data[key] = dict(
                file_path=str(psd_csv), baseline_label=baseline_label
            )
            conversion_options[key] = dict(stub_test=stub_test)

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
    # session_id is the recording start date reported in the .dat filename
    # (YYYY_MM_DD in the source filename -> YYYY-MM-DD here).
    session_id = _parse_dat_date(dat_filename).strftime("%Y-%m-%d")
    metadata["NWBFile"]["session_id"] = session_id
    available_baselines = " and ".join(
        k for k in _BASELINE_LABELS if baseline_windows[k]
    )
    metadata["NWBFile"]["session_description"] = (
        f"Chronic wireless EEG/EMG recording, subject {animal_key}, full raw recording "
        f"with {available_baselines} 24-h baseline window(s) marked in the NWB epochs table. "
    )

    # Subject metadata
    subjects_yaml = Path(__file__).parent / "metadata" / "grin2b_subjects_metadata.yaml"
    with open(subjects_yaml) as f:
        all_subjects = yaml.safe_load(f)

    subj_meta = all_subjects.get(animal_key, {})
    metadata.setdefault("Subject", {})
    metadata["Subject"].update(
        {k: v for k, v in subj_meta.items() if not str(v).startswith("TODO")}
    )
    metadata["Subject"]["subject_id"] = animal_key.replace("_", "-")
    # Ensure required fields are always set (NWB schema requires subject_id, sex, species)
    metadata["Subject"].setdefault("species", "Rattus norvegicus")
    metadata["Subject"].setdefault(
        "sex", "U"
    )  # Unknown until lab provides per-animal table

    # ---- Define output file path ----
    output_dir = Path(output_dir)
    if stub_test:
        output_dir = output_dir / "nwb_stub"
    output_dir = output_dir / f"sub-{animal_key.replace('_','-')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    nwbfile_path = (
        output_dir / f"sub-{animal_key.replace('_','-')}_ses-{session_id}_ecephys.nwb"
    )

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
    #     description="Convert one GRIN2B subject to NWB."
    # )
    # parser.add_argument("--data-dir", required=True, help="Root of the data share.")
    # parser.add_argument("--output-dir", required=True, help="Directory for NWB output.")
    # parser.add_argument(
    #     "--animal-id", type=int, required=True, help="Animal ID (e.g. 129)."
    # )
    # parser.add_argument(
    #     "--stub-test", action="store_true", help="Convert small stub only."
    # )
    # args = parser.parse_args()

    session_to_nwb(
        data_dir="H:/Gonzalez-Sulser-CN-data-share",  # args.data_dir,
        output_dir="H:/gonzalez-nwbfiles",  # args.output_dir,
        animal_id=129,  # args.animal_id,
        stub_test=False,
    )
