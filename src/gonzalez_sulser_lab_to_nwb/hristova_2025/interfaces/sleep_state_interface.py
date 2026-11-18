"""Sleep states scored by the lab's automated sleep scorer, one per 5-s epoch.

Source: Sleep state classifications/<subject>/<subject>_BL{N}-dge_ok.csv, one column "sleep.score" with 17,280 rows
(24 h of 5-s epochs). Codes 0 = Wake, 1 = NREM, 2 = REM (Hristova et al. 2025, supplementary methods). dge_ok.csv is
the scorer's output before SWD epochs are relabelled to 4 (correct.C in Sleep_autoscore_Beta.R,
AUTOMATIC-SLEEP-SCORER), so it holds only 0-2; the SWD flags are in the swd_epochs table (SwdEpochsInterface).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pynwb.epoch import TimeIntervals

from .baseline_epochs_interface import BaseBaselineStreamInterface

EPOCH_DURATION_S = 5.0
SLEEP_STATE_LABELS = {0: "Wake", 1: "NREM", 2: "REM"}


def read_epoch_codes(file_path: Path, column: str, valid_codes: set[int]) -> tuple[np.ndarray, np.ndarray]:
    """Read one code per 5-s epoch from a lab CSV; return the codes and the epoch start times from window start."""
    codes = pd.read_csv(file_path)[column].to_numpy(dtype=np.int64)
    unexpected = set(np.unique(codes).tolist()) - valid_codes
    if unexpected:
        raise ValueError(f"{file_path}: unexpected {column} codes {sorted(unexpected)} (expected {sorted(valid_codes)}).")
    return codes, np.arange(len(codes)) * EPOCH_DURATION_S


class SleepStateInterface(BaseBaselineStreamInterface):
    """Automated sleep-state scores (5-s epochs), written to processing/behavior/sleep_states."""

    keywords = ["sleep", "sleep state", "EEG", "NREM", "REM", "Wake"]
    table_name = "sleep_states"
    table_class = TimeIntervals
    table_description = (
        "Automated sleep state classifications in 5-second epochs produced by the Gonzalez-Sulser lab scoring "
        "pipeline (https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER), from its *-dge_ok.csv output. "
        "State codes: 0=Wake, 1=NREM, 2=REM. These are the scores before spike-wave discharge (SWD) epochs are "
        "relabelled, so epochs containing SWDs are scored as Wake, NREM or REM here. The scorer labels the epochs "
        "flagged in the swd_epochs table (is_swd) as SWD (state 4); that relabelled output is not part of the shared "
        "data."
    )
    column_descriptions = dict(
        sleep_score="Integer sleep state code (0=Wake, 1=NREM, 2=REM).",
        sleep_state="Human-readable sleep state label derived from sleep_score.",
    )

    def read_file(self, file_path: Path) -> pd.DataFrame:
        scores, start_times = read_epoch_codes(file_path, "sleep.score", set(SLEEP_STATE_LABELS))
        return pd.DataFrame(
            dict(
                start_time=start_times,
                stop_time=start_times + EPOCH_DURATION_S,
                sleep_score=scores,
                sleep_state=[SLEEP_STATE_LABELS[score] for score in scores],
            )
        )
