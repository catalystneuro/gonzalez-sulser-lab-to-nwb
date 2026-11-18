"""Command line of the Hristova 2025 conversion: convert, inspect, stage and upload.

Run "hristova-2025 <command> --help" for the arguments of each command. A typical run:

    hristova-2025 convert <data folder> <output folder>
    hristova-2025 stage <output folder> --dandi-instance dandi-sandbox
    hristova-2025 upload <output folder> --dandi-instance dandi-sandbox

convert converts the subjects that have no NWB file yet, inspects each new file and updates conversion_summary.csv.
inspect inspects every NWB file again. stage downloads the draft's dandiset.yaml, validates the folder and writes
draft_asset_report.csv; upload validates again and uploads the NWB files to the draft.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def convert(args: argparse.Namespace) -> int:
    """Convert and inspect the subjects without an NWB file (all with --overwrite); return 1 if one failed."""
    from .convert_all_sessions import dataset_to_nwb

    failed = dataset_to_nwb(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        animal_ids=args.animal_ids,
        max_workers=args.max_workers,
        stub_test=args.stub_test,
        overwrite=args.overwrite,
    )
    print(f"{len(failed)} subjects failed{': ' + str(failed) + ' (see conversion_errors/)' if failed else ''}")
    return int(bool(failed))


def inspect(args: argparse.Namespace) -> int:
    """Inspect every NWB file of the output folder again and update the conversion summary."""
    from .inspection import inspect_output_folder

    print(inspect_output_folder(args.output_dir).to_string(index=False))
    return 0


def stage(args: argparse.Namespace) -> int:
    """Download dandiset.yaml, validate the files and compare them with the draft; return 1 on validation errors."""
    from .upload_to_DANDI import stage_output_folder

    errors, report = stage_output_folder(args.output_dir, args.dandiset_id, args.dandi_instance)
    print("Draft assets by status (draft_asset_report.csv):")
    print(report["status"].value_counts().to_string())
    print(f"{len(errors)} validation errors", *errors, sep="\n")
    return int(bool(errors))


def upload(args: argparse.Namespace) -> int:
    """Validate the staged output folder and upload its NWB files to the draft."""
    from .upload_to_DANDI import upload_output_folder

    upload_output_folder(args.output_dir, args.dandi_instance)
    return 0


def get_parser() -> argparse.ArgumentParser:
    from .upload_to_DANDI import DANDI_INSTANCES, DANDISET_ID

    parser = argparse.ArgumentParser(prog="hristova-2025", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(required=True)

    subparser = subparsers.add_parser("convert", help=convert.__doc__)
    subparser.add_argument("data_dir", type=Path, help="the lab's data share")
    subparser.add_argument("output_dir", type=Path, help="folder of the NWB files")
    subparser.add_argument("--animal-ids", type=int, nargs="+", help="convert only these animals, e.g. 129 130")
    subparser.add_argument("--max-workers", type=int, default=1, help="subjects converted in parallel (default 1)")
    subparser.add_argument("--stub-test", action="store_true", help="write small stub files to <output>/nwb_stub/")
    subparser.add_argument("--overwrite", action="store_true", help="convert again the subjects with an NWB file")
    subparser.set_defaults(function=convert)

    subparser = subparsers.add_parser("inspect", help=inspect.__doc__)
    subparser.add_argument("output_dir", type=Path, help="folder of the NWB files")
    subparser.set_defaults(function=inspect)

    for command, function in (("stage", stage), ("upload", upload)):
        subparser = subparsers.add_parser(command, help=function.__doc__)
        subparser.add_argument("output_dir", type=Path, help="folder of the NWB files")
        subparser.add_argument(
            "--dandi-instance", required=True, choices=DANDI_INSTANCES, help="the DANDI archive or the sandbox"
        )
        if command == "stage":
            subparser.add_argument("--dandiset-id", default=DANDISET_ID, help=f"default {DANDISET_ID}")
        subparser.set_defaults(function=function)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
