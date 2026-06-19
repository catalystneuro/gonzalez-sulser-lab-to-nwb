# SFARI ARC – Gonzalez-Sulser Lab Conversion Progress

## Chronic EEG / Sleep / Seizure Dataset Conversion Progress

**Progress: 0 / TBD**

---

## Pre-Conversion

- [x] Repo Setup (local; remote pending API approval)
- [x] Initial Inspection and Notes: Delineation of *Projects (SFARI lines)*, *Experiments (Baseline 24h windows)* and *Data Streams* — see [`conversion_notes.md`](conversion_notes.md)
- [x] Phase 2 byte-level inspection of `.dat` and CSV streams ([`inspect_data.py`](inspect_data.py), [`inspection_report.json`](inspection_report.json))
- [x] Phase 3: all metadata YAMLs drafted ([`grin2b_general_metadata.yaml`](src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_general_metadata.yaml), [`grin2b_subjects_metadata.yaml`](src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_subjects_metadata.yaml))
- [x] Phase 4: synchronization analysis — single-clock, BL-offset arithmetic confirmed
- [x] Phase 5: all 5 conversion interfaces written and stub tested (GRIN2B_129 BL1 — all streams pass)
- [x] Phase 6: NWBInspector run on stub — 2 pending-lab warnings, no structural errors
- [x] Confirm TainiTec `.dat` binary layout: int16 LE, 16ch interleaved, fs = 250.4 Hz, no header
- [x] Confirm BL1/BL2 sample-window semantics from `Sample_start_end_GRIN2B.xlsx`
- [x] Confirm seizure-CSV time origin (seconds from BL window start)
- [x] Confirm `Channels.csv` is a derived feature (not raw) → will not be republished
- [x] Identify and draft all missing data / metadata requests — see `metadata_request_email.md`
- [x] **Channel order confirmed** from `grin2b_eeg_channels.csv` (2026-06-19): EMG at indices 1 (R) and 14 (L); EEG at all other indices
- [x] **Sex and genotype populated** for 29/37 animals from `GRIN2B_CDKL5_Seizures_Overall.csv` (2026-06-19)
- [x] `SeizureInterface` updated to use `ndx_events.AnnotatedEventsTable` (ndx-events ≥ 0.2.2)
- [ ] **Pending lab reply** — ADC→volts gain, sleep code legend, NeuroNexus model, sex/genotype/strain for animals 132/383/401/402/404/424/430/433, time-of-day & timezone, GRIN2B DOI, location of missing raw `.dat` files (~16 animals)
- [ ] Acquire **all** raw `.dat` files (only 21 of ~37 GRIN2B animals' raw recordings are in the share)
- [ ] Obtain lab reader / scoring code (URL)
- [ ] Re-run NWBInspector stub test after ndx-events + BaseRecordingExtractorInterface refactor

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

- [x] NWB Inspector validation (stub) — 2 pending-lab warnings only (ADC gain → conversion; subject age/DOB)
- [ ] Setup Dandiset (public — line is published)
- [ ] Example Notebooks (streaming + Spyglass query demo)

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
