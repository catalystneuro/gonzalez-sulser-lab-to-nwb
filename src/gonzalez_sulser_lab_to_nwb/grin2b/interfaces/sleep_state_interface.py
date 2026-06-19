"""Sleep state classification interface.

Reads the per-epoch sleep state labels produced by the lab's automated scorer.

Source file: `<subject_dir>/<subject_id>_BL{1,2}-dge_ok.csv`
  - Single column: `sleep.score`
  - One row per 5-second epoch, covering 24 h (17,280 epochs)
  - State codes (assumed — TODO: confirm with lab):
      0 = Wake
      1 = NREM
      2 = REM
      (state 4 referenced in pw_spectrum.csv — may appear in other animals)

Writes a TimeIntervals table to nwbfile with columns:
  start_time, stop_time, sleep_score (int), sleep_state (str label)

Timestamps are in seconds relative to session_start_time.
The epoch grid origin is bl_start_sample / sampling_frequency.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals

# TODO: confirm label mapping with lab.
_STATE_LABELS: dict[int, str] = {
    0: "Wake",
    1: "NREM",
    2: "REM",
    4: "Unknown",  # referenced in pw_spectrum.csv; meaning TBD
}
_EPOCH_DURATION_S: float = 5.0
_FS: float = 250.4


class SleepStateInterface(BaseDataInterface):
    """Interface for automated sleep state classifications (5-s epochs)."""

    keywords = ["sleep", "sleep state", "EEG", "NREM", "REM", "Wake"]

    def __init__(
        self,
        file_path: str | Path,
        bl_start_sample: int,
        sampling_frequency: float = _FS,
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to the `*-dge_ok.csv` file for the target subject and baseline.
        bl_start_sample : int
            Sample index in the .dat file where the baseline window starts.
            Used to compute epoch start times relative to session_start_time.
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        epoch_duration_s : float
            Duration of each scored epoch in seconds (default 5.0 s).
        """
        super().__init__(
            file_path=str(file_path),
            bl_start_sample=bl_start_sample,
        )
        self.file_path = Path(file_path)
        self.bl_start_sample = bl_start_sample
        self.sampling_frequency = sampling_frequency
        self.epoch_duration_s = epoch_duration_s

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        df = pd.read_csv(self.file_path)
        scores = df["sleep.score"].to_numpy(dtype=np.int32)

        if stub_test:
            scores = scores[:100]

        bl_offset_s = self.bl_start_sample / self.sampling_frequency
        n_epochs = len(scores)
        start_times = bl_offset_s + np.arange(n_epochs) * self.epoch_duration_s
        stop_times = start_times + self.epoch_duration_s

        sleep_table = TimeIntervals(
            name="sleep_states",
            description=(
                "Automated sleep state classifications in 5-second epochs "
                "produced by the Gonzalez-Sulser lab scoring pipeline. "
                "State codes: 0=Wake, 1=NREM, 2=REM "
                "(TODO: confirm mapping with lab; state 4 meaning TBD)."
            ),
        )
        sleep_table.add_column(
            name="sleep_score",
            description="Integer sleep state code (0=Wake, 1=NREM, 2=REM; TODO confirm).",
        )
        sleep_table.add_column(
            name="sleep_state",
            description="Human-readable sleep state label derived from sleep_score.",
        )

        for start, stop, score in zip(start_times, stop_times, scores):
            sleep_table.add_interval(
                start_time=float(start),
                stop_time=float(stop),
                sleep_score=int(score),
                sleep_state=_STATE_LABELS.get(int(score), f"code_{score}"),
            )

        from neuroconv.tools.nwb_helpers import get_module

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(sleep_table)
