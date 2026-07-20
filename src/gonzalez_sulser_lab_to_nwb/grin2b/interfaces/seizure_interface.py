"""Seizure event interfaces.

Three seizure-related data streams, all aligned to the same BL window origin.
Since one NWB file covers a subject's full recording (BL1 and BL2 both),
each class is instantiated once per baseline window and takes a
`baseline_label` (e.g. "baseline_window_1" / "baseline_window_2") used to
suffix the NWB object name so both baselines' tables/series coexist:

1. SeizureInterface
   Source: `Seizure timestamps/<subject_id>_BL{N}_Seizures.csv`
   Columns: sec_start, sec_end, dur
   → pynwb.epoch.TimeIntervals in processing["behavior"]
     (seizure_events_<baseline_label>)

2. SwdCountsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_DGE_SWDs.csv`
   Single column: DGE_SWDs (per 5-s epoch SWD count)
   → TimeSeries (rate = 0.2 Hz) in processing["behavior"]
     (swd_epoch_counts_<baseline_label>)

3. SeizureTotalsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_Seiz_Totals.csv`
   Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows = per-ZT-hour)
   → DynamicTable in processing["behavior"]
     (seizure_totals_by_zt_<baseline_label>)

All timestamps are in seconds relative to session_start_time, computed as:
  t_abs = bl_start_sample / fs + t_from_bl_start
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from hdmf.common import DynamicTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
from pynwb.epoch import TimeIntervals
from pynwb.misc import TimeSeries

_FS: float = 250.4
_EPOCH_DURATION_S: float = 5.0


class SeizureInterface(BaseDataInterface):
    """Interface for seizure event intervals (sec_start / sec_end / dur CSV)."""

    keywords = ["seizure", "EEG"]

    def __init__(
        self,
        file_path: str | Path,
        bl_start_sample: int,
        baseline_label: str,
        sampling_frequency: float = _FS,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to `*_Seizures.csv`. Columns: sec_start, sec_end, dur.
            Times are in seconds from the start of the baseline window.
        bl_start_sample : int
            Sample index in the .dat file where the baseline window starts.
        baseline_label : str
            Suffix identifying the baseline window (e.g. "baseline_window_1"),
            used to name the resulting NWB TimeIntervals table.
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        """
        super().__init__(
            file_path=str(file_path),
            bl_start_sample=bl_start_sample,
            baseline_label=baseline_label,
        )
        self.file_path = Path(file_path)
        self.bl_start_sample = bl_start_sample
        self.baseline_label = baseline_label
        self.sampling_frequency = sampling_frequency

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        df = pd.read_csv(self.file_path, sep=None, engine="python")
        bl_offset_s = self.bl_start_sample / self.sampling_frequency

        if stub_test:
            df = df.head(20)

        start_times = df["sec_start"].to_numpy(dtype=float) + bl_offset_s
        stop_times = df["sec_end"].to_numpy(dtype=float) + bl_offset_s
        durations = df["dur"].to_numpy(dtype=float)

        seizure_table = TimeIntervals(
            name=f"seizure_events_{self.baseline_label}",
            description=(
                "Seizure events detected by the Gonzalez-Sulser lab automated scoring pipeline. "
                "start_time/stop_time are in seconds relative to session_start_time."
            ),
        )
        seizure_table.add_column(
            name="duration",
            description="Seizure duration in seconds.",
        )

        for start, stop, duration in zip(start_times, stop_times, durations):
            seizure_table.add_interval(
                start_time=float(start),
                stop_time=float(stop),
                duration=float(duration),
            )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(seizure_table)


class SwdCountsInterface(BaseDataInterface):
    """Interface for per-epoch spike-wave discharge (SWD) counts."""

    keywords = ["seizure", "SWD", "spike-wave discharge", "EEG"]

    def __init__(
        self,
        file_path: str | Path,
        bl_start_sample: int,
        baseline_label: str,
        sampling_frequency: float = _FS,
        epoch_duration_s: float = _EPOCH_DURATION_S,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to `*_DGE_SWDs.csv`. Single column `DGE_SWDs` (17,280 rows).
        bl_start_sample : int
            Sample index in the .dat file where the baseline window starts.
        baseline_label : str
            Suffix identifying the baseline window (e.g. "baseline_window_1"),
            used to name the resulting NWB TimeSeries.
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        epoch_duration_s : float
            Duration of each scored epoch in seconds (default 5.0 s).
        """
        super().__init__(
            file_path=str(file_path),
            bl_start_sample=bl_start_sample,
            baseline_label=baseline_label,
        )
        self.file_path = Path(file_path)
        self.bl_start_sample = bl_start_sample
        self.baseline_label = baseline_label
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
        counts = df["DGE_SWDs"].to_numpy(dtype=np.float32)

        if stub_test:
            counts = counts[:100]

        bl_offset_s = self.bl_start_sample / self.sampling_frequency

        swd_series = TimeSeries(
            name=f"swd_epoch_counts_{self.baseline_label}",
            description=(
                "Number of spike-wave discharge (SWD) events per 5-second epoch, "
                "computed by the Gonzalez-Sulser lab automated scoring pipeline."
            ),
            data=counts,
            unit="events",
            starting_time=bl_offset_s,
            rate=1.0 / self.epoch_duration_s,  # 0.2 Hz
            resolution=-1.0,
        )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(swd_series)


class SeizureTotalsInterface(BaseDataInterface):
    """Interface for per-Zeitgeber-hour seizure totals."""

    keywords = ["seizure", "circadian", "Zeitgeber", "EEG"]

    def __init__(self, file_path: str | Path, baseline_label: str):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to `*_Seiz_Totals.csv`.
            Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows).
        baseline_label : str
            Suffix identifying the baseline window (e.g. "baseline_window_1"),
            used to name the resulting NWB DynamicTable.
        """
        super().__init__(file_path=str(file_path), baseline_label=baseline_label)
        self.file_path = Path(file_path)
        self.baseline_label = baseline_label

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        df = pd.read_csv(self.file_path)

        totals_table = DynamicTable(
            name=f"seizure_totals_by_zt_{self.baseline_label}",
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

        for _, row in df.iterrows():
            totals_table.add_row(
                zeitgeber_hour=int(row["ZT"]),
                number_of_seizure_events=int(row["N_event"]),
                mean_seizure_duration=float(row["mean_dur"]),
                spike_wave_discharge=int(row["SWDs"]),
                Day=int(row["Day"]),
            )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(totals_table)
