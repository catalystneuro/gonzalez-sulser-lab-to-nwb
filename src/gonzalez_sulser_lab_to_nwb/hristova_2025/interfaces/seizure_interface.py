"""Seizure (spike-wave discharge, SWD) streams of the lab's SWD detector, one file per baseline window.

- SeizureInterface: Seizure timestamps/<subject>_BL{N}_Seizures.csv, tab-separated columns sec_start, sec_end, dur
  (seconds from window start), written to processing/behavior/seizure_events.
- SwdEpochsInterface: Sleep state classifications/<subject>/seiz/<subject>_BL{N}_DGE_SWDs.csv, one column DGE_SWDs
  with one code per 5-s epoch, 6 = SWD and 4 = no SWD (cepstral_analysis.m, AUTOMATIC-SLEEP-SCORER), written to
  processing/behavior/swd_epochs.
- SeizureTotalsInterface: Sleep state classifications/<subject>/seiz/<subject>_BL{N}_Seiz_Totals.csv, columns
  N_event, mean_dur, ZT, SWDs, Day (24 rows). ZT/SWDs are hourly seizure counts; N_event, mean_dur and Day are
  window totals in row 0 with rows 1-23 zero-padded, and equal the row count and mean duration of Seizures.csv and
  the sum of SWDs (checked for every GRIN2B file), so only ZT/SWDs are written, to
  processing/behavior/seizure_counts_by_zt_hour.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pynwb.epoch import TimeIntervals

from .baseline_epochs_interface import BaseBaselineStreamInterface
from .sleep_state_interface import EPOCH_DURATION_S, read_epoch_codes

SWD_CODE, NO_SWD_CODE = 6, 4


class SeizureInterface(BaseBaselineStreamInterface):
    """Seizure event intervals."""

    keywords = ["seizure", "EEG"]
    table_name = "seizure_events"
    table_class = TimeIntervals
    table_description = (
        "Seizure events detected by the Gonzalez-Sulser lab automated scoring pipeline. "
        "start_time/stop_time are in seconds relative to session_start_time."
    )
    column_descriptions = dict(duration="Seizure duration in seconds.")

    def read_file(self, file_path: Path) -> pd.DataFrame:
        seizures = pd.read_csv(file_path, sep=None, engine="python")
        return pd.DataFrame(
            dict(
                start_time=seizures["sec_start"].astype(float),
                stop_time=seizures["sec_end"].astype(float),
                duration=seizures["dur"].astype(float),
            )
        )


class SwdEpochsInterface(BaseBaselineStreamInterface):
    """Per-5-s-epoch SWD flags."""

    keywords = ["seizure", "SWD", "spike-wave discharge", "EEG"]
    table_name = "swd_epochs"
    table_class = TimeIntervals
    table_description = (
        "Per-5-second-epoch spike-wave discharge (SWD) flag used by the Gonzalez-Sulser lab sleep scorer to label SWD "
        "epochs (sleep state 4). Written by cepstral_analysis.m "
        "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER): the detected SWD events (seizure_events) "
        "are marked on the 0.2-s time grid of the detection spectrogram, and every 25th grid point is kept, i.e. one "
        "point near the start of each epoch. An epoch is therefore flagged when that point falls inside an SWD, not "
        "whenever an SWD overlaps the epoch. start_time/stop_time are in seconds relative to session_start_time."
    )
    column_descriptions = dict(
        is_swd="True if this epoch is labelled as SWD (DGE_SWDs code 6), False otherwise (code 4)."
    )

    def read_file(self, file_path: Path) -> pd.DataFrame:
        codes, start_times = read_epoch_codes(file_path, "DGE_SWDs", {SWD_CODE, NO_SWD_CODE})
        return pd.DataFrame(
            dict(start_time=start_times, stop_time=start_times + EPOCH_DURATION_S, is_swd=codes == SWD_CODE)
        )


class SeizureTotalsInterface(BaseBaselineStreamInterface):
    """Seizure counts per Zeitgeber hour. Not time-aligned: the hours recur in every window."""

    keywords = ["seizure", "circadian", "Zeitgeber", "EEG"]
    table_name = "seizure_counts_by_zt_hour"
    table_description = (
        "Number of seizure (spike-wave discharge) events per hour of each 24-h baseline window, from the lab's "
        "*_Seiz_Totals.csv (SWDs column, computed by cepstral_analysis.m in "
        "https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). Baseline windows start at lights-on, so "
        "hour h is Zeitgeber time ZTh. An event that crosses an hour boundary is counted in the hour in which it "
        "ends. Whole-window totals (event count, mean duration) can be computed from seizure_events."
    )
    column_descriptions = dict(
        zeitgeber_hour="Zeitgeber hour (hours since lights-on, 0-23).",
        number_of_seizure_events="Number of seizure events in this Zeitgeber hour.",
    )

    def read_file(self, file_path: Path) -> pd.DataFrame:
        totals = pd.read_csv(file_path)
        return pd.DataFrame(
            dict(zeitgeber_hour=totals["ZT"].astype("int64"), number_of_seizure_events=totals["SWDs"].astype("int64"))
        )
