"""Validate the converted NWB files and upload them to the draft of DANDI:001888.

The conversion writes the files as DANDI expects them (sub-<subject>/sub-<subject>_ses-<date>_ecephys.nwb), so the
output folder is the dandiset folder: stage_output_folder downloads the draft's dandiset.yaml into it, validates the
NWB files and dandiset.yaml, and compares the folder with the draft; upload_output_folder uploads the NWB files.
Only <output_dir>/sub-*/*.nwb is uploaded, never nwb_stub/, the inspector reports or the summary.

dandi_instance is "dandi" for the archive or "dandi-sandbox" for the sandbox. Uploading needs a DANDI API key of
that instance in the environment: DANDI_API_KEY for the archive, DANDI_SANDBOX_API_KEY for the sandbox.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

from .inspection import get_nwbfile_paths

DANDISET_ID = "001888"
DANDI_INSTANCES = ("dandi", "dandi-sandbox")


def check_dandi_instance(dandi_instance: str) -> None:
    if dandi_instance not in DANDI_INSTANCES:
        raise ValueError(f"Unknown DANDI instance {dandi_instance!r}; use one of {DANDI_INSTANCES}.")


def download_dandiset_metadata(output_dir: str | Path, dandiset_id: str, dandi_instance: str) -> Path:
    """Download the draft's dandiset.yaml into output_dir, replacing an earlier copy."""
    from dandi.consts import known_instances
    from dandi.download import download

    check_dandi_instance(dandi_instance)
    with tempfile.TemporaryDirectory() as download_dir:
        download(
            urls=f"{known_instances[dandi_instance].gui}/dandiset/{dandiset_id}/draft",
            output_dir=download_dir,
            get_metadata=True,
            get_assets=False,
        )
        return Path(shutil.copy(Path(download_dir) / dandiset_id / "dandiset.yaml", Path(output_dir) / "dandiset.yaml"))


def validate_output_folder(output_dir: str | Path) -> list[str]:
    """Validate the NWB files and dandiset.yaml as dandi upload does; return one "<file>: <message>" per error.

    NWB files are checked against the NWB schema and DANDI's requirements, including the critical NWB Inspector
    checks; dandiset.yaml against the DANDI metadata schema of the installed client.
    """
    from dandi.files import DandisetMetadataFile, find_dandi_files
    from dandi.validate import Severity
    from dandischema.models import get_schema_version

    output_dir = Path(output_dir)
    paths = [output_dir / "dandiset.yaml", *get_nwbfile_paths(output_dir)]
    errors = []
    for dandi_file in find_dandi_files(*paths, dandiset_path=output_dir, include_metadata=True):
        # The draft's dandiset.yaml may state an older schema version, which dandi refuses to validate.
        schema_version = get_schema_version() if isinstance(dandi_file, DandisetMetadataFile) else None
        for result in dandi_file.get_validation_errors(schema_version=schema_version):
            if result.severity is not None and result.severity.value >= Severity.ERROR.value:
                errors.append(f"{dandi_file.filepath}: {result.message}")
    return errors


def report_draft_assets(output_dir: str | Path, dandiset_id: str, dandi_instance: str) -> pd.DataFrame:
    """Compare the NWB files with the draft assets: "replaced", "new", or "only on draft" (left as is by the upload)."""
    from dandi.dandiapi import DandiAPIClient

    check_dandi_instance(dandi_instance)
    with DandiAPIClient.for_dandi_instance(dandi_instance) as client:
        draft_paths = {asset.path for asset in client.get_dandiset(dandiset_id, "draft").get_assets()}
    local_paths = {path.relative_to(output_dir).as_posix() for path in get_nwbfile_paths(output_dir)}
    rows = []
    for path in sorted(draft_paths | local_paths):
        if path not in local_paths:
            status = "only on draft"
        else:
            status = "replaced" if path in draft_paths else "new"
        rows.append(dict(path=path, status=status))
    return pd.DataFrame(rows, columns=["path", "status"])


def stage_output_folder(output_dir: str | Path, dandiset_id: str, dandi_instance: str) -> tuple[list[str], pd.DataFrame]:
    """Download dandiset.yaml, validate, and compare with the draft; write draft_asset_report.csv to output_dir."""
    download_dandiset_metadata(output_dir, dandiset_id, dandi_instance)
    report = report_draft_assets(output_dir, dandiset_id, dandi_instance)
    report.to_csv(Path(output_dir) / "draft_asset_report.csv", index=False)
    return validate_output_folder(output_dir), report


def upload_output_folder(output_dir: str | Path, dandi_instance: str) -> None:
    """Upload the NWB files of a staged output folder to the draft; nothing is uploaded if validation fails."""
    from dandi.upload import upload

    check_dandi_instance(dandi_instance)
    if not (Path(output_dir) / "dandiset.yaml").exists():
        raise FileNotFoundError(f"No dandiset.yaml in {output_dir}; stage the folder first.")
    errors = validate_output_folder(output_dir)
    if errors:
        raise ValueError(f"{len(errors)} validation errors, nothing uploaded:\n" + "\n".join(errors))
    upload(paths=[str(path) for path in get_nwbfile_paths(output_dir)], dandi_instance=dandi_instance)
