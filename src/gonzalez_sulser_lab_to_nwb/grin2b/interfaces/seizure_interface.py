"""Seizure event interfaces.

Three seizure-related data streams, all aligned to the same BL window origin:

1. SeizureInterface
   Source: `Seizure timestamps/<subject_id>_BL{N}_Seizures.csv`
   Columns: sec_start, sec_end, dur
   → ndx_events.AnnotatedEventsTable in processing["behavior"] (seizure_events)

2. SwdCountsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_DGE_SWDs.csv`
   Single column: DGE_SWDs (per 5-s epoch SWD count)
   → TimeSeries (rate = 0.2 Hz) in processing["behavior"]

3. SeizureTotalsInterface
   Source: `<subject_dir>/seiz/<subject_id>_BL{N}_Seiz_Totals.csv`
   Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows = per-ZT-hour)
   → DynamicTable in processing["behavior"]

All timestamps are in seconds relative to session_start_time, computed as:
  t_abs = bl_start_sample / fs + t_from_bl_start
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from hdmf.common import DynamicTable
from ndx_events import AnnotatedEventsTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile
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
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        """
        super().__init__(file_path=str(file_path), bl_start_sample=bl_start_sample)
        self.file_path = Path(file_path)
        self.bl_start_sample = bl_start_sample
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

        start_times = (df["sec_start"].to_numpy(dtype=float) + bl_offset_s).tolist()
        stop_times  = (df["sec_end"].to_numpy(dtype=float)   + bl_offset_s).tolist()
        durations   = df["dur"].to_numpy(dtype=float).tolist()

        seizure_table = AnnotatedEventsTable(
            name="seizure_events",
            description=(
                "Seizure events detected by the Gonzalez-Sulser lab automated scoring pipeline. "
                "event_times are start times in seconds relative to session_start_time."
            ),
            resolution=1.0 / self.sampling_frequency,
        )
        seizure_table.add_column(
            name="stop_time",
            description="Seizure stop time in seconds relative to session_start_time.",
            index=True,
        )
        seizure_table.add_column(
            name="duration",
            description="Seizure duration in seconds.",
            index=True,
        )
        seizure_table.add_event_type(
            label="seizure",
            event_description=(
                "Spike-wave discharge seizure event scored by the lab automated pipeline."
            ),
            event_times=start_times,
            stop_time=stop_times,
            duration=durations,
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
        sampling_frequency : float
            Sampling frequency of the raw recording (default 250.4 Hz).
        epoch_duration_s : float
            Duration of each scored epoch in seconds (default 5.0 s).
        """
        super().__init__(file_path=str(file_path), bl_start_sample=bl_start_sample)
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
        counts = df["DGE_SWDs"].to_numpy(dtype=np.float32)

        if stub_test:
            counts = counts[:100]

        bl_offset_s = self.bl_start_sample / self.sampling_frequency

        swd_series = TimeSeries(
            name="swd_epoch_counts",
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

    def __init__(self, file_path: str | Path):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to `*_Seiz_Totals.csv`.
            Columns: N_event, mean_dur, ZT, SWDs, Day (24 rows).
        """
        super().__init__(file_path=str(file_path))
        self.file_path = Path(file_path)

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
            name="seizure_totals_by_zt",
            description=(
                "Per-Zeitgeber-hour seizure event totals. "
                "ZT (Zeitgeber Time) = hours since lights-on. "
                "TODO: confirm column definitions (N_event, mean_dur, SWDs, Day) with lab."
            ),
        )
        totals_table.add_column(name="ZT", description="Zeitgeber hour (hours since lights-on).")
        totals_table.add_column(name="N_event", description="Number of seizure events in this ZT hour.")
        totals_table.add_column(name="mean_dur", description="Mean seizure duration (seconds) in this ZT hour.")
        totals_table.add_column(name="SWDs", description="Number of SWDs in this ZT hour.")
        totals_table.add_column(name="Day", description="Day index within the baseline window (TODO: confirm encoding).")

        for _, row in df.iterrows():
            totals_table.add_row(
                ZT=int(row["ZT"]),
                N_event=int(row["N_event"]),
                mean_dur=float(row["mean_dur"]),
                SWDs=int(row["SWDs"]),
                Day=int(row["Day"]),
            )

        behavior_module = get_module(nwbfile, "behavior", "Processed behavioral data.")
        behavior_module.add(totals_table)
