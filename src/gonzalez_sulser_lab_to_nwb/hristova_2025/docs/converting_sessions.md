# Converting sessions

A session is the full recording of one animal and becomes one NWB file,
`sub-GRIN2B-<id>/sub-GRIN2B-<id>_ses-<recording date>_ecephys.nwb`. Sessions are converted with the `hristova-2025`
command, installed with the package (see the [README](../../../../README.md#installation)). Run it from the conda
environment of the package:

```bash
conda activate gonzalez-sulser-lab-to-nwb-env
hristova-2025 --help
```

Run `hristova-2025 <command> --help` for all options.

## 1. Convert

```bash
hristova-2025 convert "<data folder>" "<output folder>"
```

The data folder is the lab's data share (see [Data organization](data_organization.md)). The command converts every
animal of `Sample_start_end_GRIN2B.xlsx` except the excluded ones, and stops before converting if a raw recording is
missing. Subjects whose NWB file is already in the output folder are skipped, so the same command converts only new
animals. Add `--overwrite` to convert every subject again, for example after a change to the metadata.

Options:

- `--animal-ids 129 130`: convert only these animals.
- `--max-workers 4`: convert several subjects in parallel. A subject takes 15 to 20 minutes and writes a 1 to 1.6 GB
  file, so the full dataset takes about 7 hours with one worker. Each worker reads a 2 to 3 GB recording.
- `--stub-test`: write small files (100 samples of raw data, the first 100 rows of each table) to
  `<output folder>/nwb_stub/`, to check a change in a few seconds.

A subject that fails does not stop the others. For each subject the command:

- writes the NWB file,
- runs NWB Inspector on it and saves the report to `inspector_reports/<file name>.txt`,
- adds a row to `conversion_summary.csv`: the number of inspector messages per importance level and the number of
  ontology (HERD) references in the file.

The traceback of a failed subject is written to `conversion_errors/GRIN2B_<id>.txt`, and the command returns a
non-zero exit code. See [Troubleshooting](troubleshooting.md).

## 2. Inspect again

```bash
hristova-2025 inspect "<output folder>"
```

Runs NWB Inspector again on every NWB file of the output folder and updates the conversion summary, for example after
updating NWB Inspector.

## Output folder

```text
<output folder>/
  sub-GRIN2B-<id>/sub-GRIN2B-<id>_ses-<date>_ecephys.nwb   one file per subject
  inspector_reports/<file name>.txt                       NWB Inspector report of each file
  conversion_summary.csv                                  inspector message counts and HERD references per file
  conversion_errors/GRIN2B_<id>.txt                       traceback of each failed subject
  nwb_stub/                                               stub files, with their own reports and summary
  dandiset.yaml, draft_asset_report.csv                   written by the staging step (see DANDI staging)
```

The NWB files are already named and placed as DANDI expects, so the output folder is also the folder that is
uploaded (see [DANDI staging](dandi_staging.md)).

## Converting one session from Python

```python
from gonzalez_sulser_lab_to_nwb.hristova_2025.convert_session import session_to_nwb

nwbfile_path = session_to_nwb(
    data_dir="<data folder>",
    output_dir="<output folder>",
    animal_id=129,
    stub_test=True,
)
```

`session_to_nwb` overwrites an existing file. `subjects_file_path` sets another subject sheet than the default
`Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv` of the data folder. `dataset_to_nwb` in
`convert_all_sessions.py` is the function behind `hristova-2025 convert`.

## Adding animals

To convert a new GRIN2B animal recorded and analyzed the same way:

1. Put its files in the data share with the usual names (see [Data organization](data_organization.md)): the `.dat`
   file in `Chronic EEG recordings/`, the processed files in `Sleep state classifications/GRIN2B_<id>/` and
   `Seizure timestamps/`.
2. Add its BL1 and BL2 rows to `Sample_start_end_GRIN2B.xlsx` and its row to
   `GRIN2B_CDKL5_Seizures_Overall.csv`.
3. Add its sleep-scoring channels to `metadata/sleep_scoring_channels.yaml` (see [Metadata](metadata.md#sleep-scoring-channels)).
4. Convert it with `--stub-test`, check the stub file, then convert it in full. `convert` without `--overwrite`
   converts only the animals that have no file yet.

A missing processed file leaves that window out of that stream only. A file in another layout raises an error; see
[Troubleshooting](troubleshooting.md).

## Tests

```bash
pip install --editable ".[test]"
pytest tests
```

The tests use small generated files, not the data share, and run in a few seconds.
