"""Conversions must follow the conventions of the lab's own analysis code.

Scaling follows TainiTec's parse_dat.m; the DGE_SWDs and Seiz_Totals layouts follow
cepstral_analysis.m; the sleep codes and sample indexing follow Sleep_autoscore_Beta.R and
Taini_CheckChoose.m (all in Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER).
"""

from datetime import datetime, timezone

import numpy as np
import openpyxl
import pytest
from pynwb import NWBFile

from gonzalez_sulser_lab_to_nwb.grin2b.convert_session import _load_bl_windows
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.baseline_epochs_interface import BaselineEpochsInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.seizure_interface import SeizureTotalsInterface, SwdEpochsInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.sleep_state_interface import SleepStateInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.taini_recording_interface import TainiRecordingInterface

FS = 250.4


@pytest.fixture
def nwbfile():
    nwbfile = NWBFile(
        session_description="test",
        identifier="test",
        session_start_time=datetime(2021, 3, 26, tzinfo=timezone.utc),
    )
    BaselineEpochsInterface(
        baseline_windows=[{"baseline_window_1": {"start_sample": 0, "stop_sample": 999}}], sampling_frequency=FS
    ).add_to_nwbfile(nwbfile, metadata={})
    return nwbfile


def test_scaling_matches_lab_channels_csv(tmp_path):
    # GRIN2B_129_BL1_Channels.csv stores raw code 2594 as 8.23492063492063 mV (13 mV / 4095 per code,
    # 0-13 mV). The conversion centres the 13 mV range on 0 V, i.e. subtracts 6.5 mV.
    dat = tmp_path / "TAINI_1047_B_Grin2B_129_Baseline-2021_03_26-0000.dat"
    np.full((3, 16), 2594, dtype="<i2").tofile(dat)

    recording = TainiRecordingInterface(file_path=dat, signal_type="EEG").recording_extractor
    traces_uv = recording.get_traces(return_in_uV=True)

    assert traces_uv[0, 0] == pytest.approx(8234.92063492063 - 6500.0, abs=0.01)


def test_xlsx_sample_numbers_are_converted_to_zero_based(tmp_path):
    # The xlsx Start/End are 1-based (MATLAB); the lab's Channels.csv starts at .dat index Start - 1.
    xlsx = tmp_path / "Light cycle timing metadata" / "Sample_start_end_GRIN2B.xlsx"
    xlsx.parent.mkdir()
    workbook = openpyxl.Workbook()
    workbook.active.append(["Animal ID", "Line", "File", "Baseline", "Start", "End"])
    workbook.active.append([129, "GRIN2B", "TAINI_1047_B_Grin2B_129_Baseline-2021_03_26-0000.dat", "BL1", 101, 200])
    workbook.save(xlsx)

    window = _load_bl_windows(tmp_path)[(129, "BL1")]

    assert (window["start"], window["end"]) == (100, 199)


def test_unexpected_sleep_code_raises(nwbfile, tmp_path):
    # dge_ok.csv holds the scores before SWD epochs are relabelled, so only 0-2 are valid.
    csv = tmp_path / "GRIN2B_129_BL1-dge_ok.csv"
    csv.write_text("sleep.score\n0\n4\n")

    with pytest.raises(ValueError, match="unexpected sleep.score codes"):
        SleepStateInterface(file_paths={"baseline_window_1": csv}).add_to_nwbfile(nwbfile, metadata={})


def test_sleep_scoring_channels_are_written_to_epochs():
    nwbfile = NWBFile(
        session_description="test", identifier="test", session_start_time=datetime(2021, 3, 26, tzinfo=timezone.utc)
    )
    bounds = {
        "start_sample": 0,
        "stop_sample": 999,
        "sleep_scoring_eeg_channel": "M2_anterior_R",
        "sleep_scoring_emg_channel": "EMG_R",
    }

    BaselineEpochsInterface(baseline_windows=[{"baseline_window_1": bounds}], sampling_frequency=FS).add_to_nwbfile(
        nwbfile, metadata={}
    )

    epochs = nwbfile.epochs.to_dataframe()
    assert list(epochs["sleep_scoring_eeg_channel"]) == ["M2_anterior_R"]
    assert list(epochs["sleep_scoring_emg_channel"]) == ["EMG_R"]


def test_swd_codes_become_boolean_flags(nwbfile, tmp_path):
    csv = tmp_path / "GRIN2B_129_BL1_DGE_SWDs.csv"
    csv.write_text("DGE_SWDs\n4\n6\n4\n")

    SwdEpochsInterface(file_paths={"baseline_window_1": csv}).add_to_nwbfile(nwbfile, metadata={})

    df = nwbfile.processing["behavior"]["swd_epochs"].to_dataframe()
    assert list(df["is_swd"]) == [False, True, False]
    assert list(df["start_time"]) == [0.0, 5.0, 10.0]


def test_unexpected_swd_code_raises(nwbfile, tmp_path):
    csv = tmp_path / "GRIN2B_129_BL1_DGE_SWDs.csv"
    csv.write_text("DGE_SWDs\n4\n1\n")

    with pytest.raises(ValueError, match="unexpected DGE_SWDs codes"):
        SwdEpochsInterface(file_paths={"baseline_window_1": csv}).add_to_nwbfile(nwbfile, metadata={})


def test_seizure_totals_keep_hourly_counts_only(nwbfile, tmp_path):
    # Row 0 holds the window totals (N_event, mean_dur, Day); rows 1-23 are zero padding.
    hourly = [3, 0, 2] + [0] * 21
    rows = ["N_event,mean_dur,ZT,SWDs,Day"]
    rows += [f"{5 if h == 0 else 0},{1.5 if h == 0 else 0},{h},{hourly[h]},{5 if h == 0 else 0}" for h in range(24)]
    csv = tmp_path / "GRIN2B_129_BL1_Seiz_Totals.csv"
    csv.write_text("\n".join(rows) + "\n")

    SeizureTotalsInterface(file_paths={"baseline_window_1": csv}).add_to_nwbfile(nwbfile, metadata={})

    df = nwbfile.processing["behavior"]["seizure_counts_by_zt_hour"].to_dataframe()
    assert list(df.columns) == ["zeitgeber_hour", "number_of_seizure_events", "baseline_window"]
    assert list(df["number_of_seizure_events"]) == hourly
