"""Convert one GRIN2B subject of Hristova et al. 2025 to NWB.

One NWB file per subject holds the full raw EEG and EMG recording, the BL1 and BL2 baseline windows as epochs-table
rows, and the lab's per-window sleep, seizure and power-spectrum files aligned to the recording. All streams come
from one .dat file, so alignment is arithmetic: a window's start sample from Sample_start_end_GRIN2B.xlsx divided by
the sampling frequency. See docs/converting_sessions.md.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml
from neuroconv.utils import dict_deep_update, load_dict_from_file

from .interfaces.taini_recording_interface import SAMPLING_FREQUENCY
from .nwbconverter import Hristova2025NWBConverter

METADATA_DIR = Path(__file__).parent / "metadata"
RECORDING_FOLDER = "Chronic EEG recordings"
WINDOWS_FILE = "Light cycle timing metadata/Sample_start_end_GRIN2B.xlsx"
SUBJECTS_FILE = "Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv"
LINE = "Grin2b"  # "Line" in the subject sheet, which also lists the CDKL5 animals

BASELINE_LABELS = {"BL1": "baseline_window_1", "BL2": "baseline_window_2"}
# Lab file of each per-window stream, relative to the data folder. A missing file leaves that window out of the stream.
STREAM_FILES = {
    "SleepStates": "Sleep state classifications/{subject}/{subject}_{baseline}-dge_ok.csv",
    "Seizures": "Seizure timestamps/{subject}_{baseline}_Seizures.csv",
    "SwdEpochs": "Sleep state classifications/{subject}/seiz/{subject}_{baseline}_DGE_SWDs.csv",
    "SeizureTotals": "Sleep state classifications/{subject}/seiz/{subject}_{baseline}_Seiz_Totals.csv",
    "StatePowerSpectrum": "Sleep state classifications/{subject}/{subject}_{baseline}-pw_spectrum.csv",
}

SEX = {"Male": "M", "Female": "F"}
GENOTYPE = {"Het": "LE-Grin2bem1Mcwi", "Wt": "WT"}

TIMEZONE = ZoneInfo("Europe/London")
LIGHTS_ON = time(7)  # Zeitgeber time 0; BL1 starts at lights-on the day after the recording started

# Excluded from Hristova et al. 2025 after a breeding mix-up; per the PI (2026-10-20) not published on DANDI.
EXCLUDED_ANIMAL_IDS = frozenset({362, 363, 364, 365, 366, 367, 368, 369, 371, 382, 383, 430, 433})
# The xlsx "File" of GRIN2B_424 names 366's recording; its Start/End are right for 424's own file (lab, 2026-11-11).
DAT_FILE_CORRECTIONS = {424: "TAINI_1044_C_Grin2B_424_Redo-2022_06_04-0000.dat"}
# GRIN2B_424's re-analysed DGE_SWDs.csv holds the full 0.2-s detection grid, not one code per 5-s epoch, and cannot
# be aligned to the sleep epochs. Left out until the lab sends the per-epoch file.
SKIPPED_STREAMS = {424: {"SwdEpochs"}}


def get_subject_key(animal_id: int) -> str:
    """The lab's name of a subject, used in its file names, e.g. "GRIN2B_129"."""
    return f"GRIN2B_{animal_id}"


def load_baseline_windows(data_dir: str | Path) -> dict[int, dict[str, dict]]:
    """Read Sample_start_end_GRIN2B.xlsx: animal ID -> baseline ("BL1", "BL2") -> {"file", "start", "end"}.

    The xlsx Start/End are 1-based inclusive sample numbers (MATLAB); "start"/"end" are 0-based inclusive indices
    into the .dat file, as checked against the lab's *_Channels.csv. DAT_FILE_CORRECTIONS is applied to "file".
    """
    table = pd.read_excel(Path(data_dir) / WINDOWS_FILE).dropna(subset=["Animal ID"])
    windows: dict[int, dict[str, dict]] = {}
    for row in table.to_dict(orient="records"):
        animal_id = int(row["Animal ID"])
        windows.setdefault(animal_id, {})[str(row["Baseline"])] = dict(
            file=DAT_FILE_CORRECTIONS.get(animal_id, row["File"]),
            start=int(row["Start"]) - 1,
            end=int(row["End"]) - 1,
        )
    return windows


def get_subject_metadata(subjects_file_path: str | Path, animal_id: int) -> dict:
    """Read the sex and genotype of one GRIN2B subject from the lab's subject sheet.

    The sheet has one row per animal with columns ID, Genotype ("Het"/"Wt"), Sex ("Male"/"Female") and Line.
    """
    subjects = pd.read_csv(subjects_file_path)
    rows = subjects[(subjects["Line"].str.lower() == LINE.lower()) & (subjects["ID"] == animal_id)]
    if len(rows) != 1:
        raise ValueError(f"{subjects_file_path} has {len(rows)} rows for {LINE} animal {animal_id}; expected 1.")
    row = rows.iloc[0]
    return dict(
        subject_id=get_subject_key(animal_id).replace("_", "-"),
        sex=SEX[row["Sex"]],
        genotype=GENOTYPE[row["Genotype"]],
    )


def get_recording_date(dat_file_name: str) -> date:
    """The recording start date in a TainiTec file name: TAINI_<device>_<band>_<line>_<id>_<label>-YYYY_MM_DD-0000.dat."""
    match = re.search(r"-(\d{4})_(\d{2})_(\d{2})-", dat_file_name)
    if match is None:
        raise ValueError(f"No date in the file name {dat_file_name}.")
    return date(*map(int, match.groups()))


def get_session_start_time(dat_file_name: str, bl1_start_sample: int) -> datetime:
    """The time of the first .dat sample: BL1 starts at lights-on (07:00 Edinburgh) the day after the recording date.

    The file name has the date only. The lab confirmed the BL1 anchor, so the start is lights-on minus the BL1 offset.
    """
    lights_on = datetime.combine(get_recording_date(dat_file_name) + timedelta(days=1), LIGHTS_ON, tzinfo=TIMEZONE)
    elapsed = timedelta(seconds=bl1_start_sample / SAMPLING_FREQUENCY)
    return (lights_on.astimezone(timezone.utc) - elapsed).astimezone(TIMEZONE)


def get_sleep_scoring_channels(animal_id: int) -> dict:
    """The EEG and EMG channels of the lab's sleep scorer per baseline, from metadata/sleep_scoring_channels.yaml."""
    with open(METADATA_DIR / "sleep_scoring_channels.yaml") as file:
        return yaml.safe_load(file).get(get_subject_key(animal_id), {})


def session_to_nwb(
    data_dir: str | Path,
    output_dir: str | Path,
    animal_id: int,
    stub_test: bool = False,
    subjects_file_path: str | Path | None = None,
) -> Path:
    """Convert one GRIN2B subject to NWB.

    Parameters
    ----------
    data_dir : str or Path
        The lab's data share (holds "Chronic EEG recordings/", "Sleep state classifications/", ...).
    output_dir : str or Path
        The NWB file is written to <output_dir>/sub-GRIN2B-<id>/, or to <output_dir>/nwb_stub/sub-GRIN2B-<id>/ with
        stub_test.
    animal_id : int
        The animal's number, e.g. 129 for GRIN2B_129.
    stub_test : bool
        Write a few seconds of raw data and the first rows of each table, to check the pipeline quickly.
    subjects_file_path : str or Path, optional
        The lab's subject sheet; default <data_dir>/Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv.

    Returns
    -------
    Path
        The NWB file.
    """
    if animal_id in EXCLUDED_ANIMAL_IDS:
        raise ValueError(f"GRIN2B_{animal_id} was excluded from the study and is not converted.")
    data_dir = Path(data_dir)
    subject = get_subject_key(animal_id)
    windows = load_baseline_windows(data_dir).get(animal_id, {})
    if "BL1" not in windows:
        raise KeyError(f"{WINDOWS_FILE} has no BL1 window for {subject}.")
    dat_file_name = windows["BL1"]["file"]
    dat_file_path = data_dir / RECORDING_FOLDER / dat_file_name
    if not dat_file_path.exists():
        raise FileNotFoundError(f"Raw .dat file not found: {dat_file_path}")

    scoring_channels = get_sleep_scoring_channels(animal_id)
    baseline_windows = {}
    for baseline, label in BASELINE_LABELS.items():
        if baseline in windows:
            window = dict(start_sample=windows[baseline]["start"], stop_sample=windows[baseline]["end"])
            if baseline in scoring_channels:
                window["sleep_scoring_eeg_channel"], window["sleep_scoring_emg_channel"] = scoring_channels[baseline]
            baseline_windows[label] = window

    source_data = dict(
        EEGRecording=dict(file_path=str(dat_file_path), signal_type="EEG"),
        EMGRecording=dict(file_path=str(dat_file_path), signal_type="EMG"),
        BaselineEpochs=dict(baseline_windows=baseline_windows, sampling_frequency=SAMPLING_FREQUENCY),
    )
    for stream, pattern in STREAM_FILES.items():
        if stream in SKIPPED_STREAMS.get(animal_id, set()):
            continue
        file_paths = {
            label: str(data_dir / pattern.format(subject=subject, baseline=baseline))
            for baseline, label in BASELINE_LABELS.items()
            if baseline in windows
        }
        file_paths = {label: file_path for label, file_path in file_paths.items() if Path(file_path).exists()}
        if file_paths:
            source_data[stream] = dict(file_paths=file_paths)

    converter = Hristova2025NWBConverter(source_data=source_data)
    metadata = dict_deep_update(converter.get_metadata(), load_dict_from_file(METADATA_DIR / "general_metadata.yaml"))
    session_id = get_recording_date(dat_file_name).isoformat()
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_start_time"] = get_session_start_time(dat_file_name, windows["BL1"]["start"])
    metadata["NWBFile"]["session_description"] = (
        f"Chronic wireless EEG/EMG recording, subject {subject}, full raw recording with "
        f"{' and '.join(baseline for baseline in BASELINE_LABELS if baseline in windows)} 24-h baseline window(s) "
        f"marked in the NWB epochs table. "
    )
    subjects_file_path = subjects_file_path or data_dir / SUBJECTS_FILE
    metadata["Subject"].update(get_subject_metadata(subjects_file_path, animal_id))

    subject_id = metadata["Subject"]["subject_id"]
    nwbfile_dir = Path(output_dir) / ("nwb_stub" if stub_test else "") / f"sub-{subject_id}"
    nwbfile_dir.mkdir(parents=True, exist_ok=True)
    nwbfile_path = nwbfile_dir / f"sub-{subject_id}_ses-{session_id}_ecephys.nwb"
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options={name: dict(stub_test=stub_test) for name in source_data},
        overwrite=True,
    )
    return nwbfile_path
