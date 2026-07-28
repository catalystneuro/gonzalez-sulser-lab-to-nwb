"""Per-sleep-state power spectrum interface.

Source file(s): `<subject_dir>/<subject_id>_BL{N}-pw_spectrum.csv`, one per
baseline window, ordered in time (BL1, BL2, ...).
  - 628 rows (0.2 Hz steps from 0 to 125.2 Hz = Nyquist of 250.4 Hz)
  - Columns: hz, s_0, s_1, s_2, s_4
  - s_N = average power spectral density for brain state N
  - State codes confirmed (Hristova et al. 2025 supplementary):
      0 = Wake, 1 = NREM, 2 = REM,
      4 = SWD (spike-wave discharge epochs, classed separately from sleep states)
  - TODO: confirm units (µV²/Hz? normalised? baseline-corrected?)

Written as a single DynamicTable in processing["ecephys"] with one row per
(baseline window, frequency bin) and one column per brain state, plus a
"baseline_window" column. There is no time axis for this data (it's
frequency-indexed, not aligned to the recording clock), so the NWB epochs
table (added by BaselineEpochsInterface, which must run first) is only
consulted for the baseline_window tag, matched positionally: the first
file_path aligns to the first epoch, and so on.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from hdmf.common import DynamicTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile

# State code mapping confirmed from Hristova et al. 2025 supplementary methods.
# State 4 = SWD epochs (classed separately from the three sleep states).
# Maps the raw CSV column name to the actual state name used as the NWB column name.
_STATE_COLS = {
    "s_0": "Wake",
    "s_1": "NREM",
    "s_2": "REM",
    "s_4": "SWD",
}

_STATE_DESCRIPTIONS = {
    "Wake": "Average baseline-corrected PSD during Wake epochs.",
    "NREM": "Average baseline-corrected PSD during NREM sleep epochs.",
    "REM": "Average baseline-corrected PSD during REM sleep epochs.",
    "SWD": "Average baseline-corrected PSD during spike-wave discharge (SWD/seizure) epochs.",
}


class StatePowerSpectrumInterface(BaseDataInterface):
    """Interface for per-sleep-state average power spectra."""

    keywords = ["power spectrum", "EEG", "sleep", "PSD"]

    def __init__(self, file_paths: list[str | Path]):
        """
        Parameters
        ----------
        file_paths : list of str or Path
            Paths to `*-pw_spectrum.csv` files, one per baseline window,
            ordered in time (BL1, BL2, ...) to match the order of rows in the
            NWB epochs table.
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
        if nwbfile.epochs is None:
            raise ValueError(
                "StatePowerSpectrumInterface requires the NWB epochs table to already "
                "contain the baseline windows (add BaselineEpochsInterface earlier in "
                "the converter)."
            )
        epochs_df = nwbfile.epochs.to_dataframe()
        if len(epochs_df) != len(self.file_paths):
            raise ValueError(
                f"Got {len(self.file_paths)} power-spectrum CSV file(s) but "
                f"{len(epochs_df)} baseline window(s) in the NWB epochs table. Provide "
                "exactly one CSV per baseline window, ordered to match the epochs table."
            )

        # Read all files up front so the merged table's columns (the union of state
        # columns actually present across baseline windows) are known before any
        # row is added — DynamicTable requires every row to fill every column.
        dfs = []
        for file_path in self.file_paths:
            # The CSV has a spurious first data row of "BL1, BL1, ..." — skip it.
            df = pd.read_csv(file_path, skiprows=[1])
            df.columns = ["hz"] + list(df.columns[1:])
            # Convert to numeric, coercing any remaining header artifacts.
            df = df.apply(pd.to_numeric, errors="coerce").dropna()
            dfs.append(df)

        state_labels = [label for col, label in _STATE_COLS.items() if any(col in df.columns for df in dfs)]

        psd_table = DynamicTable(
            name="sleep_state_power_spectra",
            description=(
                "Average power spectral density per brain state, computed by the "
                "Gonzalez-Sulser lab automated scoring pipeline "
                "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). "
                "Frequency bins from 0 to 125.2 Hz (Nyquist of 250.4 Hz) in 0.2 Hz steps. "
                "State columns: Wake, NREM, REM, SWD (spike-wave discharge epochs). "
                "Spectra are baseline-corrected by normalizing to the average spectral power "
                "across REM, NREM, and wake for each animal. "
                "TODO: confirm absolute units (µV^2/Hz or normalised)."
            ),
        )
        psd_table.add_column(name="frequency_hz", description="Frequency in Hz.")
        for label in state_labels:
            psd_table.add_column(
                name=label,
                description=_STATE_DESCRIPTIONS.get(label, f"Average PSD for {label} state."),
            )
        psd_table.add_column(
            name="baseline_window",
            description="Baseline window (epochs-table tag) this row belongs to.",
        )

        for file_path, df, (_, epoch_row) in zip(self.file_paths, dfs, epochs_df.iterrows()):
            baseline_label = epoch_row["tags"][0] if len(epoch_row["tags"]) else ""

            n_rows = 10 if stub_test else len(df)
            for _, row in df.head(n_rows).iterrows():
                row_data = {"frequency_hz": float(row["hz"]), "baseline_window": baseline_label}
                for col, label in _STATE_COLS.items():
                    if label in state_labels:
                        row_data[label] = float(row[col]) if col in df.columns else float("nan")
                psd_table.add_row(**row_data)

        ecephys_module = get_module(nwbfile, "ecephys", "Processed electrophysiology data.")
        ecephys_module.add(psd_table)
