"""NWBConverter for the Gonzalez-Sulser GRIN2B chronic EEG dataset."""
from __future__ import annotations

from neuroconv import NWBConverter

from .interfaces.taini_recording_interface import TainiRecordingInterface
from .interfaces.sleep_state_interface import SleepStateInterface
from .interfaces.seizure_interface import (
    SeizureInterface,
    SwdCountsInterface,
    SeizureTotalsInterface,
)
from .interfaces.state_power_spectrum_interface import StatePowerSpectrumInterface


class Grin2bNWBConverter(NWBConverter):
    """Primary conversion class for one GRIN2B baseline session (BL1 or BL2).

    All streams in a session derive from a single TainiTec .dat file.
    Temporal alignment is arithmetic (BL offset from xlsx) — no TTL sync needed.
    See conversion_notes.md § Phase 4 for full sync documentation.
    """

    data_interface_classes = dict(
        Recording=TainiRecordingInterface,
        SleepStates=SleepStateInterface,
        Seizures=SeizureInterface,
        SwdCounts=SwdCountsInterface,
        SeizureTotals=SeizureTotalsInterface,
        StatePowerSpectrum=StatePowerSpectrumInterface,
    )
