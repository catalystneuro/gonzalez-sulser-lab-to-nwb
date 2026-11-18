"""Inspect converted NWB files with NWB Inspector and keep a summary of the output folder.

Each NWB file gets a report, <output_dir>/inspector_reports/<file stem>.txt. The summary,
<output_dir>/conversion_summary.csv, has one row per NWB file with the number of inspector messages per importance
level and the number of HERD references (ontology terms from metadata/general_metadata.yaml; 0 means they were not
written).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPORT_FOLDER = "inspector_reports"
SUMMARY_FILE = "conversion_summary.csv"
IMPORTANCE_LEVELS = ["ERROR", "PYNWB_VALIDATION", "CRITICAL", "BEST_PRACTICE_VIOLATION", "BEST_PRACTICE_SUGGESTION"]


def get_nwbfile_paths(output_dir: str | Path) -> list[Path]:
    """The NWB files of an output folder, <output_dir>/sub-*/*.nwb (stub files in nwb_stub/ are left out)."""
    return sorted(Path(output_dir).glob("sub-*/*.nwb"))


def inspect_nwbfile(nwbfile_path: str | Path, report_dir: str | Path) -> dict:
    """Run NWB Inspector with the DANDI configuration, save the report to report_dir, and summarize the file.

    Returns the file name, the number of messages per importance level and the number of HERD references.
    """
    from nwbinspector import format_messages, inspect_nwbfile as run_inspector, load_config, save_report
    from pynwb import NWBHDF5IO

    nwbfile_path, report_dir = Path(nwbfile_path), Path(report_dir)
    messages = list(run_inspector(nwbfile_path=nwbfile_path, config=load_config("dandi")))
    report_dir.mkdir(parents=True, exist_ok=True)
    save_report(
        report_file_path=report_dir / f"{nwbfile_path.stem}.txt",
        formatted_messages=format_messages(messages, levels=["importance", "check_function_name"]),
        overwrite=True,
    )
    with NWBHDF5IO(nwbfile_path, "r") as io:
        external_resources = io.read().external_resources
        herd_references = 0 if external_resources is None else len(external_resources.to_dataframe())
    return dict(
        nwbfile=nwbfile_path.name,
        **{level: sum(message.importance.name == level for message in messages) for level in IMPORTANCE_LEVELS},
        herd_references=herd_references,
    )


def update_summary(output_dir: str | Path, rows: list[dict]) -> pd.DataFrame:
    """Write rows to the conversion summary of an output folder, replacing earlier rows of the same files."""
    summary_path = Path(output_dir) / SUMMARY_FILE
    summary = pd.DataFrame(rows)
    if summary_path.exists():
        earlier = pd.read_csv(summary_path)
        summary = pd.concat([earlier[~earlier["nwbfile"].isin(summary["nwbfile"])], summary])
    summary = summary.sort_values("nwbfile").reset_index(drop=True)
    summary.to_csv(summary_path, index=False)
    return summary


def inspect_output_folder(output_dir: str | Path) -> pd.DataFrame:
    """Inspect every NWB file of an output folder and update its conversion summary."""
    report_dir = Path(output_dir) / REPORT_FOLDER
    return update_summary(output_dir, [inspect_nwbfile(path, report_dir) for path in get_nwbfile_paths(output_dir)])
