"""Baseline windows (BL1, BL2) in the NWB epochs table, and the base class of the streams scored per window.

The raw recording covers the whole multi-day session. The lab analyzed two 24-h baseline windows of it, BL1 and BL2,
given as sample numbers in Sample_start_end_GRIN2B.xlsx. BaselineEpochsInterface writes one epochs-table row per window,
tagged with its label ("baseline_window_1", "baseline_window_2"). The lab's derived files (sleep scores, seizures, SWD
flags, seizure totals, power spectra) hold one window each, with times relative to the start of that window.
BaseBaselineStreamInterface aligns them to the recording through the epochs-table row of the same label, so
BaselineEpochsInterface must run first.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
from hdmf.common import DynamicTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from pynwb import NWBFile

from .taini_recording_interface import SAMPLING_FREQUENCY

SLEEP_SCORING_CHANNEL_COLUMNS = {
    "sleep_scoring_eeg_channel": "Electrode-table channel (EEG) the lab's sleep scorer used for this baseline window, "
    "identified by matching the lab's *_Channels.csv against the raw recording.",
    "sleep_scoring_emg_channel": "Electrode-table channel (EMG) the lab's sleep scorer used for this baseline window, "
    "identified by matching the lab's *_Channels.csv against the raw recording.",
}
MODULE_DESCRIPTIONS = {"behavior": "Processed behavioral data.", "ecephys": "Processed electrophysiology data."}


class BaselineEpochsInterface(BaseDataInterface):
    """Adds one NWB epochs-table row per baseline window."""

    keywords = ["epochs", "baseline window"]

    def __init__(self, baseline_windows: dict[str, dict], sampling_frequency: float = SAMPLING_FREQUENCY):
        """
        Parameters
        ----------
        baseline_windows : dict
            Baseline label (the epoch tag, e.g. "baseline_window_1") to the window, in chronological order. A window
            has "start_sample" and "stop_sample", the 0-based inclusive sample indices in the .dat file, and
            optionally "sleep_scoring_eeg_channel" and "sleep_scoring_emg_channel", the electrode-table channels the
            lab's sleep scorer used. The channels must be given for every window or for none.
        sampling_frequency : float
            Sampling frequency of the raw recording.
        """
        super().__init__(baseline_windows=baseline_windows, sampling_frequency=sampling_frequency)
        self.baseline_windows = baseline_windows
        self.sampling_frequency = sampling_frequency

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        has_channels = [set(SLEEP_SCORING_CHANNEL_COLUMNS) <= set(w) for w in self.baseline_windows.values()]
        if any(has_channels) and not all(has_channels):
            raise ValueError("Sleep-scoring channels must be given for every baseline window or for none.")
        if any(has_channels):
            for name, description in SLEEP_SCORING_CHANNEL_COLUMNS.items():
                nwbfile.add_epoch_column(name=name, description=description)

        for label, window in self.baseline_windows.items():
            nwbfile.add_epoch(
                start_time=window["start_sample"] / self.sampling_frequency,
                stop_time=(window["stop_sample"] + 1) / self.sampling_frequency,
                tags=[label],
                **{name: window[name] for name in SLEEP_SCORING_CHANNEL_COLUMNS if name in window},
            )


def get_baseline_start_times(nwbfile: NWBFile, labels: list[str]) -> dict[str, float]:
    """Return the start time of each baseline window, from the epochs-table row tagged with its label."""
    if nwbfile.epochs is None:
        raise ValueError("The epochs table has no baseline windows; add BaselineEpochsInterface before this stream.")
    start_times = {tags[0]: start for tags, start in zip(nwbfile.epochs["tags"][:], nwbfile.epochs["start_time"][:])}
    missing = [label for label in labels if label not in start_times]
    if missing:
        raise ValueError(f"Baseline windows {missing} are not in the epochs table (it has {list(start_times)}).")
    return {label: float(start_times[label]) for label in labels}


class BaseBaselineStreamInterface(BaseDataInterface):
    """A stream with one lab file per baseline window, written as one table with a "baseline_window" column.

    A window without a file for the stream is left out of that stream only (e.g. the lab has no BL1 power spectrum
    for GRIN2B_140). Subclasses set the table name, class, module and column descriptions, and read one file into a
    DataFrame with times in seconds from the start of its window; "start_time" and "stop_time" are shifted to the
    session clock here.
    """

    table_name: str
    table_description: str
    table_class: type[DynamicTable] = DynamicTable
    module_name: str = "behavior"
    column_descriptions: dict[str, str]
    stub_rows: int = 100

    def __init__(self, file_paths: dict[str, str | Path]):
        """
        Parameters
        ----------
        file_paths : dict
            Path of the lab file of each baseline window, keyed by the window's label in the epochs table
            (e.g. "baseline_window_1").
        """
        super().__init__(file_paths={label: str(file_path) for label, file_path in file_paths.items()})
        self.file_paths = {label: Path(file_path) for label, file_path in file_paths.items()}

    def read_file(self, file_path: Path) -> pd.DataFrame:
        raise NotImplementedError

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        start_times = get_baseline_start_times(nwbfile, list(self.file_paths))
        frames = []
        for label, file_path in self.file_paths.items():
            frame = self.read_file(file_path)
            if stub_test:
                frame = frame.head(self.stub_rows)
            for column in ("start_time", "stop_time"):
                if column in frame:
                    frame[column] = frame[column] + start_times[label]
            frames.append(frame.assign(baseline_window=label))
        data = pd.concat(frames, ignore_index=True)

        if data.empty:
            # An empty column has no dtype for HDMF to write. A subject with no seizure in any window is a real
            # outcome (e.g. GRIN2B_238), so the table is left out.
            warnings.warn(f"{type(self).__name__}: no rows in {list(self.file_paths.values())}; {self.table_name} is not written.")
            return

        descriptions = dict(
            self.column_descriptions,
            baseline_window="Baseline window (epochs-table tag) this row belongs to.",
        )
        table = self.table_class.from_dataframe(
            data,
            name=self.table_name,
            table_description=self.table_description,
            columns=[dict(name=name, description=descriptions[name]) for name in data.columns if name in descriptions],
        )
        get_module(nwbfile, self.module_name, MODULE_DESCRIPTIONS[self.module_name]).add(table)
