# DANDI staging

The converted files are shared in [DANDI:001888](https://dandiarchive.org/dandiset/001888). Uploads go to the draft
of the dandiset; a published version is a fixed snapshot of the draft. Upload by hand, after reviewing the NWB files
and the conversion summary.

Each step takes `--dandi-instance`: `dandi` for the archive, `dandi-sandbox` for the
[sandbox](https://sandbox.dandiarchive.org), a separate test server where a copy of the dandiset can be tried first.
`stage` takes the dandiset ID with `--dandiset-id` (default `001888`), for example for a sandbox dandiset.

The conversion already names and places the files as DANDI expects
(`sub-GRIN2B-<id>/sub-GRIN2B-<id>_ses-<date>_ecephys.nwb`), so the output folder is the dandiset folder. Only the
NWB files under `sub-*/` are uploaded; the stub files, reports and summaries stay local.

## 1. Review the converted files

Before staging, check in the output folder:

- `conversion_summary.csv`: a row for each of the 24 subjects, no `CRITICAL`, `ERROR` or `PYNWB_VALIDATION`
  messages, and `herd_references` above 0.
- `inspector_reports/`: the NWB Inspector report of each file.
- A few files opened with PyNWB or Neurosift (see [NWB file structure](nwb_file_structure.md)).

## 2. Stage

```bash
hristova-2025 stage "<output folder>" --dandi-instance dandi
```

This:

- downloads the draft's `dandiset.yaml` into the output folder, replacing an earlier copy;
- validates the NWB files and `dandiset.yaml` as `dandi upload` would (NWB schema, DANDI's requirements, and the
  critical NWB Inspector checks), and prints the errors;
- writes `draft_asset_report.csv` to the output folder, with the status of each file:
  - `replaced`: on the draft at the same path; the upload replaces it.
  - `new`: not on the draft yet.
  - `only on draft`: on the draft but not in the output folder. The upload leaves it there; remove it on the dandiset
    page or with `dandi delete` if it should go.

It returns a non-zero exit code if validation finds errors.

## 3. Upload

Set your DANDI API key (from your account page on the archive or the sandbox) in the environment:
`DANDI_API_KEY` for the archive, `DANDI_SANDBOX_API_KEY` for the sandbox. Then:

```bash
hristova-2025 upload "<output folder>" --dandi-instance dandi
```

This validates the folder again and uploads the NWB files to the draft. Nothing is uploaded if validation finds an
error. A file already on the draft is replaced when the local file is newer (dandi's `existing="refresh"`). The
full upload is about 30 GB.

## Dandiset metadata

The name, description, contributors and other metadata of the dandiset are edited on the DANDI website. `stage`
validates the copy it downloads, so an error in it shows up before uploading.
