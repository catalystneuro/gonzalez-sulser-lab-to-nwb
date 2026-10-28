"""Baseline (BL1/BL2/...) epochs interface.

Under the one-NWB-file-per-subject design, the raw recording written by
TainiRecordingInterface spans the full multi-day session rather than a single
BL window. This interface adds each baseline window to the NWB epochs
table instead, so downstream users can slice the full recording back down to
the analyzed baseline windows.

Sample offsets come from Sample_start_end_GRIN2B.xlsx (parsed in
convert_session.py) and are expressed in seconds relative to
session_start_time, consistent with every other interface in this pipeline.
"""

from __future__ import annotations

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict
from pynwb import NWBFile

_FS: float = 250.4


def get_baseline_start_times(nwbfile: NWBFile, baseline_labels: list[str], interface_name: str) -> dict[str, float]:
    """Look up the start_time of each baseline window in the NWB epochs table by its tag.

    Used by the per-baseline stream interfaces, which take one file per baseline
    label. A baseline window with no file for a given stream (e.g. a missing
    power-spectrum CSV) is simply not requested, so the other windows still align.
    """
    if nwbfile.epochs is None:
        raise ValueError(
            f"{interface_name} requires the NWB epochs table to already contain the "
            "baseline windows (add BaselineEpochsInterface earlier in the converter)."
        )
    epochs_df = nwbfile.epochs.to_dataframe()
    start_times = {row["tags"][0]: float(row["start_time"]) for _, row in epochs_df.iterrows() if len(row["tags"])}
    missing = [label for label in baseline_labels if label not in start_times]
    if missing:
        raise ValueError(
            f"{interface_name}: baseline window(s) {missing} not found in the NWB epochs table "
            f"(available: {list(start_times)})."
        )
    return {label: start_times[label] for label in baseline_labels}


class BaselineEpochsInterface(BaseDataInterface):
    """Adds an NWB epochs-table row for each available baseline window."""

    keywords = ["epochs", "baseline window"]

    def __init__(
        self,
        baseline_windows: list[dict[str, dict[str, int]]],
        sampling_frequency: float = _FS,
    ):
        """
        Parameters
        ----------
        baseline_windows : list of dict
            One entry per baseline window, in chronological order. Each entry
            has the form ``{baseline_label: {"start_sample": int, "stop_sample": int}}``,
            e.g. ``[{"baseline_window_1": {"start_sample": 0, "stop_sample": 100}}]``.
            ``start_sample``/``stop_sample`` are the inclusive sample-index window
            for that baseline in the .dat file. Optional keys
            ``sleep_scoring_eeg_channel`` / ``sleep_scoring_emg_channel`` name the
            electrode-table channels the lab's sleep scorer used for that window;
            when given, every window must have them. ``baseline_label`` is used as the
            NWB epoch's tag, and as the join key for other interfaces (e.g.
            SeizureInterface, SleepStateInterface), whose ``file_paths`` are
            keyed by the same labels.
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        """
        super().__init__(
            baseline_windows=baseline_windows,
            sampling_frequency=sampling_frequency,
        )
        self.baseline_windows = baseline_windows
        self.sampling_frequency = sampling_frequency

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        all_bounds = [bounds for window in self.baseline_windows for bounds in window.values()]
        with_channels = ["sleep_scoring_eeg_channel" in bounds for bounds in all_bounds]
        if any(with_channels) and not all(with_channels):
            raise ValueError("Sleep-scoring channels must be given for every baseline window or for none.")
        if all_bounds and all(with_channels):
            nwbfile.add_epoch_column(
                name="sleep_scoring_eeg_channel",
                description=(
                    "Electrode-table channel (EEG) the lab's sleep scorer used for this baseline window, "
                    "identified by matching the lab's *_Channels.csv against the raw recording."
                ),
            )
            nwbfile.add_epoch_column(
                name="sleep_scoring_emg_channel",
                description=(
                    "Electrode-table channel (EMG) the lab's sleep scorer used for this baseline window, "
                    "identified by matching the lab's *_Channels.csv against the raw recording."
                ),
            )

        for window in self.baseline_windows:
            for baseline_label, bounds in window.items():
                channels = {
                    key: bounds[key]
                    for key in ("sleep_scoring_eeg_channel", "sleep_scoring_emg_channel")
                    if key in bounds
                }
                nwbfile.add_epoch(
                    start_time=bounds["start_sample"] / self.sampling_frequency,
                    stop_time=(bounds["stop_sample"] + 1) / self.sampling_frequency,
                    tags=[baseline_label],
                    **channels,
                )
