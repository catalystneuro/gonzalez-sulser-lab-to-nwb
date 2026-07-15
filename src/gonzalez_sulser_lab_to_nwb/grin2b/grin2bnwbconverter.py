"""NWBConverter for the Gonzalez-Sulser GRIN2B chronic EEG dataset."""

from __future__ import annotations

from neuroconv import NWBConverter

from .interfaces.taini_recording_interface import TainiRecordingInterface
from .interfaces.baseline_epochs_interface import BaselineEpochsInterface
from .interfaces.sleep_state_interface import SleepStateInterface
from .interfaces.seizure_interface import (
    SeizureInterface,
    SwdCountsInterface,
    SeizureTotalsInterface,
)
from .interfaces.state_power_spectrum_interface import StatePowerSpectrumInterface


class Grin2bNWBConverter(NWBConverter):
    """Primary conversion class for one GRIN2B subject.

    All streams derive from a single TainiTec .dat file per animal. The
    16-channel *full* recording is written as two ElectricalSeries —
    EEGRecording (14 channels) and EMGRecording (2 channels) — sharing one
    electrode table but distinct ElectrodeGroups. The BL1/BL2 baseline
    windows within that recording are marked in the NWB epochs table
    (BaselineEpochs). Each derived sleep/seizure stream is instantiated once
    per available baseline window (suffix `_BL1`/`_BL2` in source_data keys),
    writing distinctly-named NWB objects
    (suffixed `_baseline_window_1`/`_baseline_window_2`) into
    processing["behavior"] / processing["ecephys"] so both baselines coexist
    in the same file. Temporal alignment is arithmetic (BL offset from xlsx)
    — no TTL sync needed. See conversion_notes.md § Temporal Alignment for
    full sync documentation.
    """

    data_interface_classes = dict(
        EEGRecording=TainiRecordingInterface,
        EMGRecording=TainiRecordingInterface,
        BaselineEpochs=BaselineEpochsInterface,
        SleepStates_BL1=SleepStateInterface,
        SleepStates_BL2=SleepStateInterface,
        Seizures_BL1=SeizureInterface,
        Seizures_BL2=SeizureInterface,
        SwdCounts_BL1=SwdCountsInterface,
        SwdCounts_BL2=SwdCountsInterface,
        SeizureTotals_BL1=SeizureTotalsInterface,
        SeizureTotals_BL2=SeizureTotalsInterface,
        StatePowerSpectrum_BL1=StatePowerSpectrumInterface,
        StatePowerSpectrum_BL2=StatePowerSpectrumInterface,
    )
