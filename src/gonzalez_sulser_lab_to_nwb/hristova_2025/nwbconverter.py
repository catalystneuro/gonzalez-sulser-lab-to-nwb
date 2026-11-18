"""NWBConverter of the Hristova et al. 2025 GRIN2B dataset: one NWB file per subject."""

from neuroconv import NWBConverter

from .interfaces import (
    BaselineEpochsInterface,
    SeizureInterface,
    SeizureTotalsInterface,
    SleepStateInterface,
    StatePowerSpectrumInterface,
    SwdEpochsInterface,
    TainiRecordingInterface,
)


class Hristova2025NWBConverter(NWBConverter):
    """The full raw EEG and EMG recording, the baseline windows, and the lab's per-window derived streams.

    BaselineEpochs must come before the per-window streams, which align to its epochs-table rows.
    """

    data_interface_classes = dict(
        EEGRecording=TainiRecordingInterface,
        EMGRecording=TainiRecordingInterface,
        BaselineEpochs=BaselineEpochsInterface,
        SleepStates=SleepStateInterface,
        Seizures=SeizureInterface,
        SwdEpochs=SwdEpochsInterface,
        SeizureTotals=SeizureTotalsInterface,
        StatePowerSpectrum=StatePowerSpectrumInterface,
    )
