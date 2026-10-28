"""Per-sleep-state power spectrum interface.

Source file(s): `<subject_dir>/<subject_id>_BL{N}-pw_spectrum.csv`, one per
baseline window, keyed by baseline label (the epochs-table tag). The lab's
script did not produce a BL1 file for GRIN2B_140 and GRIN2B_378; those
animals carry the BL2 spectrum only.
  - 628 rows (0.2 Hz steps from 0 to 125.2 Hz = Nyquist of 250.4 Hz)
  - Columns: hz, s_0, s_1, s_2, s_4
  - s_N = mean spectrum over the epochs of brain state N
  - State codes confirmed (Hristova et al. 2025 supplementary):
      0 = Wake, 1 = NREM, 2 = REM,
      4 = SWD (spike-wave discharge epochs, classed separately from sleep states)
  - Units, from rat.spectr / rat.mtspec / rat.norm / rat.lsmth in the lab's
    sleep_score_library.R (AUTOMATIC-SLEEP-SCORER repo): per-5-s-epoch multitaper
    spectrum of one EEG channel in mV, as log10(power + 1e-6) / 2 (log10 amplitude),
    minus each frequency's 5th percentile across the window's epochs, smoothed
    across similar neighbouring epochs. Dimensionless, not an absolute PSD.

Written as a single DynamicTable in processing["ecephys"] with one row per
(baseline window, frequency bin) and one column per brain state, plus a
"baseline_window" column. There is no time axis for this data (it's
frequency-indexed, not aligned to the recording clock), so the NWB epochs
table (added by BaselineEpochsInterface, which must run first) is only
checked to contain each baseline label.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from hdmf.common import DynamicTable
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict
from pynwb import NWBFile

from .baseline_epochs_interface import get_baseline_start_times

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
    "Wake": "Mean normalized log10 amplitude spectrum over Wake epochs.",
    "NREM": "Mean normalized log10 amplitude spectrum over NREM sleep epochs.",
    "REM": "Mean normalized log10 amplitude spectrum over REM sleep epochs.",
    "SWD": "Mean normalized log10 amplitude spectrum over spike-wave discharge (SWD) epochs.",
}


class StatePowerSpectrumInterface(BaseDataInterface):
    """Interface for per-sleep-state average power spectra."""

    keywords = ["power spectrum", "EEG", "sleep", "PSD"]

    def __init__(self, file_paths: dict[str, str | Path]):
        """
        Parameters
        ----------
        file_paths : dict of str to str or Path
            Paths to `*-pw_spectrum.csv` files keyed by baseline label (the
            epochs-table tag, e.g. "baseline_window_1").
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
        get_baseline_start_times(nwbfile, list(self.file_paths), "StatePowerSpectrumInterface")

        # Read all files up front so the merged table's columns (the union of state
        # columns actually present across baseline windows) are known before any
        # row is added — DynamicTable requires every row to fill every column.
        dfs = []
        for file_path in self.file_paths.values():
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
                "Mean EEG spectrum per brain state over each 24-h baseline window, computed by the "
                "Gonzalez-Sulser lab sleep scorer "
                "(https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER, functions rat.spectr, "
                "rat.mtspec, rat.norm and rat.lsmth in sleep_score_library.R). The input is a single "
                "EEG channel in mV, selected by the experimenter during scoring (which channel is not "
                "recorded in the shared files), with packet-loss gaps interpolated. For each 5-s epoch "
                "a multitaper spectrum (6 DPSS tapers) is computed and converted to log10 amplitude as "
                "log10(power + 1e-6) / 2; each frequency is then normalized by subtracting its 5th "
                "percentile across all epochs of the window, and each epoch is averaged with its most "
                "similar epochs within +/-5 epochs. The state columns are means over the epochs scored "
                "as that state. Values are dimensionless log10 amplitude relative to the per-frequency "
                "5th percentile (a difference of 0.1 is about a 26% change in amplitude), not an "
                "absolute power spectral density. "
                "Frequency bins from 0 to 125.2 Hz (Nyquist of 250.4 Hz) in 0.2 Hz steps. "
                "State columns: Wake, NREM, REM, SWD (spike-wave discharge epochs)."
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

        for baseline_label, df in zip(self.file_paths, dfs):
            n_rows = 10 if stub_test else len(df)
            for _, row in df.head(n_rows).iterrows():
                row_data = {"frequency_hz": float(row["hz"]), "baseline_window": baseline_label}
                for col, label in _STATE_COLS.items():
                    if label in state_labels:
                        row_data[label] = float(row[col]) if col in df.columns else float("nan")
                psd_table.add_row(**row_data)

        ecephys_module = get_module(nwbfile, "ecephys", "Processed electrophysiology data.")
        ecephys_module.add(psd_table)
