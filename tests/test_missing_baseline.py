"""Per-baseline streams must align by baseline label when one baseline's CSV is missing.

GRIN2B_140/378 have no BL1 power-spectrum CSV and GRIN2B_375 has no BL1 seizures
CSV; the BL2 file must still land on the BL2 epoch.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from neuroconv.utils import load_dict_from_file
from pynwb import NWBHDF5IO, NWBFile

from gonzalez_sulser_lab_to_nwb.hristova_2025.interfaces.baseline_epochs_interface import BaselineEpochsInterface
from gonzalez_sulser_lab_to_nwb.hristova_2025.interfaces.seizure_interface import SeizureInterface
from gonzalez_sulser_lab_to_nwb.hristova_2025.interfaces.sleep_state_interface import SleepStateInterface
from gonzalez_sulser_lab_to_nwb.hristova_2025.interfaces.state_power_spectrum_interface import StatePowerSpectrumInterface

FS = 250.4
GENERAL_METADATA = Path(__file__).parents[1] / "src" / "gonzalez_sulser_lab_to_nwb" / "hristova_2025" / "metadata" / "general_metadata.yaml"
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
        baseline_windows={"baseline_window_1": BL1, "baseline_window_2": BL2}, sampling_frequency=FS
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


def test_no_seizures_in_any_window_writes_no_table(nwbfile, tmp_path):
    # GRIN2B_238 has header-only Seizures.csv files in both windows.
    csv = tmp_path / "GRIN2B_238_BL1_Seizures.csv"
    csv.write_text("sec_start\tsec_end\tdur\n")

    with pytest.warns(UserWarning, match="seizure_events is not written"):
        SeizureInterface(file_paths={"baseline_window_1": csv}).add_to_nwbfile(nwbfile, metadata={})

    assert "behavior" not in nwbfile.processing


def test_tables_of_both_windows_are_written_and_read_back(nwbfile, tmp_path):
    sleep_csvs = {}
    for label in ("baseline_window_1", "baseline_window_2"):
        sleep_csvs[label] = tmp_path / f"{label}-dge_ok.csv"
        sleep_csvs[label].write_text("sleep.score\n0\n1\n2\n")
    SleepStateInterface(file_paths=sleep_csvs).add_to_nwbfile(nwbfile, metadata=load_dict_from_file(GENERAL_METADATA))
    nwbfile_path = tmp_path / "test.nwb"
    with NWBHDF5IO(nwbfile_path, "w") as io:
        io.write(nwbfile)

    with NWBHDF5IO(nwbfile_path, "r") as io:
        read_nwbfile = io.read()
        sleep_states = read_nwbfile.processing["behavior"]["sleep_states"]
        df = sleep_states.to_dataframe()
        meanings = sleep_states.meanings_tables["sleep_state_meanings"].to_dataframe()
        references = read_nwbfile.external_resources.to_dataframe()

    assert dict(zip(meanings["value"], meanings["HED"])) == {
        "Wake": "Awake",
        "NREM": "Asleep",
        "REM": "Asleep, sc:Sleep-stage-REM",
    }
    assert dict(zip(references["key"], references["entity_id"])) == {
        "Wake": "NBO:0000066",
        "NREM": "NBO:0000161",
        "REM": "NBO:0000159",
    }

    assert list(df["sleep_state"]) == ["Wake", "NREM", "REM"] * 2
    assert list(df["baseline_window"]) == ["baseline_window_1"] * 3 + ["baseline_window_2"] * 3
    assert df["start_time"].iloc[3] == pytest.approx(BL2["start_sample"] / FS)
