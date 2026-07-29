"""Seizure event interfaces.

Three seizure-related data streams, all aligned to the NWB epochs table added
by BaselineEpochsInterface (which must run first). Each interface takes one
file per baseline window, ordered in time (BL1, BL2, ...) to match the order
of rows in the epochs table, and writes a single merged NWB object covering
all baseline windows, tagged with a "baseline_window" column so the source
baseline of each row/sample can be recovered:

1. SeizureInterface
   Source: `Seizure timestamps/<subject_id>_BL{N}_Seizures.csv`
   Columns: sec_start, sec_end, dur
   → a single pynwb.epoch.TimeIntervals in processing["behavior"]
     (seizure_events)

2. SwdCountsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_DGE_SWDs.csv`
   Single column: DGE_SWDs (per 5-s epoch SWD count)
   → a single pynwb.epoch.TimeIntervals in processing["behavior"]
     (swd_epoch_counts)

3. SeizureTotalsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_Seiz_Totals.csv`
   Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows = per-ZT-hour)
   → a single hdmf.common.DynamicTable in processing["behavior"]
     (seizure_totals_by_zt); not time-aligned (ZT-hour buckets recur every
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

_EPOCH_DURATION_S: float = 5.0


def _require_epochs(nwbfile: NWBFile, file_paths: list, interface_name: str) -> pd.DataFrame:
    """Fetch the NWB epochs table as a DataFrame, checked against file_paths length."""
    if nwbfile.epochs is None:
        raise ValueError(
            f"{interface_name} requires the NWB epochs table to already contain the "
            "baseline windows (add BaselineEpochsInterface earlier in the converter)."
        )
    epochs_df = nwbfile.epochs.to_dataframe()
    if len(epochs_df) != len(file_paths):
        raise ValueError(
            f"Got {len(file_paths)} file(s) but {len(epochs_df)} baseline window(s) in the "
            "NWB epochs table. Provide exactly one file per baseline window, ordered to "
            "match the epochs table."
        )
    return epochs_df


def _epoch_label(epoch_row: pd.Series) -> str:
    return epoch_row["tags"][0] if len(epoch_row["tags"]) else ""


class SeizureInterface(BaseDataInterface):
    """Interface for seizure event intervals (sec_start / sec_end / dur CSVs).

    Aligns each CSV's seizure events to the corresponding row of the NWB
    epochs table (added by BaselineEpochsInterface, which must run first),
    matched positionally: the first file_path aligns to the first epoch, and
    so on. All events from all files are written into a single TimeIntervals
    table, tagged with the baseline window they came from.
    """

    keywords = ["seizure", "EEG"]

    def __init__(self, file_paths: list[str | Path]):
        """
        Parameters
        ----------
        file_paths : list of str or Path
            Paths to `*_Seizures.csv` files, one per baseline window, ordered
            in time (BL1, BL2, ...) to match the order of rows in the NWB
            epochs table. Columns: sec_start, sec_end, dur. Times are in
            seconds from the start of the corresponding baseline window.
        """
        super().__init__(file_paths=[str(file_path) for file_path in file_paths])
        self.file_paths = [Path(file_path) for file_path in file_paths]

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        epochs_df = _require_epochs(nwbfile, self.file_paths, "SeizureInterface")

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

        for file_path, (_, epoch_row) in zip(self.file_paths, epochs_df.iterrows()):
            bl_offset_s = float(epoch_row["start_time"])
            baseline_label = _epoch_label(epoch_row)

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
                f"({[str(p) for p in self.file_paths]}) — skipping seizure_events table.",
                stacklevel=2,
            )
            return

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(seizure_table)


class SwdCountsInterface(BaseDataInterface):
    """Interface for per-epoch spike-wave discharge (SWD) counts.

    Aligns each CSV's per-5-s-epoch counts to the corresponding row of the
    NWB epochs table (added by BaselineEpochsInterface, which must run
    first), matched positionally. All epochs from all files are written into
    a single TimeIntervals table, tagged with the baseline window they came
    from.
    """

    keywords = ["seizure", "SWD", "spike-wave discharge", "EEG"]

    def __init__(
        self,
        file_paths: list[str | Path],
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_paths : list of str or Path
            Paths to `*_DGE_SWDs.csv` files, one per baseline window, ordered
            in time (BL1, BL2, ...) to match the order of rows in the NWB
            epochs table. Each has a single column `DGE_SWDs` (17,280 rows).
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
        epochs_df = _require_epochs(nwbfile, self.file_paths, "SwdCountsInterface")

        swd_table = TimeIntervals(
            name="swd_epoch_counts",
            description=(
                "Number of spike-wave discharge (SWD) events per 5-second epoch, "
                "computed by the Gonzalez-Sulser lab automated scoring pipeline. "
                "start_time/stop_time are in seconds relative to session_start_time."
            ),
        )
        swd_table.add_column(
            name="swd_count",
            description="Number of SWD events in this epoch.",
        )
        swd_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this epoch belongs to.",
        )

        for file_path, (_, epoch_row) in zip(self.file_paths, epochs_df.iterrows()):
            bl_offset_s = float(epoch_row["start_time"])
            baseline_label = _epoch_label(epoch_row)

            df = pd.read_csv(file_path)
            counts = df["DGE_SWDs"].to_numpy(dtype=np.float32)
            if stub_test:
                counts = counts[:100]

            n_epochs = len(counts)
            start_times = bl_offset_s + np.arange(n_epochs) * self.epoch_duration_s
            stop_times = start_times + self.epoch_duration_s

            for start, stop, count in zip(start_times, stop_times, counts):
                swd_table.add_interval(
                    start_time=float(start),
                    stop_time=float(stop),
                    swd_count=float(count),
                    baseline_window=baseline_label,
                )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(swd_table)


class SeizureTotalsInterface(BaseDataInterface):
    """Interface for per-Zeitgeber-hour seizure totals.

    Not time-aligned to the recording (ZT-hour buckets recur every baseline
    window), so the epochs table is only consulted for the baseline_window
    tag, matched positionally: the first file_path aligns to the first epoch,
    and so on. All rows from all files are written into a single
    DynamicTable, tagged with the baseline window they came from.
    """

    keywords = ["seizure", "circadian", "Zeitgeber", "EEG"]

    def __init__(self, file_paths: list[str | Path]):
        """
        Parameters
        ----------
        file_paths : list of str or Path
            Paths to `*_Seiz_Totals.csv` files, one per baseline window,
            ordered in time (BL1, BL2, ...) to match the order of rows in the
            NWB epochs table. Columns: N_event, mean_dur, ZT, SWDs, Day
            (24 rows each).
        """
        super().__init__(file_paths=[str(file_path) for file_path in file_paths])
        self.file_paths = [Path(file_path) for file_path in file_paths]

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        epochs_df = _require_epochs(nwbfile, self.file_paths, "SeizureTotalsInterface")

        totals_table = DynamicTable(
            name="seizure_totals_by_zt",
            description=(
                "Per-Zeitgeber-hour seizure event totals. "
                "ZT (Zeitgeber Time) = hours since lights-on. "
                "TODO: confirm column definitions (N_event, mean_dur, SWDs, Day) with lab."
            ),
        )
        totals_table.add_column(
            name="zeitgeber_hour", description="Zeitgeber hour (hours since lights-on)."
        )
        totals_table.add_column(
            name="number_of_seizure_events",
            description="Number of seizure events in this ZT hour.",
        )
        totals_table.add_column(
            name="mean_seizure_duration",
            description="Mean seizure duration (seconds) in this ZT hour.",
        )
        totals_table.add_column(
            name="spike_wave_discharge",
            description="Number of spike-wave discharge (SWD) in this ZT hour.",
        )
        totals_table.add_column(
            name="Day",
            description="Day index within the baseline window (TODO: confirm encoding).",
        )
        totals_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this row belongs to.",
        )

        for file_path, (_, epoch_row) in zip(self.file_paths, epochs_df.iterrows()):
            baseline_label = _epoch_label(epoch_row)
            df = pd.read_csv(file_path)

            for _, row in df.iterrows():
                totals_table.add_row(
                    zeitgeber_hour=int(row["ZT"]),
                    number_of_seizure_events=int(row["N_event"]),
                    mean_seizure_duration=float(row["mean_dur"]),
                    spike_wave_discharge=int(row["SWDs"]),
                    Day=int(row["Day"]),
                    baseline_window=baseline_label,
                )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(totals_table)
