"""Sleep state classification interface.

Reads the per-epoch sleep state labels produced by the lab's automated scorer.

Source file(s): `<subject_dir>/<subject_id>_BL{N}-dge_ok.csv`, one per
baseline window, keyed by baseline label (the epochs-table tag).
  - Single column: `sleep.score`
  - One row per 5-second epoch, covering 24 h (17,280 epochs)
  - State codes confirmed (Hristova et al. 2025 Epilepsia, doi:10.1111/epi.18606,
    and its supplementary methods):
      0 = Wake
      1 = NREM
      2 = REM
      4 = SWD (spike-wave discharge epochs, classed separately from the three
          sleep states; state 3 is not used by the lab's scoring pipeline)

Writes a single TimeIntervals table to nwbfile with columns:
  start_time, stop_time, sleep_score (int), sleep_state (str label),
  baseline_window (str tag)

Timestamps are in seconds relative to session_start_time. Each file's epoch
grid origin is taken from the NWB epochs-table row with the matching
baseline tag (added by BaselineEpochsInterface, which must run first).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals

from .baseline_epochs_interface import get_baseline_start_times

# State code mapping confirmed from Hristova et al. 2025 supplementary methods
# (same mapping used by StatePowerSpectrumInterface).
_STATE_LABELS: dict[int, str] = {
    0: "Wake",
    1: "NREM",
    2: "REM",
    4: "SWD",
}
_EPOCH_DURATION_S: float = 5.0


class SleepStateInterface(BaseDataInterface):
    """Interface for automated sleep state classifications (5-s epochs)."""

    keywords = ["sleep", "sleep state", "EEG", "NREM", "REM", "Wake"]

    def __init__(
        self,
        file_paths: dict[str, str | Path],
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_paths : dict of str to str or Path
            Paths to `*-dge_ok.csv` files keyed by baseline label (the
            epochs-table tag, e.g. "baseline_window_1").
        epoch_duration_s : float
            Duration of each scored epoch in seconds (default 5.0 s).
        """
        super().__init__(file_paths={label: str(file_path) for label, file_path in file_paths.items()})
        self.file_paths = {label: Path(file_path) for label, file_path in file_paths.items()}
        self.epoch_duration_s = epoch_duration_s

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        bl_offsets = get_baseline_start_times(nwbfile, list(self.file_paths), "SleepStateInterface")

        sleep_table = TimeIntervals(
            name="sleep_states",
            description=(
                "Automated sleep state classifications in 5-second epochs "
                "produced by the Gonzalez-Sulser lab scoring pipeline "
                "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). "
                "State codes: 0=Wake, 1=NREM, 2=REM, 4=SWD (spike-wave discharge "
                "epochs, classed separately from the three sleep states)."
            ),
        )
        sleep_table.add_column(
            name="sleep_score",
            description="Integer sleep state code (0=Wake, 1=NREM, 2=REM, 4=SWD).",
        )
        sleep_table.add_column(
            name="sleep_state",
            description="Human-readable sleep state label derived from sleep_score.",
        )
        sleep_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this sleep-state epoch belongs to.",
        )

        for baseline_label, file_path in self.file_paths.items():
            bl_offset_s = bl_offsets[baseline_label]

            df = pd.read_csv(file_path)
            scores = df["sleep.score"].to_numpy(dtype=np.int32)
            if stub_test:
                scores = scores[:100]

            n_epochs = len(scores)
            start_times = bl_offset_s + np.arange(n_epochs) * self.epoch_duration_s
            stop_times = start_times + self.epoch_duration_s

            for start, stop, score in zip(start_times, stop_times, scores):
                sleep_table.add_interval(
                    start_time=float(start),
                    stop_time=float(stop),
                    sleep_score=int(score),
                    sleep_state=_STATE_LABELS.get(int(score), f"code_{score}"),
                    baseline_window=baseline_label,
                )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(sleep_table)
