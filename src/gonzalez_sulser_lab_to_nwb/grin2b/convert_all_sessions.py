"""Convert all GRIN2B baseline sessions to NWB.

Discovers all (animal_id, baseline) pairs from Sample_start_end_GRIN2B.xlsx
whose raw .dat file is present on disk, then runs the conversion in parallel.

Usage
-----
    python -m gonzalez_sulser_lab_to_nwb.grin2b.convert_all_sessions \\
        --data-dir "H:/Gonzalez-Sulser-CN-data-share" \\
        --output-dir "/path/to/nwb_output" \\
        [--max-workers 4] \\
        [--stub-test]
"""
from __future__ import annotations

import argparse
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Literal

from .convert_session import _load_bl_windows, session_to_nwb

_EEG_DIR = "Chronic EEG recordings"


def _get_all_sessions(data_dir: Path) -> list[dict]:
    """Return kwargs for every session whose .dat file is on disk."""
    windows = _load_bl_windows(data_dir)
    eeg_dir = data_dir / _EEG_DIR
    on_disk = {f.name for f in eeg_dir.glob("*.dat")}

    sessions = []
    skipped = []
    for (animal_id, baseline), win in windows.items():
        if win["file"] not in on_disk:
            skipped.append((animal_id, baseline, win["file"]))
            continue
        sessions.append(dict(animal_id=animal_id, baseline=baseline))

    if skipped:
        print(
            f"Skipping {len(skipped)} sessions — raw .dat not in share:\n"
            + "\n".join(f"  GRIN2B_{a} {bl}: {f}" for a, bl, f in skipped)
        )
    print(f"Found {len(sessions)} convertible sessions.")
    return sessions


def _safe_convert(data_dir, output_dir, animal_id, baseline, stub_test, exception_dir):
    try:
        session_to_nwb(
            data_dir=data_dir,
            output_dir=output_dir,
            animal_id=animal_id,
            baseline=baseline,
            stub_test=stub_test,
        )
    except Exception:
        exc_path = Path(exception_dir) / f"GRIN2B_{animal_id}_{baseline}.txt"
        exc_path.write_text(traceback.format_exc())
        print(f"ERROR GRIN2B_{animal_id} {baseline} — see {exc_path}")


def dataset_to_nwb(
    data_dir: str | Path,
    output_dir: str | Path,
    max_workers: int = 1,
    stub_test: bool = False,
) -> None:
    """Convert all available GRIN2B sessions to NWB.

    Parameters
    ----------
    data_dir : str or Path
        Root of the Gonzalez-Sulser data share.
    output_dir : str or Path
        Directory where NWB files will be written.
    max_workers : int
        Number of parallel worker processes.
    stub_test : bool
        If True, convert small stubs only (for pipeline validation).
    """
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    exception_dir = output_dir / "exceptions"
    exception_dir.mkdir(parents=True, exist_ok=True)

    sessions = _get_all_sessions(data_dir)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for s in sessions:
            executor.submit(
                _safe_convert,
                data_dir=str(data_dir),
                output_dir=str(output_dir),
                animal_id=s["animal_id"],
                baseline=s["baseline"],
                stub_test=stub_test,
                exception_dir=str(exception_dir),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert all GRIN2B sessions to NWB.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--stub-test", action="store_true")
    args = parser.parse_args()

    dataset_to_nwb(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        stub_test=args.stub_test,
    )
