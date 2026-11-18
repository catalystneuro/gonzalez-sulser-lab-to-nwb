"""Mean EEG spectrum per brain state over each baseline window, from the lab's sleep scorer.

Source: Sleep state classifications/<subject>/<subject>_BL{N}-pw_spectrum.csv, columns hz, s_0, s_1, s_2, s_4 with
a spurious first data row ("BL1, BL1, ..."), 628 rows from 0 to 125.2 Hz in 0.2 Hz steps. s_N is the mean spectrum
over the epochs of state N: 0 = Wake, 1 = NREM, 2 = REM, 4 = SWD. The lab's script did not produce a BL1 file for
GRIN2B_140 and GRIN2B_378. Units are derived from rat.spectr, rat.mtspec, rat.norm and rat.lsmth in
sleep_score_library.R (AUTOMATIC-SLEEP-SCORER); see the table description. Written to
processing/ecephys/sleep_state_power_spectra. Frequency-indexed, so the epochs table is only checked for the labels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .baseline_epochs_interface import BaseBaselineStreamInterface

STATE_COLUMNS = {"s_0": "Wake", "s_1": "NREM", "s_2": "REM", "s_4": "SWD"}
STATE_NAMES = {"Wake": "Wake", "NREM": "NREM sleep", "REM": "REM sleep", "SWD": "spike-wave discharge (SWD)"}


class StatePowerSpectrumInterface(BaseBaselineStreamInterface):
    """Per-brain-state mean spectra."""

    keywords = ["power spectrum", "EEG", "sleep", "PSD"]
    table_name = "sleep_state_power_spectra"
    module_name = "ecephys"
    table_description = (
        "Mean EEG spectrum per brain state over each 24-h baseline window, computed by the Gonzalez-Sulser lab sleep "
        "scorer (https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER, functions rat.spectr, rat.mtspec, "
        "rat.norm and rat.lsmth in sleep_score_library.R). The input is a single EEG channel in mV, selected by the "
        "experimenter during scoring (which channel is not recorded in the shared files), with packet-loss gaps "
        "interpolated. For each 5-s epoch a multitaper spectrum (6 DPSS tapers) is computed and converted to log10 "
        "amplitude as log10(power + 1e-6) / 2; each frequency is then normalized by subtracting its 5th percentile "
        "across all epochs of the window, and each epoch is averaged with its most similar epochs within +/-5 epochs. "
        "The state columns are means over the epochs scored as that state. Values are dimensionless log10 amplitude "
        "relative to the per-frequency 5th percentile (a difference of 0.1 is about a 26% change in amplitude), not "
        "an absolute power spectral density. Frequency bins from 0 to 125.2 Hz (Nyquist of 250.4 Hz) in 0.2 Hz steps. "
        "State columns: Wake, NREM, REM, SWD (spike-wave discharge epochs)."
    )
    column_descriptions = dict(
        frequency_hz="Frequency in Hz.",
        **{state: f"Mean normalized log10 amplitude spectrum over {name} epochs." for state, name in STATE_NAMES.items()},
    )

    def read_file(self, file_path: Path) -> pd.DataFrame:
        spectrum = pd.read_csv(file_path, skiprows=[1])
        spectrum = spectrum.rename(columns={spectrum.columns[0]: "frequency_hz", **STATE_COLUMNS})
        return spectrum.apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)
