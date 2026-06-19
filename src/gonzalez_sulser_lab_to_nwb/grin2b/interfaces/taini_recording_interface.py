"""TainiTec wireless EEG/EMG recording interface.

Wraps spikeinterface.core.BinaryRecordingExtractor for the proprietary TainiTec
binary .dat format:
  - int16 little-endian
  - 16 channels interleaved sample-by-sample
  - No file header
  - Sampling frequency: 250.4 Hz
  - 12-bit ADC range: [0, 4095] stored as int16

Channel layout confirmed from grin2b_eeg_channels.csv (2026-06-19):
  idx 0:  S1_Tr,         Right, EEG
  idx 1:  EMG,           Right, EMG
  idx 2:  M2_Fra,        Right, EEG
  idx 3:  M2_anterior,   Right, EEG
  idx 4:  M1_anterior,   Right, EEG
  idx 5:  V2_ML,         Right, EEG
  idx 6:  V1_M,          Right, EEG
  idx 7:  S1Hl_S1Fl,     Right, EEG
  idx 8:  V1_M,          Left,  EEG
  idx 9:  V2_ML,         Left,  EEG
  idx 10: S1Hl_S1Fl,     Left,  EEG
  idx 11: M1_anterior,   Left,  EEG
  idx 12: M2_anterior,   Left,  EEG
  idx 13: M2_Fra,        Left,  EEG
  idx 14: EMG,           Left,  EMG
  idx 15: S1_Tr,         Left,  EEG

Only the requested baseline window (BL1 or BL2) is written to NWB.
The window is expressed as sample indices into the .dat file and comes
from Sample_start_end_GRIN2B.xlsx.

TODO (pending lab reply):
  - Confirm ADC → volts gain (gain_to_uV / channel_conversion parameter)
  - NeuroNexus EEG grid model number and per-channel anatomical targets
  - EMG electrode placement (neck? trapezius?)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import (
    BaseRecordingExtractorInterface,
)
from neuroconv.utils import DeepDict
from spikeinterface.core import BinaryRecordingExtractor

# ---------------------------------------------------------------------------
# Recording constants
# ---------------------------------------------------------------------------
_N_CHANNELS = 16
_FS = 250.4  # Hz — confirmed by inspection (21,634,560 samples = 24 h exactly)
_DTYPE = "int16"

# ---------------------------------------------------------------------------
# Channel layout — confirmed from grin2b_eeg_channels.csv (2026-06-19)
# Format: (python_channel_index, electrode_label, hemisphere, electrode_group)
# ---------------------------------------------------------------------------
_CHANNEL_MAP: list[tuple[int, str, str, str]] = [
    (0,  "S1_Tr",       "R", "EEGArray"),
    (1,  "EMG",         "R", "EMGArray"),
    (2,  "M2_Fra",      "R", "EEGArray"),
    (3,  "M2_anterior", "R", "EEGArray"),
    (4,  "M1_anterior", "R", "EEGArray"),
    (5,  "V2_ML",       "R", "EEGArray"),
    (6,  "V1_M",        "R", "EEGArray"),
    (7,  "S1Hl_S1Fl",   "R", "EEGArray"),
    (8,  "V1_M",        "L", "EEGArray"),
    (9,  "V2_ML",       "L", "EEGArray"),
    (10, "S1Hl_S1Fl",   "L", "EEGArray"),
    (11, "M1_anterior", "L", "EEGArray"),
    (12, "M2_anterior", "L", "EEGArray"),
    (13, "M2_Fra",      "L", "EEGArray"),
    (14, "EMG",         "L", "EMGArray"),
    (15, "S1_Tr",       "L", "EEGArray"),
]

# Unique channel IDs (label + hemisphere) for use as spikeinterface channel_ids
_CHANNEL_IDS = [f"{label}_{hemi}" for _, label, hemi, _ in _CHANNEL_MAP]


class TainiRecordingInterface(BaseRecordingExtractorInterface):
    """Interface for TainiTec chronic EEG/EMG .dat recordings.

    Writes a single baseline window (BL1 or BL2) as an ElectricalSeries
    in the NWB acquisition group. Inherits the full neuroconv recording pipeline
    (electrode table, chunked HDF5 compression, etc.) via
    BaseRecordingExtractorInterface.
    """

    Extractor = BinaryRecordingExtractor
    keywords = ["EEG", "EMG", "chronic", "TainiTec", "wireless"]

    @classmethod
    def get_extractor_class(cls):
        return BinaryRecordingExtractor

    def _initialize_extractor(self, source_data: dict) -> BinaryRecordingExtractor:
        # The default BaseRecordingExtractorInterface._initialize_extractor adds
        # all_annotations=True, which BinaryRecordingExtractor does not accept.
        # Override to pass only the valid extractor kwargs.
        self.extractor_kwargs = dict(source_data)
        return BinaryRecordingExtractor(**self.extractor_kwargs)

    def __init__(
        self,
        file_path: str | Path,
        bl_start_sample: int,
        bl_stop_sample: int,
        baseline_name: str = "BL1",
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        file_path : str or Path
            Path to the TainiTec .dat binary file.
        bl_start_sample : int
            Zero-based sample index where the baseline window starts (xlsx "Start").
        bl_stop_sample : int
            Inclusive last sample index of the baseline window (xlsx "End").
        baseline_name : str
            Label for this window, e.g. "BL1" or "BL2".
        verbose : bool
            Passed to the underlying spikeinterface extractor.
        """
        self.bl_start_sample = bl_start_sample
        self.bl_stop_sample = bl_stop_sample
        self.baseline_name = baseline_name

        super().__init__(
            file_paths=[str(file_path)],
            sampling_frequency=_FS,
            num_channels=_N_CHANNELS,
            dtype=_DTYPE,
            channel_ids=_CHANNEL_IDS,
            verbose=verbose,
        )

        # Slice to BL window — lazy, no data read at construction time
        self.recording_extractor = self.recording_extractor.frame_slice(
            start_frame=bl_start_sample,
            end_frame=bl_stop_sample + 1,
        )

        # Annotate t_start so neuroconv sets ElectricalSeries.starting_time correctly
        self.recording_extractor.annotate(t_start=bl_start_sample / _FS)

        # Set per-channel properties (become columns in the NWB electrodes table).
        # NOTE: "location" in spikeinterface means 2D XY electrode coordinates (float,
        # shape (n_ch, 2)). Brain-area strings go in "brain_area"; neuroconv maps that
        # to the NWB electrode "location" column.
        labels      = [label for _, label, _, _ in _CHANNEL_MAP]
        hemispheres = [hemi  for _, _, hemi, _  in _CHANNEL_MAP]
        groups      = [grp   for _, _, _, grp   in _CHANNEL_MAP]
        filterings  = ["none"] * _N_CHANNELS  # raw, no hardware filter applied by us

        # XY electrode positions in mm — NaN until lab provides NeuroNexus grid coordinates.
        # TODO: replace with actual (x, y) positions from NeuroNexus grid layout.
        xy_placeholder = np.full((_N_CHANNELS, 2), fill_value=np.nan, dtype=float)

        self.recording_extractor.set_property("group_name",  np.array(groups))
        self.recording_extractor.set_property("brain_area",  np.array(labels))
        self.recording_extractor.set_property("hemisphere",  np.array(hemispheres))
        self.recording_extractor.set_property("filtering",   np.array(filterings))
        self.recording_extractor.set_property("location",    xy_placeholder)

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        metadata["Ecephys"]["Device"] = [
            {
                "name": "TainiTecWirelessEEG",
                "description": (
                    "TainiTec wireless EEG/EMG telemetry system. "
                    "16-channel headstage. "
                    "Sampling frequency 250.4 Hz, 12-bit ADC stored as int16 LE."
                ),
                "manufacturer": "TainiTec",
            }
        ]

        # Fix device reference in auto-generated electrode groups
        for grp in metadata["Ecephys"]["ElectrodeGroup"]:
            grp["device"] = "TainiTecWirelessEEG"
            if grp["name"] == "EEGArray":
                grp["description"] = (
                    "14-channel chronic EEG electrode array (NeuroNexus grid). "
                    "Channels cover bilateral cortex: S1_Tr, M2_Fra, M2_anterior, "
                    "M1_anterior, V2_ML, V1_M, S1Hl_S1Fl (right and left hemispheres). "
                    "TODO: add NeuroNexus model number and anatomical coordinates per channel."
                )
                grp["location"] = "cortex"
            elif grp["name"] == "EMGArray":
                grp["description"] = (
                    "2-channel chronic EMG electrodes (right and left). "
                    "TODO: confirm placement (neck / trapezius?)."
                )
                grp["location"] = "muscle"

        n_samples = self.bl_stop_sample - self.bl_start_sample + 1
        metadata["Ecephys"]["ElectricalSeries"] = {
            "name": f"ElectricalSeries_{self.baseline_name}",
            "description": (
                f"Chronic EEG/EMG recording, {self.baseline_name} window "
                f"({n_samples / _FS / 3600:.1f} h). "
                f"Channel layout confirmed from grin2b_eeg_channels.csv: "
                f"14 EEG channels (indices 0,2-13,15) and 2 EMG channels (indices 1,14). "
                f"ADC gain (conversion) is a placeholder — TODO: confirm with lab."
            ),
        }

        return metadata
