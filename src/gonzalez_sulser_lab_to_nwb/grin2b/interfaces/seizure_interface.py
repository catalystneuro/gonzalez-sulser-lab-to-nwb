"""Seizure event interfaces.

Three seizure-related data streams, all aligned to the NWB epochs table added
by BaselineEpochsInterface (which must run first). Each interface takes one
file per baseline window, keyed by the baseline label used as the epochs-table
tag (e.g. "baseline_window_1"), so a baseline with no file for that stream is
simply left out. Each writes a single merged NWB object covering the provided
baseline windows, tagged with a "baseline_window" column so the source
baseline of each row/sample can be recovered:

1. SeizureInterface
   Source: `Seizure timestamps/<subject_id>_BL{N}_Seizures.csv`
   Columns: sec_start, sec_end, dur
   → a single pynwb.epoch.TimeIntervals in processing["behavior"]
     (seizure_events)

2. SwdEpochsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_DGE_SWDs.csv`
   Single column: DGE_SWDs, one value per 5-s epoch: 6 = SWD, 4 = no SWD
   (written by cepstral_analysis.m in the lab's AUTOMATIC-SLEEP-SCORER repo;
   the sleep scorer turns 6 into sleep state 4 = SWD)
   → a single pynwb.epoch.TimeIntervals in processing["behavior"]
     (swd_epochs) with a boolean is_swd column

3. SeizureTotalsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_Seiz_Totals.csv`
   Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows). Per cepstral_analysis.m,
   ZT/SWDs are the per-hour seizure counts; N_event, mean_dur and Day are
   baseline-window totals stored in row 0 with rows 1-23 zero-padded. The
   totals equal the row count / mean duration of the matching Seizures.csv and
   the sum of SWDs (checked for every GRIN2B file), so only ZT/SWDs are written.
   → a single hdmf.common.DynamicTable in processing["behavior"]
     (seizure_counts_by_zt_hour); not time-aligned (ZT-hour buckets recur every
     baseline window), so the epochs table is only consulted for the
     baseline_window tag, not for timing.

All timestamps are in seconds relative to session_start_time, computed as:
  t_abs = bl_offset_s + t_from_bl_start
where bl_offset_s is read from the corresponding NWB epochs-table row's
start_time.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from hdmf.common import DynamicTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals

from .baseline_epochs_interface import get_baseline_start_times

_EPOCH_DURATION_S: float = 5.0


class SeizureInterface(BaseDataInterface):
    """Interface for seizure event intervals (sec_start / sec_end / dur CSVs).

    Aligns each CSV's seizure events to the NWB epochs-table row with the
    matching baseline tag (added by BaselineEpochsInterface, which must run
    first). All events from all files are written into a single TimeIntervals
    table, tagged with the baseline window they came from.
    """

    keywords = ["seizure", "EEG"]

    def __init__(self, file_paths: dict[str, str | Path]):
        """
        Parameters
        ----------
        file_paths : dict of str to str or Path
            Paths to `*_Seizures.csv` files keyed by baseline label (the
            epochs-table tag, e.g. "baseline_window_1"). Columns: sec_start,
            sec_end, dur. Times are in seconds from the start of the
            corresponding baseline window.
        """
        super().__init__(file_paths={label: str(file_path) for label, file_path in file_paths.items()})
        self.file_paths = {label: Path(file_path) for label, file_path in file_paths.items()}

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        bl_offsets = get_baseline_start_times(nwbfile, list(self.file_paths), "SeizureInterface")

        seizure_table = TimeIntervals(
            name="seizure_events",
            description=(
                "Seizure events detected by the Gonzalez-Sulser lab automated scoring pipeline. "
                "start_time/stop_time are in seconds relative to session_start_time."
            ),
        )
        seizure_table.add_column(
            name="duration",
            description="Seizure duration in seconds.",
        )
        seizure_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this seizure event belongs to.",
        )

        for baseline_label, file_path in self.file_paths.items():
            bl_offset_s = bl_offsets[baseline_label]

            df = pd.read_csv(file_path, sep=None, engine="python")
            if stub_test:
                df = df.head(20)

            start_times = df["sec_start"].to_numpy(dtype=float) + bl_offset_s
            stop_times = df["sec_end"].to_numpy(dtype=float) + bl_offset_s
            durations = df["dur"].to_numpy(dtype=float)

            for start, stop, duration in zip(start_times, stop_times, durations):
                seizure_table.add_interval(
                    start_time=float(start),
                    stop_time=float(stop),
                    duration=float(duration),
                    baseline_window=baseline_label,
                )

        if len(seizure_table) == 0:
            # HDMF cannot infer a dtype for an empty VectorData, and an empty
            # seizure_events table is a real outcome (animal had zero scored
            # seizures in every available baseline) rather than an error, so
            # skip writing the table instead of crashing the conversion.
            warnings.warn(
                "SeizureInterface: no seizure events found in any baseline window "
                f"({[str(p) for p in self.file_paths.values()]}) — skipping seizure_events table.",
                stacklevel=2,
            )
            return

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(seizure_table)


class SwdEpochsInterface(BaseDataInterface):
    """Interface for per-epoch spike-wave discharge (SWD) flags.

    Aligns each CSV's per-5-s-epoch flags to the NWB epochs-table row with
    the matching baseline tag (added by BaselineEpochsInterface, which must
    run first). All epochs from all files are written into a single
    TimeIntervals table, tagged with the baseline window they came from.
    """

    keywords = ["seizure", "SWD", "spike-wave discharge", "EEG"]

    def __init__(
        self,
        file_paths: dict[str, str | Path],
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_paths : dict of str to str or Path
            Paths to `*_DGE_SWDs.csv` files keyed by baseline label (the
            epochs-table tag, e.g. "baseline_window_1"). Each has a single
            column `DGE_SWDs` (17,280 rows, 6 = SWD, 4 = no SWD).
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
        bl_offsets = get_baseline_start_times(nwbfile, list(self.file_paths), "SwdEpochsInterface")

        swd_table = TimeIntervals(
            name="swd_epochs",
            description=(
                "Per-5-second-epoch spike-wave discharge (SWD) flag used by the Gonzalez-Sulser lab "
                "sleep scorer to label SWD epochs (sleep state 4). Written by cepstral_analysis.m "
                "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER): the detected SWD "
                "events (seizure_events) are marked on the 0.2-s time grid of the detection "
                "spectrogram, and every 25th grid point is kept, i.e. one point near the start of "
                "each epoch. An epoch is therefore flagged when that point falls inside an SWD, not "
                "whenever an SWD overlaps the epoch. "
                "start_time/stop_time are in seconds relative to session_start_time."
            ),
        )
        swd_table.add_column(
            name="is_swd",
            description="True if this epoch is labelled as SWD (DGE_SWDs code 6), False otherwise (code 4).",
        )
        swd_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this epoch belongs to.",
        )

        for baseline_label, file_path in self.file_paths.items():
            bl_offset_s = bl_offsets[baseline_label]

            df = pd.read_csv(file_path)
            codes = df["DGE_SWDs"].to_numpy()
            unexpected_codes = set(np.unique(codes)) - {4, 6}
            if unexpected_codes:
                raise ValueError(f"{file_path}: unexpected DGE_SWDs codes {sorted(unexpected_codes)} (expected 4 or 6).")
            if stub_test:
                codes = codes[:100]

            n_epochs = len(codes)
            start_times = bl_offset_s + np.arange(n_epochs) * self.epoch_duration_s
            stop_times = start_times + self.epoch_duration_s

            for start, stop, code in zip(start_times, stop_times, codes):
                swd_table.add_interval(
                    start_time=float(start),
                    stop_time=float(stop),
                    is_swd=bool(code == 6),
                    baseline_window=baseline_label,
                )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(swd_table)


class SeizureTotalsInterface(BaseDataInterface):
    """Interface for per-Zeitgeber-hour seizure counts.

    Not time-aligned to the recording (ZT-hour buckets recur every baseline
    window), so the epochs table is only checked to contain each baseline
    label. All rows from all files are written into a single DynamicTable,
    tagged with the baseline window they came from.
    """

    keywords = ["seizure", "circadian", "Zeitgeber", "EEG"]

    def __init__(self, file_paths: dict[str, str | Path]):
        """
        Parameters
        ----------
        file_paths : dict of str to str or Path
            Paths to `*_Seiz_Totals.csv` files keyed by baseline label (the
            epochs-table tag, e.g. "baseline_window_1"). Columns: N_event,
            mean_dur, ZT, SWDs, Day (24 rows each).
        """
        super().__init__(file_paths={label: str(file_path) for label, file_path in file_paths.items()})
        self.file_paths = {label: Path(file_path) for label, file_path in file_paths.items()}

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        get_baseline_start_times(nwbfile, list(self.file_paths), "SeizureTotalsInterface")

        totals_table = DynamicTable(
            name="seizure_counts_by_zt_hour",
            description=(
                "Number of seizure (spike-wave discharge) events per hour of each 24-h baseline "
                "window, from the lab's *_Seiz_Totals.csv (SWDs column, computed by "
                "cepstral_analysis.m in https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). "
                "Baseline windows start at lights-on, so hour h is Zeitgeber time ZTh. "
                "An event that crosses an hour boundary is counted in the hour in which it ends. "
                "Whole-window totals (event count, mean duration) can be computed from seizure_events."
            ),
        )
        totals_table.add_column(
            name="zeitgeber_hour", description="Zeitgeber hour (hours since lights-on, 0-23)."
        )
        totals_table.add_column(
            name="number_of_seizure_events",
            description="Number of seizure events in this Zeitgeber hour.",
        )
        totals_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this row belongs to.",
        )

        for baseline_label, file_path in self.file_paths.items():
            df = pd.read_csv(file_path)

            for _, row in df.iterrows():
                totals_table.add_row(
                    zeitgeber_hour=int(row["ZT"]),
                    number_of_seizure_events=int(row["SWDs"]),
                    baseline_window=baseline_label,
                )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(totals_table)
