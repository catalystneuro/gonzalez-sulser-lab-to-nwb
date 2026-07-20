"""Baseline (BL1/BL2) epochs interface.

Under the one-NWB-file-per-subject design, the raw recording written by
TainiRecordingInterface spans the full multi-day session rather than a single
BL window. This interface adds the BL1 and BL2 windows to the NWB epochs
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
        bl1_start_sample: int | None = None,
        bl1_stop_sample: int | None = None,
        bl2_start_sample: int | None = None,
        bl2_stop_sample: int | None = None,
        sampling_frequency: float = _FS,
    ):
        """
        Parameters
        ----------
        bl1_start_sample, bl1_stop_sample : int, optional
            Inclusive sample-index window for BL1 in the .dat file. Omit both
            if this animal has no BL1 window.
        bl2_start_sample, bl2_stop_sample : int, optional
            Inclusive sample-index window for BL2 in the .dat file. Omit both
            if this animal has no BL2 window.
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        """
        super().__init__(
            bl1_start_sample=bl1_start_sample,
            bl1_stop_sample=bl1_stop_sample,
            bl2_start_sample=bl2_start_sample,
            bl2_stop_sample=bl2_stop_sample,
            sampling_frequency=sampling_frequency,
        )
        self.bl1_start_sample = bl1_start_sample
        self.bl1_stop_sample = bl1_stop_sample
        self.bl2_start_sample = bl2_start_sample
        self.bl2_stop_sample = bl2_stop_sample
        self.sampling_frequency = sampling_frequency

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        if self.bl1_start_sample is not None:
            nwbfile.add_epoch(
                start_time=self.bl1_start_sample / self.sampling_frequency,
                stop_time=(self.bl1_stop_sample + 1) / self.sampling_frequency,
                tags=["baseline_window_1"],
            )
        if self.bl2_start_sample is not None:
            nwbfile.add_epoch(
                start_time=self.bl2_start_sample / self.sampling_frequency,
                stop_time=(self.bl2_stop_sample + 1) / self.sampling_frequency,
                tags=["baseline_window_2"],
            )
