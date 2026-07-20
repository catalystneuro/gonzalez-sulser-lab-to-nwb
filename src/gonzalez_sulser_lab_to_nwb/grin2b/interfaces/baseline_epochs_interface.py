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
            for that baseline in the .dat file. ``baseline_label`` is used as the
            NWB epoch's tag, and as the join key for other interfaces (e.g.
            SeizureInterface, SleepStateInterface) that align their data to
            these epochs.
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
        for window in self.baseline_windows:
            for baseline_label, bounds in window.items():
                nwbfile.add_epoch(
                    start_time=bounds["start_sample"] / self.sampling_frequency,
                    stop_time=(bounds["stop_sample"] + 1) / self.sampling_frequency,
                    tags=[baseline_label],
                )
