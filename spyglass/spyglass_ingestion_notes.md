# Spyglass Ingestion Notes — Gonzalez-Sulser Lab GRIN2B

## Project Overview

Ingestion of the already-converted, DANDI-published GRIN2B chronic EEG/EMG NWB files
(`DANDI:001888`, produced by `src/gonzalez_sulser_lab_to_nwb/`, see `../conversion_notes.md`)
into a Spyglass (DataJoint) database, for the SFARI ARC deliverable. Target schema:
**`common_eeg`/`ImportedEEG`**, a chronic-EEG ingestion path added to Spyglass specifically for
this dataset.

- **Lab POC:** Natalie Hung / Niamh McLaughlin
- **PI:** Prof. Alfredo Gonzalez-Sulser
- **CN team:** Ben Dichter, Alessandra Trapani
- **Upstream Spyglass work:** [LorenFrankLab/spyglass#1634](https://github.com/LorenFrankLab/spyglass/issues/1634)
  (issue, cites this project by name) → [LorenFrankLab/spyglass#1638](https://github.com/LorenFrankLab/spyglass/pull/1638)
  (draft PR, branch `feature/eeg-ingestion`). `common_eeg.py`'s own docstring uses
  `DANDI:001888` — this project's dandiset — as its example, so the PR was almost certainly
  written against these exact files.
- **Approach:** post-hoc — read the already-converted NWB files as-is and ingest them; do
  **not** re-run or fork the DANDI conversion pipeline to "bake in" Spyglass requirements. See
  "Design decision" below.
- **Status (2026-09-11): all 17 currently-converted subjects inserted and verified, 0 failures,
  no NWB file changes needed.**

## Design decision: post-hoc ingestion, not a from-scratch Spyglass conversion

The `/spyglass-convert` skill's default stance is to build Spyglass-compatible NWB files from
scratch instead of reusing a DANDI-oriented conversion. That does not apply here: this repo
already has a finished, published conversion, and redoing it would waste that work and would
not generalize to other labs already through a standard conversion. Instead, the plan is a
**post-hoc interface**: inspect an already-converted NWB file, diff it against what Spyglass
actually requires, and only transform/prompt for what's genuinely missing. In practice (see
"Empirical gap analysis" below) the gap turned out to be ~zero, so no transform step exists yet
— but the intended shape of that tool (`spyglass_interface/`, not built) is documented in the
project plan file for when a real gap shows up.

## Environment

Full runbook: see git history of this file / the project plan. Summary of what's running:

| Layer | Where | Details |
|---|---|---|
| MySQL DB | Docker Desktop container `spyglass-db` | `datajoint/mysql:8.0`, port 3306, data in the named volume `spyglass_spyglass-mysql-data` (not a bind mount — `F:` is exFAT and can't back InnoDB) |
| Spyglass Python | WSL2 **Ubuntu-24.04**, Miniforge at `/opt/miniforge3` | Native Windows can't run Spyglass at all (`spyglass-neuro` calls `multiprocessing.set_start_method("fork")` at import time, which doesn't exist on Windows) |
| Data | External SSD `F:\CN_data` (exFAT) | Published NWBs at `F:\CN_data\001888\sub-GRIN2B-<id>\*.nwb`; Spyglass data root at `F:\CN_data\gonzalez-sulser\spyglass_data\` (raw/analysis/recording/...), seen from WSL as `/mnt/f/CN_data/...` |

Two WSL conda envs, both defined in this folder:

- **`spyglass`** (`spyglass-env.yaml`) — PyPI `spyglass-neuro 0.6.0`. Verified working
  (`check_connection.py`), but does **not** have `common_eeg`/`ImportedEEG` — it's the release,
  PR #1638 hasn't merged. Kept as a known-good fallback.
- **`spyglass-eeg`** (`spyglass-eeg-env.yaml`) — spyglass installed straight from the PR branch:
  `git+https://github.com/LorenFrankLab/spyglass.git@feature/eeg-ingestion`
  (resolves to `spyglass-neuro 0.5.5a2.dev87+gaac13e01a`). **This is the env actually used for
  GRIN2B ingestion.** Needed two extra installs beyond the yaml to work:
  `pip install kachery-cloud` (a `ModuleNotFoundError` inside `insert_sessions()` otherwise),
  then `pip install "pubnub<6.4"` to re-pin after `kachery-cloud` pulled `pubnub>=7.2` and broke
  `spyglass-neuro`'s own `pubnub<6.4` constraint. This conflict is unresolved upstream — pinning
  `pubnub<6.4` works for everything exercised so far.

Bring the DB up: `docker compose -f docker-compose.yml up -d` (PowerShell, from this folder).
Activate the env: `wsl -d Ubuntu-24.04`, then `conda activate spyglass-eeg`.
Config: `dj_local_conf.json` (git-ignored, has DB credentials) — shared by both envs, same DB.

## Empirical gap analysis (2026-09-11)

Rather than trust the `/spyglass-convert` skill's `knowledge/spyglass-nwb-requirements.md`
(which turned out to describe an older/different Spyglass code path — see below), the actual
requirement was read directly from the installed source and then confirmed by literally running
insertion against a real, unmodified file (`dry_run_insertion.py`, subject `GRIN2B-129`).

**What was read from source, before running anything:**

- `common_eeg.ImportedEEG.get_nwb_objects()` selects `acquisition` `ElectricalSeries` objects
  whose electrodes' `ElectrodeGroup.group_name` contains `"eeg"` or `"emg"` (case-insensitive
  substring) — our existing `EEGArray`/`EMGArray` group names already match, no rename needed.
- `common_ephys.ElectrodeGroup.probe_id` and `Electrode.probe_shank`/`probe_electrode`/
  `Probe.Electrode` are all **nullable FKs with defaults** (`ref_elect_id`→`-1`,
  `bad_channel`→`False`, probe fields→`None`) — missing NWB electrode columns do **not** crash
  ingestion. Brain region comes from `ElectrodeGroup.location`, not a per-electrode column
  (already set to `"cortex"`/`"trapezius muscle"` by `TainiRecordingInterface`).
- `common_device.DataAcquisitionDevice` only ingests `ndx_franklab_novela.DataAcqDevice`
  objects; our plain `pynwb.Device` yields 0 rows — confirmed non-fatal.

**What the dry run then confirmed empirically**, against the unmodified, DANDI-published
`sub-GRIN2B-129_ses-2021-03-26_ecephys.nwb`: `sgi.insert_sessions()` and
`ImportedEEG.populate()` both completed with **no exception**, populated `Session`(1),
`ElectrodeGroup`(2), `Electrode`(16), `ImportedEEG`(2), `ImportedEEG.Electrode`(16); read-back
via `fetch_nwb()` matched the source file's shapes/rate/unit exactly. **`DataAcquisitionDevice`
= 0 rows** (expected/cosmetic) and **`TaskEpoch`/`Task` did not populate** (no `"tasks"`
processing module in the file — the BL1/BL2 windows are still present as raw NWB `epochs` and in
`IntervalList`, just not wired into Spyglass's Task pipeline).

**Net result: zero NWB changes needed** for `common_eeg`/`ImportedEEG` ingestion of this
dataset. The one environment-level snag (`kachery_cloud` import failure inside
`insert_sessions()`) was a missing/undeclared dependency, unrelated to the NWB files.

## Ingestion run (2026-09-11)

All 17 currently-converted subjects, copied unmodified from `F:\CN_data\001888\` into
`F:\CN_data\gonzalez-sulser\spyglass_data\raw\` (~19.8 GB), inserted via `insert_session.py`:

- **17/17 subjects inserted, 0 failures.**
- Every subject: `ElectrodeGroup=2, Electrode=16, ImportedEEG=2, ImportedEEG.Electrode=16,
  DataAcquisitionDevice=0` (see `insertion_report.txt` for the raw per-subject dump).
- `verify_insertion.py`: **34/34 series pass** data-integrity check (first 1000 samples of every
  `EEGElectricalSeries`/`EMGElectricalSeries`, compared between the Spyglass `fetch_nwb()`
  read-back and a direct read of the source NWB file). Table printouts for all 17 subjects in
  `tables.txt`.
- Subjects covered: 129, 130, 131, 132, 137, 138, 139, 227, 228, 229, 236, 237, 238, 239, 240,
  241, 373 (the same 17 with a raw `.dat` on the share per `../conversion_notes.md` §"Conversion
  Run Log" — GRIN2B_424 excluded there too, for the xlsx/file-naming mismatch documented in that
  file's "GRIN2B_424 xlsx error" section).

## File Inventory (`spyglass/`)

```text
docker-compose.yml         MySQL 8.0 service (named volume, port 3306) — committed
dj_local_conf.json         DataJoint config + credentials — git-ignored
spyglass-env.yaml          conda env: PyPI spyglass-neuro 0.6.0 (fallback, no common_eeg)
spyglass-eeg-env.yaml      conda env: spyglass from feature/eeg-ingestion (used for ingestion)
bootstrap_wsl.sh           one-time Miniforge + env setup inside WSL2 Ubuntu-24.04
check_connection.py        DataJoint/Spyglass connection smoke test
dry_run_insertion.py       empirical gap-analysis script (single subject, verbose)
insert_session.py          batch insertion — all subjects in the Spyglass raw dir
verify_insertion.py        batch verification — table printouts + data-integrity read-back
insertion_report.txt       output of the last insert_session.py run
tables.txt                 output of the last verify_insertion.py run
spyglass_ingestion_notes.md  this file
```

Not yet created: `spyglass_interface/` (the general post-hoc gap-analysis tool described in the
project plan — not needed yet since the observed gap was zero; revisit if a future dataset/lab
needs real transformation), `notebooks/spyglass_tutorial.ipynb` (Phase 10).

## Known gaps / accepted as-is for now

- **`DataAcquisitionDevice`: 0 rows.** Would need `ndx_franklab_novela.DataAcqDevice` instead of
  the plain `Device("TainiTecWirelessEEG")` written by `TainiRecordingInterface`. Cosmetic —
  nothing currently ingested depends on it.
- **`TaskEpoch`/`Task`: not populated.** Would need a `"tasks"` processing module + `task_table`
  in the NWB file (not currently written). BL1/BL2 are still queryable as raw NWB `epochs` /
  `IntervalList` rows; only the Task-pipeline convenience layer is missing.
- **Derived streams have no Spyglass table at all**: sleep states, seizure events, SWD epoch
  counts, per-ZT seizure totals, state power spectra (all in `processing["behavior"]`/
  `processing["ecephys"]` — see `../conversion_notes.md` §"Data Streams"). PR #1638 does not
  cover these. Still stored in the NWB file and reachable via `Nwbfile.get_abs_path()`, just not
  queryable through DataJoint yet.

## Open Questions

- Do the derived streams (sleep/seizure/SWD/PSD) need to be *queryable in Spyglass*, or is
  storing them in the NWB file enough for the ARC deliverable? If queryable: open a Spyglass
  issue (general concept, multiple labs would benefit) vs. a lab-scoped
  `spyglass_extensions/` custom `dj.Imported` table?
- PR #1638 is a **draft** — worth flagging to whoever's driving it that this project is
  ingesting against it live (17/17 clean), and tracking if the schema changes before merge.
- Is closing the `DataAcquisitionDevice`/`TaskEpoch` gaps worth doing, or acceptable as-is?
- The 16 animals with processed sleep/seizure data but no raw `.dat` on the share (see
  `../conversion_notes.md` §"File Inventory & Counts") will need the same ingestion once their
  raw files land and get converted.

## TODOs

- Find a way to insert processing/behavior, epochs in the DB
- Discuss with spyglass team about the HERD ontologies
