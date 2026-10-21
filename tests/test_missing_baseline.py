"""Per-baseline streams must align by baseline label when one baseline's CSV is missing.

GRIN2B_140/378 have no BL1 power-spectrum CSV and GRIN2B_375 has no BL1 seizures
CSV; the BL2 file must still land on the BL2 epoch.
"""

from datetime import datetime, timezone

import pytest
from pynwb import NWBFile

from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.baseline_epochs_interface import BaselineEpochsInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.seizure_interface import SeizureInterface
from gonzalez_sulser_lab_to_nwb.grin2b.interfaces.state_power_spectrum_interface import StatePowerSpectrumInterface

FS = 250.4
BL1 = {"start_sample": 1000, "stop_sample": 1999}
BL2 = {"start_sample": 2000, "stop_sample": 2999}


@pytest.fixture
def nwbfile():
    nwbfile = NWBFile(
        session_description="test",
        identifier="test",
        session_start_time=datetime(2022, 5, 7, tzinfo=timezone.utc),
    )
    BaselineEpochsInterface(
        baseline_windows=[{"baseline_window_1": BL1}, {"baseline_window_2": BL2}], sampling_frequency=FS
    ).add_to_nwbfile(nwbfile, metadata={})
    return nwbfile


def test_seizures_with_only_bl2_file(nwbfile, tmp_path):
    csv = tmp_path / "GRIN2B_375_BL2_Seizures.csv"
    csv.write_text("sec_start\tsec_end\tdur\n10.0\t12.0\t2.0\n")

    SeizureInterface(file_paths={"baseline_window_2": csv}).add_to_nwbfile(nwbfile, metadata={})

    df = nwbfile.processing["behavior"]["seizure_events"].to_dataframe()
    assert list(df["baseline_window"]) == ["baseline_window_2"]
    assert df["start_time"].iloc[0] == pytest.approx(BL2["start_sample"] / FS + 10.0)


def test_power_spectrum_with_only_bl2_file(nwbfile, tmp_path):
    csv = tmp_path / "GRIN2B_140_BL2-pw_spectrum.csv"
    csv.write_text("hz,s_0,s_1,s_2,s_4\nBL2,BL2,BL2,BL2,BL2\n0.0,1.0,2.0,3.0,4.0\n0.2,1.1,2.1,3.1,4.1\n")

    StatePowerSpectrumInterface(file_paths={"baseline_window_2": csv}).add_to_nwbfile(nwbfile, metadata={})

    df = nwbfile.processing["ecephys"]["sleep_state_power_spectra"].to_dataframe()
    assert set(df["baseline_window"]) == {"baseline_window_2"}
    assert list(df["Wake"]) == [1.0, 1.1]
