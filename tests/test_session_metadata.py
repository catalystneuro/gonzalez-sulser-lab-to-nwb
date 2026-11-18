"""Per-subject metadata from the lab's subject sheet, and the session start time."""

from datetime import datetime, timezone

import pytest

from gonzalez_sulser_lab_to_nwb.hristova_2025.convert_session import (
    get_session_start_time,
    get_subject_metadata,
)

FS = 250.4


@pytest.fixture
def subjects_file_path(tmp_path):
    # Same columns as Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv, which also lists CDKL5 animals.
    path = tmp_path / "GRIN2B_CDKL5_Seizures_Overall.csv"
    path.write_text(
        "ID,Group,Genotype,Sex,Line,N_events,Mean_duration,Total_duration\n"
        "129,Het Male,Het,Male,Grin2b,784.5,4.7,3695.2\n"
        "140,Wt Female,Wt,Female,Grin2b,0.5,0.8,0.8\n"
        "2024,Het Male,Het,Male,Cdkl5,0,0,0\n"
    )
    return path


def test_het_subject_gets_the_line_genotype(subjects_file_path):
    assert get_subject_metadata(subjects_file_path, 129) == dict(
        subject_id="GRIN2B-129", sex="M", genotype="LE-Grin2bem1Mcwi"
    )


def test_wild_type_subject(subjects_file_path):
    assert get_subject_metadata(subjects_file_path, 140) == dict(subject_id="GRIN2B-140", sex="F", genotype="WT")


def test_subject_of_another_line_is_not_used(subjects_file_path):
    with pytest.raises(ValueError, match="0 rows for Grin2b animal 2024"):
        get_subject_metadata(subjects_file_path, 2024)


def test_session_start_time_is_bl1_lights_on_minus_bl1_offset():
    # BL1 starts at 07:00 Edinburgh time the day after the date in the file name.
    start = get_session_start_time("TAINI_1047_B_Grin2B_129_Baseline-2021_03_26-0000.dat", bl1_start_sample=int(3600 * FS))
    assert start.isoformat() == "2021-03-27T06:00:00+00:00"


def test_session_start_time_counts_elapsed_time_across_a_clock_change():
    # The UK clocks went forward at 01:00 UTC on 2021-03-28, so BL1 at 07:00 BST is 06:00 UTC, and 10 h of
    # recording before it started at 20:00 UTC (GMT) on 2021-03-27.
    start = get_session_start_time("TAINI_1047_B_X_1-2021_03_27-0000.dat", bl1_start_sample=int(10 * 3600 * FS))
    assert start.astimezone(timezone.utc) == datetime(2021, 3, 27, 20, tzinfo=timezone.utc)
