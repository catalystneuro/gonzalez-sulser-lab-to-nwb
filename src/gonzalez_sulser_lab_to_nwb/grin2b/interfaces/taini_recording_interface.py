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

The 16 channels are written as two separate ElectricalSeries — one for the
14 EEG channels and one for the 2 EMG channels — sharing a single electrode
table but pointing at distinct ElectrodeGroups ("EEGArray" / "EMGArray").
To produce both series, instantiate this interface twice per session (once
with signal_type="EEG", once with signal_type="EMG"); both instances share
the same underlying .dat file and BL window, and the second call to append
electrodes reuses the table built by the first (electrodes are deduplicated
by channel id, so the table ends up with all 16 rows exactly once).

ADC full-scale range: 13 mV peak-to-peak (+/- 6.5 mV) over the 12-bit
(0-4095) range -> gain = 13000 uV / 4096 codes ~= 3.174 uV/code.
Applied via recording_extractor.set_channel_gains(); no per-channel
offset is applied.

Per-channel stereotaxic AP/ML coordinates (mm, bregma-referenced) were
provided keyed by (label, hemisphere) — see _STEREOTAXIC_COORDINATES_MM
below. EMG channels have no AP/ML target and are left as NaN.

EEG grid: Custom H16-Rat EEG16 (NeuroNexus); EMG electrodes placed in
the trapezius muscle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

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

# ADC gain — confirmed by TainiTec support.
# 12-bit ADC (0-4095 codes) spans a 13 mV peak-to-peak full-scale range (+/- 6.5 mV).
_ADC_BITS = 12
_ADC_FULL_SCALE_UV = 13000.0  # 13 mV peak-to-peak, in microvolts
_GAIN_TO_UV = _ADC_FULL_SCALE_UV / (2**_ADC_BITS)  # ~3.174 uV/code

# ---------------------------------------------------------------------------
# Channel layout — confirmed from grin2b_eeg_channels.csv (2026-06-19)
# Format: (python_channel_index, electrode_label, hemisphere, electrode_group)
# ---------------------------------------------------------------------------
_CHANNEL_MAP: list[tuple[int, str, str, str]] = [
    (0, "S1_Tr", "R", "EEGArray"),
    (1, "EMG", "R", "EMGArray"),
    (2, "M2_Fra", "R", "EEGArray"),
    (3, "M2_anterior", "R", "EEGArray"),
    (4, "M1_anterior", "R", "EEGArray"),
    (5, "V2_ML", "R", "EEGArray"),
    (6, "V1_M", "R", "EEGArray"),
    (7, "S1Hl_S1Fl", "R", "EEGArray"),
    (8, "V1_M", "L", "EEGArray"),
    (9, "V2_ML", "L", "EEGArray"),
    (10, "S1Hl_S1Fl", "L", "EEGArray"),
    (11, "M1_anterior", "L", "EEGArray"),
    (12, "M2_anterior", "L", "EEGArray"),
    (13, "M2_Fra", "L", "EEGArray"),
    (14, "EMG", "L", "EMGArray"),
    (15, "S1_Tr", "L", "EEGArray"),
]

# Unique channel IDs (label + hemisphere) for use as spikeinterface channel_ids
_CHANNEL_IDS = [f"{label}_{hemi}" for _, label, hemi, _ in _CHANNEL_MAP]

# ---------------------------------------------------------------------------
# Per-channel stereotaxic coordinates (AP, ML in mm, bregma-referenced).
# Keyed by (label, hemisphere) rather than TAINI/NNX pin or Python
# channel index — the lab's coordinate table uses TAINI/NNX pin numbering
# ---------------------------------------------------------------------------
_STEREOTAXIC_COORDINATES_MM: dict[tuple[str, str], tuple[float, float]] = {
    ("V1_M", "L"): (-7.0, 3.0),
    ("V2_ML", "L"): (-5.0, 3.0),
    ("S1_Tr", "L"): (-3.0, 2.8),
    ("S1Hl_S1Fl", "L"): (-1.0, 2.8),
    ("M1_anterior", "L"): (1.5, 2.8),
    ("M2_anterior", "L"): (1.5, 1.2),
    ("M2_Fra", "L"): (3.6, 1.2),
    ("M2_Fra", "R"): (3.6, 1.2),
    ("M2_anterior", "R"): (1.5, 1.2),
    ("M1_anterior", "R"): (1.5, 2.8),
    ("S1Hl_S1Fl", "R"): (-1.0, 2.8),
    ("S1_Tr", "R"): (-3.0, 2.8),
    ("V2_ML", "R"): (-5.0, 3.0),
    ("V1_M", "R"): (-7.0, 3.0),
}

# Electrode group name -> ElectricalSeries name prefix
_SIGNAL_TYPE_TO_GROUP = {"EEG": "EEGArray", "EMG": "EMGArray"}


class TainiRecordingInterface(BaseRecordingExtractorInterface):
    """Interface for TainiTec chronic EEG/EMG .dat recordings.

    Writes one signal type (EEG or EMG) of a single baseline window (BL1 or
    BL2) as an ElectricalSeries in the NWB acquisition group. Both signal
    types share the same 16-channel .dat file and electrode table but are
    written as separate ElectricalSeries under separate ElectrodeGroups —
    instantiate this interface once per signal_type to get both.
    Inherits the full neuroconv recording pipeline (electrode table, chunked
    HDF5 compression, etc.) via BaseRecordingExtractorInterface.
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
        signal_type: Literal["EEG", "EMG"],
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
        signal_type : "EEG" or "EMG"
            Which subset of the 16 channels this interface instance writes.
        baseline_name : str
            Label for this window, e.g. "BL1" or "BL2".
        verbose : bool
            Passed to the underlying spikeinterface extractor.
        """
        if signal_type not in _SIGNAL_TYPE_TO_GROUP:
            raise ValueError(
                f"signal_type must be one of {list(_SIGNAL_TYPE_TO_GROUP)}, got {signal_type!r}"
            )

        self.bl_start_sample = bl_start_sample
        self.bl_stop_sample = bl_stop_sample
        self.signal_type = signal_type
        self.baseline_name = baseline_name
        self._electrode_group_name = _SIGNAL_TYPE_TO_GROUP[signal_type]

        super().__init__(
            file_paths=[str(file_path)],
            sampling_frequency=_FS,
            num_channels=_N_CHANNELS,
            dtype=_DTYPE,
            channel_ids=_CHANNEL_IDS,
            verbose=verbose,
            es_key=f"{signal_type}ElectricalSeries",
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
        labels = [label for _, label, _, _ in _CHANNEL_MAP]
        hemispheres = [hemi for _, _, hemi, _ in _CHANNEL_MAP]
        groups = [grp for _, _, _, grp in _CHANNEL_MAP]
        filterings = ["none"] * _N_CHANNELS  # raw, no hardware filter applied by us

        # XY electrode positions (AP, ML in mm, bregma-referenced).
        xy = np.full((_N_CHANNELS, 2), fill_value=np.nan, dtype=float)
        for i, (_, label, hemi, _grp) in enumerate(_CHANNEL_MAP):
            coord = _STEREOTAXIC_COORDINATES_MM.get((label, hemi))
            if coord is not None:
                xy[i] = coord

        self.recording_extractor.set_property("group_name", np.array(groups))
        self.recording_extractor.set_property("brain_area", np.array(labels))
        self.recording_extractor.set_property("hemisphere", np.array(hemispheres))
        self.recording_extractor.set_property("filtering", np.array(filterings))
        self.recording_extractor.set_property("location", xy)

        # 12-bit ADC over a 13 mV peak-to-peak full-scale range. Applied uniformly
        # to all channels. Offset is set to 0 (must still be set explicitly).
        self.recording_extractor.set_channel_gains(np.full(_N_CHANNELS, _GAIN_TO_UV))
        self.recording_extractor.set_channel_offsets(np.zeros(_N_CHANNELS))

        # Restrict to only the channels belonging to this signal type. Properties
        # set above are carried over by select_channels, and the electrode table
        # rows for the other signal type's channels are added by that other
        # interface instance (same shared electrode table, deduplicated by
        # channel id).
        channel_ids_for_type = [
            channel_id
            for channel_id, (_, _, _, grp) in zip(_CHANNEL_IDS, _CHANNEL_MAP)
            if grp == self._electrode_group_name
        ]
        self.recording_extractor = self.recording_extractor.select_channels(
            channel_ids=channel_ids_for_type
        )

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        metadata["Ecephys"]["Device"] = [
            {
                "name": "TainiTecWirelessEEG",
                "description": (
                    "TainiTec wireless EEG/EMG telemetry system. "
                    "16-channel headstage, Custom H16-Rat EEG16 grid (NeuroNexus). "
                    "Sampling frequency 250.4 Hz, 12-bit ADC stored as int16 LE, "
                    "13 mV peak-to-peak full-scale range."
                ),
                "manufacturer": "TainiTec",
            }
        ]

        # Fix device reference in auto-generated electrode groups
        for grp in metadata["Ecephys"]["ElectrodeGroup"]:
            grp["device"] = "TainiTecWirelessEEG"
            if grp["name"] == "EEGArray":
                grp["description"] = (
                    "14-channel chronic EEG electrode array, Custom H16-Rat EEG16 "
                    "(NeuroNexus). Channels cover bilateral cortex: S1_Tr, M2_Fra, "
                    "M2_anterior, M1_anterior, V2_ML, V1_M, S1Hl_S1Fl (right and left "
                    "hemispheres), at stereotaxic AP/ML coordinates from bregma "
                    "confirmed by the lab (see electrode table 'location' column)."
                )
                grp["location"] = "cortex"
            elif grp["name"] == "EMGArray":
                grp["description"] = (
                    "2-channel chronic EMG electrodes (right and left), placed in the "
                    "trapezius muscle."
                )
                grp["location"] = "trapezius muscle"

        n_samples = self.bl_stop_sample - self.bl_start_sample + 1
        duration_hours = n_samples / _FS / 3600
        metadata["Ecephys"][self.es_key] = {
            "name": f"{self.signal_type}ElectricalSeries{self.baseline_name}",
            "description": (
                f"Chronic {self.signal_type} recording, {self.baseline_name} window "
                f"({duration_hours:.1f} h). Values converted to volts using a "
                f"TainiTec 12-bit ADC over a 13 mV peak-to-peak full-scale range "
                f"({_GAIN_TO_UV:.4f} uV/code)."
            ),
        }

        return metadata
