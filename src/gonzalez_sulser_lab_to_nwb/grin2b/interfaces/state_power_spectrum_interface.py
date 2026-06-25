"""Per-sleep-state power spectrum interface.

Source file: `<subject_dir>/<subject_id>_BL{N}-pw_spectrum.csv`
  - 628 rows (0.2 Hz steps from 0 to 125.2 Hz = Nyquist of 250.4 Hz)
  - Columns: hz, s_0, s_1, s_2, s_4
  - s_N = average power spectral density for brain state N
  - State codes confirmed (Hristova et al. 2025 supplementary):
      0 = Wake, 1 = NREM, 2 = REM,
      4 = SWD (spike-wave discharge epochs, classed separately from sleep states)
  - TODO: confirm units (µV²/Hz? normalised? baseline-corrected?)

Written as a DynamicTable in processing["ecephys"] with one row per
frequency bin and one column per brain state.
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

# State code mapping confirmed from Hristova et al. 2025 supplementary methods.
# State 4 = SWD epochs (classed separately from the three sleep states).
_STATE_COLS = {
    "s_0": "Wake",
    "s_1": "NREM",
    "s_2": "REM",
    "s_4": "SWD",
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
                "Average power spectral density per brain state, computed by the "
                "Gonzalez-Sulser lab automated scoring pipeline "
                "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). "
                "Frequency bins from 0 to 125.2 Hz (Nyquist of 250.4 Hz) in 0.2 Hz steps. "
                "State columns: s_0=Wake, s_1=NREM, s_2=REM, s_4=SWD (spike-wave discharge epochs). "
                "Spectra are baseline-corrected by normalizing to the average spectral power "
                "across REM, NREM, and wake for each animal. "
                "TODO: confirm absolute units (µV^2/Hz or normalised)."
            ),
        )
        psd_table.add_column(name="frequency_hz", description="Frequency in Hz.")
        _STATE_DESCRIPTIONS = {
            "s_0": "Average baseline-corrected PSD during Wake epochs.",
            "s_1": "Average baseline-corrected PSD during NREM sleep epochs.",
            "s_2": "Average baseline-corrected PSD during REM sleep epochs.",
            "s_4": "Average baseline-corrected PSD during spike-wave discharge (SWD/seizure) epochs.",
        }
        for col, label in _STATE_COLS.items():
            if col in df.columns:
                psd_table.add_column(
                    name=col,
                    description=_STATE_DESCRIPTIONS.get(col, f"Average PSD for {label} state."),
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
