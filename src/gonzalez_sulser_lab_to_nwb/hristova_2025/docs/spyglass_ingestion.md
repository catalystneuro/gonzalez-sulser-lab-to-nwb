# Spyglass ingestion

[Spyglass](https://github.com/LorenFrankLab/spyglass) is a DataJoint pipeline that stores what an NWB file holds in a
MySQL database, so sessions can be queried and analyzed together. The converted files can be ingested into a local
Spyglass database: session and subject metadata, the EEG and EMG recordings, the sleep scoring and seizures, and the
HERD and HED annotations.

Upstream Spyglass doesn't ingest most of this yet. The missing pieces are open pull requests on LorenFrankLab/spyglass
(section 5). Until they are merged, the environment installs Spyglass from the tag
`gonzalez-sulser-example-v1` of the [CatalystNeuro fork](https://github.com/catalystneuro/spyglass), which combines
upstream `master` with those branches. Tables from open PRs can change in review; section 5 explains how to update.

Everything is in [src/gonzalez_sulser_lab_to_nwb/hristova_2025/spyglass/](../spyglass/):

- `docker-compose.yml`: the local MySQL database;
- `spyglass-env.yaml` and `bootstrap_wsl.sh`: the conda environment;
- `dj_local_conf.example.json`: template of the connection and storage settings;
- `check_connection.py`: checks the connection;
- `insert_full_session.py`: ingests files and reports what was ingested;
- `notebooks/`: three notebooks that read the database (section 4);
- `spyglass_ingestion_notes.md`: the state of the PRs this depends on, known gaps and open ideas.

## 1. Set up

Spyglass can't be imported on native Windows, so on Windows it runs in WSL2 (Ubuntu 24.04), with the database in
Docker Desktop. You need:

- WSL2 with Ubuntu 24.04, and [Miniforge](https://github.com/conda-forge/miniforge) installed in it at
  `/opt/miniforge3` (the path `bootstrap_wsl.sh` expects);
- Docker Desktop, with WSL integration turned on.

### Database

From `spyglass/`:

```bash
docker compose up -d
```

This starts the `spyglass-db` container (MySQL 8.0) on port 3306, with its data in a Docker volume. The container
restarts with Docker Desktop.

### Environment

From a Windows terminal:

```bash
wsl -d Ubuntu-24.04 -- bash /mnt/c/<path to repo>/src/gonzalez_sulser_lab_to_nwb/hristova_2025/spyglass/bootstrap_wsl.sh
```

This creates the `spyglass-gonzalez-sulser-lab-env` conda env from `spyglass-env.yaml`, or updates it if it exists,
and then installs package versions that pip can't resolve together with Spyglass's own pins: pynwb 4.2 and hdmf 6.2
(the files use NWB 2.11), and ndx-hed 0.3 with numpy 2. The header of `spyglass-env.yaml` explains each one. Pip
prints warnings about these conflicts; they are expected.

To run the notebooks, register the env as a Jupyter kernel once:

```bash
conda activate spyglass-gonzalez-sulser-lab-env
python -m ipykernel install --user --name spyglass-gonzalez-sulser-lab-env
```

### Configuration

Copy `dj_local_conf.example.json` to `dj_local_conf.json` in `spyglass/` (the copy is not tracked by git), and replace
`/path/to/spyglass_data_gonzalez` with a folder inside WSL. Spyglass keeps the NWB files it ingests in `raw/` and its
own output files in `analysis/`. A folder on the Linux side (not under `/mnt/c`, and not on an exFAT drive) is much
faster. The database settings match `docker-compose.yml`.

The scripts and notebooks load this file before importing Spyglass, because Spyglass connects to the database when it
is imported. Check the setup with:

```bash
conda activate spyglass-gonzalez-sulser-lab-env
cd /mnt/c/<path to repo>/src/gonzalez_sulser_lab_to_nwb/hristova_2025/spyglass
python check_connection.py
```

It prints the connection and the Spyglass schemas on the server.

## 2. Ingest the files

Copy the NWB files of DANDI:001888 into the `raw` folder of `dj_local_conf.json`, without the subject folders, then
pass their names to `insert_full_session.py`, from `spyglass/` in the activated env:

```bash
python insert_full_session.py sub-GRIN2B-129_ses-2021-03-26_ecephys.nwb
```

To ingest every file in the folder:

```bash
python insert_full_session.py $(cd /path/to/spyglass_data_gonzalez/raw && ls sub-*.nwb | grep -v '_\.nwb')
```

For each file, the script runs Spyglass's `insert_sessions()`, prints the number of rows per table, and lists the
errors Spyglass logged in its `InsertError` table. A file ingested correctly has no `InsertError` rows. Spyglass
writes a copy of each file next to it, with `_` added to the name (`sub-GRIN2B-129_ses-2021-03-26_ecephys_.nwb`), that
links to the original's data; the database refers to that copy. If a file is already in the database, the script
deletes its entry first, so a file can be ingested again after a change. All 24 files take about 2 minutes.

To start from an empty database, for example after the tables changed (section 5), run `docker compose down -v` and
`docker compose up -d` from `spyglass/`, and delete the `*_.nwb` copies in `raw/`. This deletes the database volume
and everything in it; the original NWB files are not touched.

## 3. What is ingested

Rows per session:

| Data in the NWB file | Spyglass tables | Rows |
| --- | --- | --- |
| Session metadata, experimenters | `Session`, `Session.Experimenter` | 1, 13 |
| Baseline windows (epochs table) and series valid times | `IntervalList` | 4 |
| EEG and EMG electrode groups and electrodes | `ElectrodeGroup`, `Electrode` | 2, 16 |
| `EEGElectricalSeries` and `EMGElectricalSeries` | `ImportedEEG` (`.Electrode`) | 2 (16) |
| Sleep scoring (`sleep_states`) | `SleepStateScoring` (`.Epoch`) | 1 (34,560) |
| Seizures (`seizure_events`) | `SeizureEvents` (`.Event`) | 1 (1 to 2,121), none for GRIN2B-238 and GRIN2B-375 |
| HERD ontology references | `ExternalResources` (`.Reference`) | 1 (27) |
| HED schema versions and the sleep states' HED column | `HedMetadata`, `HedAnnotation` (`.Row`) | 1, 1 (3) |

Tables shared across sessions hold the 24 subjects, 13 lab members, the institution and lab, 2 brain regions
(`cerebral cortex` and `trapezius muscle`) and 24 ontology terms (`OntologyTerm`). `DataAcquisitionDevice` and
`TaskEpoch` stay empty, because the files have no data of those kinds.

The database stores metadata, the scored epochs and the seizure times, and the object ids of the NWB data. The EEG and
EMG samples stay in the NWB files; `ImportedEEG.nwb_object()` reads them from the copy in `raw/`.

Not ingested, because Spyglass has no table for them: the cortical area and channel name of each EEG screw (Spyglass's
`Electrode` takes the region from the electrode group), and the other analysis results in the files
(`swd_epochs`, `seizure_counts_by_zt_hour`, `sleep_state_power_spectra`). They stay in the NWB files.

## 4. Notebooks

The notebooks in [spyglass/notebooks/](../spyglass/notebooks/) read the database, so ingest the files first. Open
them with the `spyglass-gonzalez-sulser-lab-env` kernel, from Jupyter started in WSL or from VS Code connected to
WSL. Each loads `../dj_local_conf.json` in its first cell.

- [spyglass_eeg_emg_tutorial.ipynb](../spyglass/notebooks/spyglass_eeg_emg_tutorial.ipynb): the electrodes and EEG
  screw positions of a session, the series and baseline windows of every session, 10 seconds of EEG and EMG, and a
  comparison of the samples read through Spyglass with the source files.
- [spyglass_hed_herd_tutorial.ipynb](../spyglass/notebooks/spyglass_hed_herd_tutorial.ipynb): the ontology terms
  linked to the subjects, electrode locations, experimenters and sleep states, a query of sleep epochs by ontology
  term, and the HED tags of the sleep states, validated against the HED schemas.
- [spyglass_sleep_seizures_tutorial.ipynb](../spyglass/notebooks/spyglass_sleep_seizures_tutorial.ipynb): time in
  each state per rat, a hypnogram with seizures, seizure rates per rat and per sleep state, and the EEG around a
  seizure.

Before working with the data, each notebook checks that every session in the database has the expected rows.

## 5. Upstream status and updates

The tables used here come from these branches:

| Data | Pull request |
| --- | --- |
| EEG/EMG series | [#1638](https://github.com/LorenFrankLab/spyglass/pull/1638) |
| HERD external resources | [#1722](https://github.com/LorenFrankLab/spyglass/pull/1722) |
| HED annotations | [#1723](https://github.com/LorenFrankLab/spyglass/pull/1723) |
| Sleep scoring and seizures | [#1726](https://github.com/LorenFrankLab/spyglass/pull/1726) |

Upstream Spyglass also needs pynwb 4 to read these files
([#1694](https://github.com/LorenFrankLab/spyglass/issues/1694)); the bootstrap installs it over Spyglass's pins. The
current state of each PR is in [spyglass_ingestion_notes.md](../spyglass/spyglass_ingestion_notes.md) and in
[issue #13](https://github.com/catalystneuro/gonzalez-sulser-lab-to-nwb/issues/13).

The sleep tables are the most likely to change: the conventions that select a sleep scoring table (a `sleep_state`
column) and a seizure table (the name `seizure_events`) are still to be discussed with the Spyglass team. When a PR
changes, a new tag of the fork is made and the environment files point to it. To update:

1. Pull this repository.
2. Run `bootstrap_wsl.sh` again.
3. Reset the database and ingest the files again (section 2).
4. Re-run the notebooks.

Once all the PRs are merged, the environment will install a Spyglass release, and the tag and the notes file will be
removed.
