"""Sleep state classification interface.

Reads the per-epoch sleep state labels produced by the lab's automated scorer.

Source file(s): `<subject_dir>/<subject_id>_BL{N}-dge_ok.csv`, one per
baseline window, ordered in time (BL1, BL2, ...).
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
grid origin is taken from the corresponding row of the NWB epochs table
(added by BaselineEpochsInterface, which must run first), matched
positionally: the first file_path aligns to the first epoch, and so on.
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
        file_paths: list[str | Path],
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_paths : list of str or Path
            Paths to `*-dge_ok.csv` files, one per baseline window, ordered in
            time (BL1, BL2, ...) to match the order of rows in the NWB epochs
            table.
        epoch_duration_s : float
            Duration of each scored epoch in seconds (default 5.0 s).
        """
        super().__init__(file_paths=[str(file_path) for file_path in file_paths])
        self.file_paths = [Path(file_path) for file_path in file_paths]
        self.epoch_duration_s = epoch_duration_s

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        if nwbfile.epochs is None:
            raise ValueError(
                "SleepStateInterface requires the NWB epochs table to already contain the "
                "baseline windows (add BaselineEpochsInterface earlier in the converter)."
            )
        epochs_df = nwbfile.epochs.to_dataframe()
        if len(epochs_df) != len(self.file_paths):
            raise ValueError(
                f"Got {len(self.file_paths)} sleep-score CSV file(s) but {len(epochs_df)} "
                "baseline window(s) in the NWB epochs table. Provide exactly one CSV per "
                "baseline window, ordered to match the epochs table."
            )

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

        for file_path, (_, epoch_row) in zip(self.file_paths, epochs_df.iterrows()):
            bl_offset_s = float(epoch_row["start_time"])
            baseline_label = epoch_row["tags"][0] if len(epoch_row["tags"]) else ""

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
