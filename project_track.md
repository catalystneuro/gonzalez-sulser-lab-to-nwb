# SFARI ARC – Gonzalez-Sulser Lab Conversion Progress

## Chronic EEG / Sleep / Seizure Dataset Conversion Progress

**Progress: 0 / TBD**

---

## Pre-Conversion

- Repo Setup (PR TBD)
- Initial Inspection and Notes: Delineation of *Projects (SFARI lines)*, *Experiments (Baseline 24h windows)* and *Data Streams* — see [`conversion_notes.md`](conversion_notes.md)
- Identify and request missing data / metadata / READMEs — see [`metadata_request_email.md`](metadata_request_email.md)
- Acquire **all** raw `.dat` files (only 21 of ~37 animals' raw recordings are currently in the share)
- Confirm TainiTec `.dat` binary spec (dtype, sample rate, channel order, gain)
- Obtain subject metadata table for all GRIN2B animals
- Obtain reader / scoring code from the lab

---

## Project 1: GRIN2B (lead — published line)

- Convert all sessions (PR TBD)

### Behavior

#### Conversion with Spyglass compatibility

- Sleep-state classifications (5-s epochs, `*-dge_ok.csv`) → `TimeIntervals` / `BehavioralEpochs` (PR TBD)
- Light-cycle metadata (lights-on Zeitgeber, `Sample_start_end_GRIN2B.xlsx`) → `LabMetaData` / `epochs` (PR TBD)

#### Ingest in Spyglass

- Sleep-state classifications
- Light-cycle epochs

### External Stimuli

*None — naturalistic chronic recording (no programmed stimulus).*

### Ephys

#### Conversion with Spyglass compatibility

- Chronic EEG, 14 channels, TainiTec `.dat` (custom recording interface) (PR TBD)
- Chronic EMG, 2 channels, TainiTec `.dat` (custom recording interface) (PR TBD)
- NeuroNexus EEG grid `ElectrodeGroup` + `Device` metadata (PR TBD)

#### Ingest in Spyglass

- EEG (raw)
- EMG (raw)

### Events

#### Conversion with Spyglass compatibility

- Seizure timestamps (`Seizure timestamps/*_BL{1,2}_Seizures.csv`) → `TimeIntervals` (PR TBD)
- Spike-Wave Discharges (`*/seiz/*_DGE_SWDs.csv`) → `TimeIntervals` (PR TBD)
- Per-ZT seizure totals (`*/seiz/*_Seiz_Totals.csv`) → `processing/behavior` table (PR TBD)
- Per-state power spectra (`*-pw_spectrum.csv`) → `DecompositionSeries` or skip (PR TBD)

#### Ingest in Spyglass

- Seizure intervals
- SWD intervals

### Temporal Alignment

#### Conversion with Spyglass compatibility

- BL1 / BL2 sample-window offsets from `Sample_start_end_GRIN2B.xlsx` applied to align sleep, seizure, and SWD timestamps to raw `.dat` time origin (PR TBD)
- `session_start_time` populated with Edinburgh local timezone (Europe/London) (PR TBD)

#### Ingest in Spyglass

- Aligned event timestamps

### Post-Conversion

- Setup Dandiset (public — line is published)
- NWB Inspector validation
- README / Documentation
- Example Notebooks (streaming + Spyglass query demo)

---

## Project 2: SFARI line #2 (TBD)

*Name to be confirmed by lab. Pipeline generalised from Project 1.*

- Convert all sessions
- Spyglass ingestion

### Behavior
- Sleep-state classifications
- Light-cycle metadata

### Ephys
- Chronic EEG (TainiTec `.dat`)
- Chronic EMG (TainiTec `.dat`)

### Events
- Seizure timestamps
- SWDs / per-ZT totals

### Temporal Alignment
- BL window offsets

### Post-Conversion
- Setup Dandiset (embargoed until publication)
- Inspection / Validation
- README / Documentation
- Example Notebooks

---

## Project 3: SFARI line #3 (TBD)

*Same scaffold as Project 2.*

- Convert all sessions
- Behavior · Ephys · Events · Temporal Alignment · Spyglass ingestion · Post-Conversion

---

## Project 4: SFARI line #4 (TBD)

*Same scaffold as Project 2.*

- Convert all sessions
- Behavior · Ephys · Events · Temporal Alignment · Spyglass ingestion · Post-Conversion

---

## Project 5: SFARI line #5 (TBD)

*Same scaffold as Project 2.*

- Convert all sessions
- Behavior · Ephys · Events · Temporal Alignment · Spyglass ingestion · Post-Conversion

---

## Cross-Project Deliverables (Aim 4 — Demonstrate NWB usage)

- Tutorial notebook: read converted NWB locally
- Tutorial notebook: stream NWB directly from DANDI
- Tutorial notebook: query data via Spyglass
- Lab-facing README and onboarding doc
