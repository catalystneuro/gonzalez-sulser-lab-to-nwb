# Troubleshooting

A failed subject's traceback is in `conversion_errors/GRIN2B_<id>.txt` in the output folder (see
[Converting sessions](converting_sessions.md)). This page lists the errors of the conversion and the staging, with
what to do.

## Conversion errors

| Error | Meaning | What to do |
|---|---|---|
| "Raw recordings not in the data folder" | `convert` found an animal of the xlsx whose `.dat` file is not in `Chronic EEG recordings/`; nothing was converted | ask the lab for the file, check the `File` column of the xlsx, or convert the others with `--animal-ids` |
| "`GRIN2B_<id>` was excluded from the study" | the animal is in `EXCLUDED_ANIMAL_IDS` | nothing; excluded animals are not published |
| "... has no BL1 window for `GRIN2B_<id>`" | the xlsx has no BL1 row for the animal; the session start time is computed from BL1 | ask the lab for the window |
| "Raw .dat file not found" | the xlsx `File` of the animal is not in `Chronic EEG recordings/` | check the file name; for a wrong name in the xlsx, add the right one to `DAT_FILE_CORRECTIONS` |
| "... has 0 rows for Grin2b animal `<id>`" | the subject sheet has no row for the animal (or more than one) | add or correct the row in `GRIN2B_CDKL5_Seizures_Overall.csv` |
| `KeyError` on a sex or genotype value | the subject sheet has a value other than `Male`/`Female` or `Het`/`Wt` | correct the sheet, or add the value to `SEX` or `GENOTYPE` in `convert_session.py` |
| "unexpected sleep.score codes" or "unexpected DGE_SWDs codes" | a lab file has codes other than 0 to 2 (sleep) or 4 and 6 (SWD), for example a relabelled `-dge_swd.csv` copied under the `-dge_ok.csv` name | ask the lab which file is right |
| `KeyError: 'DGE_SWDs'` (or another column) | a lab file has another layout, as 424's re-analysed `DGE_SWDs.csv` | ask the lab for the file in the usual layout, or add the animal to `SKIPPED_STREAMS` |
| "Baseline windows ... are not in the epochs table" | a processed file was given for a window without an epochs-table row | check the xlsx rows of the animal |

A warning "no rows in ...; seizure_events is not written" is expected for an animal without seizures in any window
(GRIN2B_238, GRIN2B_375).

## NWB files

- A subject is not converted again: `convert` skips subjects whose NWB file exists. Add `--overwrite`.
- `herd_references` is 0 in the conversion summary: the ontology terms were not written. NeuroConv writes them from
  the `ExternalResources` block of `general_metadata.yaml`; check that the installed NeuroConv is the version pinned
  in `pyproject.toml` (releases up to 0.10.2 do not write them), and that every location and experimenter has an
  entry with exactly the same spelling (see [Metadata](metadata.md#ontology-terms)).
- NWB Inspector messages: the report of each file is in `inspector_reports/`. `CRITICAL`, `ERROR` and
  `PYNWB_VALIDATION` messages must be fixed before uploading. The known `BEST_PRACTICE_SUGGESTION` messages follow
  from the data and need no change:
  - `check_column_binary_capability` on `sleep_states.sleep_score`: the check reads part of the column, which may
    have no REM epoch (always in stub files).
  - `check_column_binary_capability` on `seizure_counts_by_zt_hour.number_of_seizure_events`: animals with at most one
    seizure per hour (for example 140, 402, 404).
  - `check_single_row` on `seizure_events`: animals with one seizure (140 and 404).

## Staging

- `stage` fails to download `dandiset.yaml`: check the dandiset ID and the instance; a sandbox dandiset has its own
  ID.
- `upload` stops with validation errors: nothing was uploaded. Fix the files or the dandiset metadata on the website,
  then run `stage` and `upload` again.
- `upload` fails with an authentication error: set `DANDI_API_KEY` (archive) or `DANDI_SANDBOX_API_KEY` (sandbox).
