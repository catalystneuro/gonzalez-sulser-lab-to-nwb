"""Convert every GRIN2B subject of Hristova et al. 2025 that has a raw recording, and inspect the new files.

Subjects come from Sample_start_end_GRIN2B.xlsx, without the excluded animals. A subject whose NWB file exists is
skipped unless overwrite is set. Each new file is inspected (see inspection.py). The traceback of a failed subject is
written to <output_dir>/conversion_errors/GRIN2B_<id>.txt.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .convert_session import (
    EXCLUDED_ANIMAL_IDS,
    RECORDING_FOLDER,
    get_subject_key,
    load_baseline_windows,
    session_to_nwb,
)
from .inspection import REPORT_FOLDER, inspect_nwbfile, update_summary


def get_animal_ids(data_dir: str | Path) -> list[int]:
    """The animals to convert: every animal of the xlsx that is not excluded. Raises if a raw recording is missing."""
    windows = load_baseline_windows(data_dir)
    animal_ids = sorted(set(windows) - EXCLUDED_ANIMAL_IDS)
    missing = [
        f"{get_subject_key(animal_id)}: {windows[animal_id]['BL1']['file']}"
        for animal_id in animal_ids
        if not (Path(data_dir) / RECORDING_FOLDER / windows[animal_id]["BL1"]["file"]).exists()
    ]
    if missing:
        raise FileNotFoundError("Raw recordings not in the data folder:\n" + "\n".join(missing))
    return animal_ids


def convert_and_inspect(data_dir: Path, output_dir: Path, animal_id: int, stub_test: bool) -> dict:
    """Convert one subject and inspect its file; on failure, write the traceback and return the error."""
    try:
        nwbfile_path = session_to_nwb(data_dir=data_dir, output_dir=output_dir, animal_id=animal_id, stub_test=stub_test)
        return inspect_nwbfile(nwbfile_path, report_dir=nwbfile_path.parents[1] / REPORT_FOLDER)
    except Exception as error:
        error_dir = output_dir / "conversion_errors"
        error_dir.mkdir(parents=True, exist_ok=True)
        (error_dir / f"{get_subject_key(animal_id)}.txt").write_text(traceback.format_exc())
        return dict(animal_id=animal_id, error=repr(error))


def dataset_to_nwb(
    data_dir: str | Path,
    output_dir: str | Path,
    animal_ids: list[int] | None = None,
    max_workers: int = 1,
    stub_test: bool = False,
    overwrite: bool = False,
) -> list[int]:
    """Convert and inspect the GRIN2B subjects; return the animal IDs that failed.

    Parameters
    ----------
    data_dir : str or Path
        The lab's data share.
    output_dir : str or Path
        Folder of the NWB files (one sub-GRIN2B-<id>/ folder per subject).
    animal_ids : list of int, optional
        The animals to convert; default all (get_animal_ids).
    max_workers : int
        Subjects converted in parallel. A full subject takes 15-20 min and writes 1-1.6 GB.
    stub_test : bool
        Write stub files to <output_dir>/nwb_stub/.
    overwrite : bool
        Convert again the subjects whose NWB file exists.
    """
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    nwb_dir = output_dir / "nwb_stub" if stub_test else output_dir
    animal_ids = animal_ids or get_animal_ids(data_dir)
    if not overwrite:
        existing = {animal_id for animal_id in animal_ids if any(nwb_dir.glob(f"sub-GRIN2B-{animal_id}/*.nwb"))}
        if existing:
            print(f"Skipping {len(existing)} subjects with an NWB file (use overwrite to convert them again).")
        animal_ids = [animal_id for animal_id in animal_ids if animal_id not in existing]

    rows, failed = [], []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(convert_and_inspect, data_dir, output_dir, animal_id, stub_test) for animal_id in animal_ids
        ]
        for future in as_completed(futures):
            result = future.result()
            if "error" in result:
                failed.append(result["animal_id"])
                print(f"FAILED {get_subject_key(result['animal_id'])}: {result['error']}")
            else:
                rows.append(result)
                print(f"Converted {result['nwbfile']}")
    if rows:
        update_summary(nwb_dir, rows)
    return sorted(failed)
