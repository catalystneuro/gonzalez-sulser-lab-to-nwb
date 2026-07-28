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
    electrode table but distinct ElectrodeGroups. The baseline windows (BL1,
    BL2, ...) within that recording are marked in the NWB epochs table
    (BaselineEpochs), which must run before all derived streams below since
    each aligns its per-file data to the epochs table rows. SleepStates,
    Seizures, SwdCounts, SeizureTotals, and StatePowerSpectrum each take one
    file per baseline window (ordered BL1, BL2, ...) and write a single
    merged table tagged with a "baseline_window" column, so all baselines
    coexist in one table in processing["behavior"] / processing["ecephys"].
    Temporal alignment is arithmetic (BL offset from xlsx) — no TTL sync
    needed. See conversion_notes.md § Temporal Alignment for full sync
    documentation.
    """

    data_interface_classes = dict(
        EEGRecording=TainiRecordingInterface,
        EMGRecording=TainiRecordingInterface,
        BaselineEpochs=BaselineEpochsInterface,
        SleepStates=SleepStateInterface,
        Seizures=SeizureInterface,
        SwdCounts=SwdCountsInterface,
        SeizureTotals=SeizureTotalsInterface,
        StatePowerSpectrum=StatePowerSpectrumInterface,
    )
