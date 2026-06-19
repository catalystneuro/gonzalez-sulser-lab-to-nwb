"""Per-sleep-state power spectrum interface.

Source file: `<subject_dir>/<subject_id>_BL{N}-pw_spectrum.csv`
  - 628 rows (0.2 Hz steps from 0 to 125.2 Hz = Nyquist of 250.4 Hz)
  - Columns: hz, s_0, s_1, s_2, s_4
  - s_N = average power spectral density for sleep state N
  - TODO: confirm units (µV²/Hz? normalised?) and meaning of state 4

Written as a DynamicTable in processing["ecephys"] with one row per
frequency bin and one column per sleep state.
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

# State column name → human-readable label mapping
# TODO: confirm state 4 meaning with lab.
_STATE_COLS = {
    "s_0": "Wake",
    "s_1": "NREM",
    "s_2": "REM",
    "s_4": "Unknown_state_4",  # TODO: ask lab
}


class StatePowerSpectrumInterface(BaseDataInterface):
    """Interface for per-sleep-state average power spectra."""

    keywords = ["power spectrum", "EEG", "sleep", "PSD"]

    def __init__(self, file_path: str | Path):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to `*-pw_spectrum.csv`.
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
        # The CSV has a spurious first data row of "BL1, BL1, ..." — skip it.
        df = pd.read_csv(self.file_path, skiprows=[1])
        df.columns = ["hz"] + list(df.columns[1:])

        # Convert to numeric, coercing any remaining header artifacts.
        df = df.apply(pd.to_numeric, errors="coerce").dropna()

        psd_table = DynamicTable(
            name="sleep_state_power_spectra",
            description=(
                "Average power spectral density per sleep state, computed by the "
                "Gonzalez-Sulser lab scoring pipeline. "
                "Frequency bins from 0 to 125.2 Hz (Nyquist of 250.4 Hz) in 0.2 Hz steps. "
                "State columns: s_0=Wake, s_1=NREM, s_2=REM, s_4=TBD (TODO confirm). "
                "TODO: confirm units (µV²/Hz or normalised PSD?)."
            ),
        )
        psd_table.add_column(name="frequency_hz", description="Frequency in Hz.")
        for col, label in _STATE_COLS.items():
            if col in df.columns:
                psd_table.add_column(
                    name=col,
                    description=f"Average PSD for {label} state. Units: TODO (confirm with lab).",
                )

        n_rows = 10 if stub_test else len(df)
        for _, row in df.head(n_rows).iterrows():
            row_data = {"frequency_hz": float(row["hz"])}
            for col in _STATE_COLS:
                if col in df.columns:
                    row_data[col] = float(row[col])
            psd_table.add_row(**row_data)

        ecephys_module = get_module(nwbfile, "ecephys", "Processed electrophysiology data.")
        ecephys_module.add(psd_table)
