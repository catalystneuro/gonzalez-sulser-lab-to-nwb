"""TainiTec wireless EEG/EMG recording (.dat).

Format, as in TainiTec's parse_dat.m (shipped in the lab's AUTOMATIC-SLEEP-SCORER repo):
16 channels interleaved sample by sample, int16 little-endian, no header, 250.4 Hz. Values are unsigned 12-bit ADC
codes (0-4095) over a 13 mV peak-to-peak range: 13000 / 4095 uV per code, with code 2047.5 = 0 V (parse_dat.m returns
0-13 mV; the offset centres it on 0 V). Radio packet loss is stored as code 32767 on all channels; it is kept
unchanged and documented in the series description.

The channel layout is from the lab's grin2b_eeg_channels.csv and the AP/ML coordinates from the lab's coordinate
table. EEG: custom H16-Rat EEG16 grid (NeuroNexus); EMG: trapezius muscle. In the electrode table, "location" is the
area of each electrode (full name and abbreviation, as in the paper), "channel_name" the lab's label and hemisphere
(e.g. "S1_Tr_R"), and "x" and "z" the stereotaxic position in microns from bregma, with the NWB axes: +x posterior,
+z right. The depth (NWB "y") of skull-surface electrodes is not defined, so there is no "y" column.

The interface writes the full recording of one signal type: instantiate it with signal_type="EEG" and again with
"EMG". Both share one electrode table (rows deduplicated by channel id) with separate ElectrodeGroups.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.utils import DeepDict
from spikeinterface.core import BinaryRecordingExtractor

SAMPLING_FREQUENCY = 250.4  # Hz; 21,634,560 samples = 24 h exactly
ADC_FULL_SCALE_UV = 13000.0
GAIN_TO_UV = ADC_FULL_SCALE_UV / 4095  # ~3.1746 uV per code
OFFSET_UV = -ADC_FULL_SCALE_UV / 2
MISSED_PACKET_CODE = 2**15 - 1

# (label, hemisphere) of the 16 .dat channels in file order.
CHANNELS = [
    ("S1_Tr", "R"), ("EMG", "R"), ("M2_Fra", "R"), ("M2_anterior", "R"),
    ("M1_anterior", "R"), ("V2_ML", "R"), ("V1_M", "R"), ("S1Hl_S1Fl", "R"),
    ("V1_M", "L"), ("V2_ML", "L"), ("S1Hl_S1Fl", "L"), ("M1_anterior", "L"),
    ("M2_anterior", "L"), ("M2_Fra", "L"), ("EMG", "L"), ("S1_Tr", "L"),
]  # fmt: skip
CHANNEL_IDS = [f"{label}_{hemisphere}" for label, hemisphere in CHANNELS]
# Area of each label, written to the electrode-table "location" column.
LOCATIONS = {
    "S1_Tr": "primary somatosensory cortex, trunk region (S1-Tr)",
    "S1Hl_S1Fl": "primary somatosensory cortex, hindlimb and forelimb regions (S1-HL/FL)",
    "M1_anterior": "primary motor cortex, anterior (M1-Ant)",
    "M2_anterior": "secondary motor cortex, anterior (M2-Ant)",
    "M2_Fra": "secondary motor cortex, frontal association area (M2-FrA)",
    "V1_M": "primary visual cortex, monocular area (V1-M)",
    "V2_ML": "secondary visual cortex, mediolateral area (V2-ML)",
    "EMG": "trapezius muscle",
}
# AP (anterior positive) and ML (unsigned) in mm from bregma; the same on both hemispheres. EMG channels have none.
COORDINATES_MM = {
    "V1_M": (-7.0, 3.0), "V2_ML": (-5.0, 3.0), "S1_Tr": (-3.0, 2.8), "S1Hl_S1Fl": (-1.0, 2.8),
    "M1_anterior": (1.5, 2.8), "M2_anterior": (1.5, 1.2), "M2_Fra": (3.6, 1.2),
}  # fmt: skip

DEVICE_KEY = "TainiTecWirelessEEG"
DEVICE_MODEL_KEY = "TainiTecTransmitter"
ELECTRODE_GROUPS = {
    "EEG": dict(
        name="EEGArray",
        location="cerebral cortex",
        description=(
            "14-channel chronic EEG skull-surface electrode grid, Custom H16-Rat EEG16 (NeuroNexus), 7 electrodes per "
            "hemisphere over somatosensory, motor and visual cortex. The area of each electrode is in the location "
            "column of the electrode table, and its stereotaxic position in the x (+ posterior) and z (+ right) "
            "columns, in microns from bregma."
        ),
    ),
    "EMG": dict(
        name="EMGArray",
        location="trapezius muscle",
        description="2-channel chronic EMG electrodes (right and left), placed in the trapezius muscle.",
    ),
}


class TainiRecordingInterface(BaseRecordingExtractorInterface):
    """The EEG or the EMG channels of a TainiTec .dat recording, written as one ElectricalSeries in acquisition.

    The electrode layout is set by the class attributes: channels (label and hemisphere of each .dat column, with
    "EMG" labelling the EMG channels), locations (area of each label), coordinates_mm (AP, ML of each EEG label),
    electrode_groups and device_description. For a line with another layout, subclass this interface and override
    them.
    """

    keywords = ["EEG", "EMG", "chronic", "TainiTec", "wireless"]
    channels: list[tuple[str, str]] = CHANNELS
    locations: dict[str, str] = LOCATIONS
    coordinates_mm: dict[str, tuple[float, float]] = COORDINATES_MM
    electrode_groups: dict[str, dict] = ELECTRODE_GROUPS
    device_description: str = (
        "TainiTec wireless EEG/EMG telemetry system. 16-channel headstage, Custom H16-Rat EEG16 grid "
        "(NeuroNexus). Sampling frequency 250.4 Hz, 12-bit ADC stored as int16 LE, 13 mV peak-to-peak "
        "full-scale range. The grid's plus-symbol reference point was aligned over bregma during "
        "implantation; all EEG electrodes are independent of one another and are not interconnected. A "
        "separate cerebellar ground screw (-11.5 mm AP, +/-0.5 mm ML from bregma) was connected to the "
        "grid via silver paint."
    )

    @classmethod
    def get_extractor_class(cls):
        return BinaryRecordingExtractor

    def _initialize_extractor(self, source_data: dict) -> BinaryRecordingExtractor:
        # The base class adds all_annotations=True, which BinaryRecordingExtractor does not accept.
        self.extractor_kwargs = dict(source_data)
        return BinaryRecordingExtractor(**self.extractor_kwargs)

    def __init__(self, file_path: str | Path, signal_type: Literal["EEG", "EMG"], verbose: bool = False):
        """
        Parameters
        ----------
        file_path : str or Path
            The TainiTec .dat file. The full file is written, starting at session_start_time.
        signal_type : "EEG" or "EMG"
            Which channels this instance writes.
        verbose : bool
        """
        if signal_type not in self.electrode_groups:
            raise ValueError(f"signal_type must be one of {list(self.electrode_groups)}, got {signal_type!r}")
        self.signal_type = signal_type
        channel_ids = [f"{label}_{hemisphere}" for label, hemisphere in self.channels]
        super().__init__(
            file_paths=[str(file_path)],
            sampling_frequency=SAMPLING_FREQUENCY,
            num_channels=len(self.channels),
            dtype="int16",
            channel_ids=channel_ids,
            verbose=verbose,
            metadata_key=f"{signal_type}ElectricalSeries",
        )

        # "brain_area" becomes the electrode-table "location" column. NWB's x is posterior and z right, in microns.
        recording = self.recording_extractor
        labels = [label for label, _ in self.channels]
        hemispheres = [hemisphere for _, hemisphere in self.channels]
        signal_types = ["EMG" if label == "EMG" else "EEG" for label in labels]
        n_channels = len(self.channels)
        ap_ml_mm = np.array([self.coordinates_mm.get(label, (np.nan, np.nan)) for label in labels])
        ml_sign = np.array([1.0 if hemisphere == "R" else -1.0 for hemisphere in hemispheres])
        recording.set_property("group_name", np.array([self.electrode_groups[s]["name"] for s in signal_types]))
        recording.set_property("brain_area", np.array([self.locations[label] for label in labels]))
        recording.set_property("hemisphere", np.array(hemispheres))
        recording.set_property("filtering", np.array(["none"] * n_channels))
        recording.set_property("x", -ap_ml_mm[:, 0] * 1000)
        recording.set_property("z", ml_sign * ap_ml_mm[:, 1] * 1000)
        recording.set_channel_gains(np.full(n_channels, GAIN_TO_UV))
        recording.set_channel_offsets(np.full(n_channels, OFFSET_UV))
        self.recording_extractor = recording.select_channels(
            [channel_id for channel_id, s in zip(channel_ids, signal_types) if s == signal_type]
        )

    def get_metadata(self) -> DeepDict:
        # NeuroConv's dict-based metadata: devices in a top-level "Devices" registry, electrode groups and series in
        # Ecephys keyed by metadata key. pynwb 4 holds the manufacturer in a DeviceModel. The EEG and EMG instances'
        # entries merge in the converter.
        metadata = super().get_metadata()
        metadata["DeviceModels"] = {
            DEVICE_MODEL_KEY: dict(
                name="TainiTec wireless EEG and EMG transmitter",
                manufacturer="TainiTec",
                description=(
                    "16-channel wireless telemetry transmitter, 12-bit ADC over a 13 mV peak-to-peak full-scale "
                    "range, 250.4 Hz sampling."
                ),
            )
        }
        metadata["Devices"] = {
            DEVICE_KEY: dict(
                name="TainiTecWirelessEEG",
                description=self.device_description,
                device_model_metadata_key=DEVICE_MODEL_KEY,
            )
        }
        group = self.electrode_groups[self.signal_type]
        metadata["Ecephys"]["ElectrodeGroups"] = {group["name"]: dict(group, device_metadata_key=DEVICE_KEY)}
        metadata["Ecephys"]["Electrodes"] = [
            dict(name="hemisphere", description="Hemisphere of the electrode: R (right) or L (left)."),
            dict(name="filtering", description="No hardware or software filtering applied by the conversion."),
            dict(
                name="x",
                description="Stereotaxic anterior-posterior position in microns from bregma, positive posterior "
                "(NWB convention). NaN for the EMG electrodes.",
            ),
            dict(
                name="z",
                description="Stereotaxic medial-lateral position in microns from bregma, positive right "
                "(NWB convention). NaN for the EMG electrodes.",
            ),
        ]
        duration_hours = self.recording_extractor.get_num_frames() / SAMPLING_FREQUENCY / 3600
        metadata["Ecephys"]["ElectricalSeries"][self.metadata_key] = dict(
            name=f"{self.signal_type}ElectricalSeries",
            description=(
                f"Full chronic {self.signal_type} recording ({duration_hours:.1f} h). BL1/BL2 baseline windows within "
                f"this recording are marked in the NWB epochs table. The data are the unsigned 12-bit TainiTec ADC "
                f"codes (0-4095); conversion and offset give volts over a 13 mV peak-to-peak full-scale range centred "
                f"on 0 V ({GAIN_TO_UV:.4f} uV/code, code 2047.5 = 0 V). A small number of samples (under 0.02%) lie "
                f"outside 0-4095, mostly just above 4095 at saturation plus occasional isolated corrupted values; they "
                f"are kept unchanged. Samples lost to radio packet loss are stored by the TainiTec system as the raw "
                f"value {MISSED_PACKET_CODE} on all channels at once "
                f"({(MISSED_PACKET_CODE * GAIN_TO_UV + OFFSET_UV) / 1000:.1f} mV after conversion) and are kept "
                f"unchanged; exclude raw values equal to {MISSED_PACKET_CODE} before analysis. The lab's own pipeline "
                f"sets these samples to 0 and interpolates over them."
            ),
        )
        return metadata
