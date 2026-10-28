"""Conversions must follow the conventions of the lab's own analysis code.

Scaling follows TainiTec's parse_dat.m; the DGE_SWDs and Seiz_Totals layouts follow
cepstral_analysis.m (both in Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER).
"""

from datetime import datetime, timezone

import numpy as np
import pytest
from pynwb import NWBFile

from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.baseline_epochs_interface import BaselineEpochsInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.seizure_interface import SeizureTotalsInterface, SwdEpochsInterface
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
    # GRIN2B_129_BL1_Channels.csv stores raw code 2594 as 8.23492063492063 mV (13 mV / 4095 per code).
    dat = tmp_path / "TAINI_1047_B_Grin2B_129_Baseline-2021_03_26-0000.dat"
    np.full((3, 16), 2594, dtype="<i2").tofile(dat)

    recording = TainiRecordingInterface(file_path=dat, signal_type="EEG").recording_extractor
    traces_uv = recording.get_traces(return_in_uV=True)

    assert traces_uv[0, 0] == pytest.approx(8234.92063492063, abs=0.01)


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
