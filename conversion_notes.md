# Conversion Notes — Gonzalez-Sulser Lab to NWB

## Project Overview

Conversion of chronic EEG/EMG recordings from the Gonzalez-Sulser lab (University of Edinburgh) to NWB. Part of the SFARI Autism Rat Models Consortium (ARC). The lab has collected chronic EEG across **five SFARI lines** to study circadian rhythms, sleep–wake cycles, and seizure activity. Data is acquired wirelessly using a **TainiTec** system with **NeuroNexus EEG grids (14 EEG + 2 EMG channels)** over multi-day sessions (~3 days each). The lab has automated sleep-state classification and seizure scoring pipelines.

- **Lab POC:** Natalie Hung
- **PI:** Prof. Alfredo Gonzalez-Sulser
- **CN team:** Ben Dichter, Alessandra Trapani
- **Repo:** <https://github.com/catalystneuro/gonzalez-sulser-lab-to-nwb> (to be created)
- **Strategy:** Develop against the published GRIN2B line, validate on the remaining 4 lines.
- **Downstream targets:** DANDI Archive (GRIN2B public; others embargoed) + Spyglass ingestion.

## Data Streams

| Stream | Format | Source | File Pattern | NeuroConv Interface |
|---|---|---|---|---|
| Raw EEG/EMG | TainiTec `.dat` (int16, 16ch interleaved) | TainiTec wireless + NeuroNexus grid | `TAINI_<deviceID>_<slot>_<line>_<animalID>_<condition>-<YYYY_MM_DD>-0000.dat` | **Custom** (no existing TAINI interface; will wrap as `BaseRecordingExtractor` or use `BinaryRecordingExtractor`) |
| Sleep state labels | CSV (5-s epochs) | Lab pipeline | `<line>_<animalID>/<line>_<animalID>_BL{1,2}-dge_ok.csv` | Custom (TimeIntervals or BehavioralEpochs) |
| Sleep scoring inputs | CSV (per-sample EEG+EMG, 24h, 2 cols) | Lab pipeline | `..._BL{1,2}_Channels.csv` | Likely **not converted** — derived from raw `.dat` (assumption — confirm) |
| Sleep power spectrum | CSV (629 rows × 5 cols: hz, s_0…s_4) | Lab pipeline | `..._BL{1,2}-pw_spectrum.csv` | Custom (DecompositionSeries or skip if redundant) |
| Seizure timestamps | CSV (`sec_start`, `sec_end`, `dur`) | Lab manual/auto scoring | `Seizure timestamps/<line>_<animalID>_BL{1,2}_Seizures.csv` | Custom (TimeIntervals) |
| Seizure event details (SWDs / totals) | CSV | Lab pipeline | `<subject_dir>/seiz/*.csv` | Custom (TimeIntervals + processing module) |
| Light cycle metadata | XLSX (light-on times, BL1/BL2 sample windows) | Lab | `Light cycle timing metadata/Sample_start_end_GRIN2B.xlsx` | Custom (drives session start, BL windowing) |
| Subject metadata | (Not provided — see metadata_request_email.md) | Lab | TBD | YAML in repo |

## Directory Structure (provided share `H:/Gonzalez-Sulser-CN-data-share/`)

```text
Chronic EEG recordings/                    # 21 .dat files, ~2.2 GB each
  TAINI_<dev>_<slot>_<line>_<animalID>_<cond>-<date>-0000.dat
Light cycle timing metadata/
  Sample_start_end_GRIN2B.xlsx             # rows = sessions; cols = BL1/BL2 sample windows
Seizure timestamps/                        # 73 CSVs (per animal × BL1/BL2)
  GRIN2B_<animalID>_BL{1,2}_Seizures.csv
Sleep state classifications/               # 37 per-animal folders
  GRIN2B_<animalID>/
    GRIN2B_<animalID>_BL{1,2}-dge_ok.csv         # sleep.score, 17,280 epochs (5-s × 24h)
    GRIN2B_<animalID>_BL{1,2}-pw_spectrum.csv    # 628 rows; cols hz, s_0..s_4
    GRIN2B_<animalID>_BL{1,2}_Channels.csv       # 21.6M rows; 2 cols (EEG + EMG, 250.4 Hz × 24h)
    sbh_<animalID>_BL{1,2}.png                   # sleep hypnogram plot
    spec_<animalID>_BL{1,2}.png                  # spectrogram plot
    seiz/
      GRIN2B_<animalID>_BL{1,2}_DGE_SWDs.csv     # spike-wave discharge events
      GRIN2B_<animalID>_BL{1,2}_Seiz_Totals.csv  # per-ZT seizure tallies
      GRIN2B_<animalID>_BL{1,2}_Seizures.csv     # duplicate of top-level seizure CSV?
```

## File Inventory & Counts

- **Raw `.dat` files:** 21 (covering animals 129, 130, 131, 132, 137, 138, 139, 140, 227–229, 236–241, 373, 378, 424)
- **Animals with sleep scoring:** 37 (129–140, 227–241, 362–369, 371, 373, 375, 378, 382, 383, 401, 402, 404, 430, 433)
- **Animals with seizure CSVs:** 73 / 2 = ~37 animals × {BL1, BL2}
- **MISMATCH:** sleep/seizure cover ~37 animals, but only 21 `.dat` files are present in the share. **Many animals have processed data but no raw recording** — needs clarification (see metadata_request_email.md).

## Sessions / Subjects

- **Animals (GRIN2B line):** ≥37, identified by 3-digit IDs (e.g., GRIN2B_129).
- **Per animal:** typically 2 baselines (BL1, BL2) extracted as 24h windows from a multi-day raw recording.
- **Simultaneous recording:** each TainiTec transmitter (device IDs 1044, 1045, 1047, 1048) records one animal at a time; up to 4 animals recorded in parallel on the same date.
- **Slot letter (A/B/C/D):** appears between TAINI device ID and line — assumed to be the device slot/animal position. Confirm with lab.

## Existing Resources

- **Publication:** GRIN2B paper exists (already published per SoW). **DOI to obtain from Natalie Hung.**
- **Existing public data:** none flagged.
- **Existing analysis code:** lab has automated sleep-detection and seizure-scoring pipelines (Python). **Repo URL to obtain.**
- **TAINI reader code:** the lab presumably has Python code to read `.dat` (since they generate `Channels.csv` per-sample series). **Request reader/spec from Natalie.**
- **Data source:** local mount at `H:/Gonzalez-Sulser-CN-data-share/` (read-only share).

## Phase 2 — Findings From Direct File Inspection

Direct inspection performed by [`inspect_data.py`](inspect_data.py) on 2026-04-28; results in [`inspection_report.json`](inspection_report.json). Many Phase 1 assumptions are now confirmed; remaining items are clearly listed in *Open Questions*.

### Confirmed via inspection

| Fact | Value | Evidence |
|---|---|---|
| `.dat` channel count | **16** interleaved | file_size ÷ (16 × 2) gives integer sample count for all 21 files |
| `.dat` dtype | **int16, little-endian** | sample values fall in `[0, 4095]` (12-bit ADC dressed as int16); occasional `-2`/`-3` outliers near boundary |
| `.dat` sample rate | **250.4 Hz exactly** | Channels.csv has 21,634,560 rows = 250.4 × 86,400 s exactly; no rounding works at 250 or 256 |
| `.dat` no header | confirmed | byte 0 reads as a plausible sample, not a magic header |
| ADC zero-level | ~2,560–2,615 (channel-dependent) | mean values across first 100k samples |
| Per-channel activity (first 2 GRIN2B_131 100k) | std varies 12.8 → 96.9 across channels | ch12 most active (std=96.9, 1502 unique values); ch00/ch01/ch10 very flat → likely reference, ground or unused |
| Session duration in `.dat` | **3.207 days** | 69,378,213 samples ÷ 250.4 / 86,400 |
| BL1 window | samples **18,088,897 → 39,723,456** of `.dat` (= 72,239 s → 158,639 s = 20:04 h → 44:04 h) | `Sample_start_end_GRIN2B.xlsx` (consistent for all 2021_03_26 animals) |
| BL2 window | samples **39,723,457 → 61,358,016** (immediately after BL1) | xlsx |
| BL window length | 21,634,560 samples = **24 h** exactly | BL2_end − BL2_start = 21,634,559 samples |
| `Sample_start_end_GRIN2B.xlsx` cols | `Animal ID, Line, File, Baseline, Start, End` | 75 rows, 1 sheet |
| Sleep epoch length | **5 s** | 17,280 epochs × 5 s = 86,400 s = 24 h |
| Sleep state codes observed (BL1, GRIN2B_129) | `{0: 10539, 1: 6443, 2: 298}` — sums to 17,280 | Distribution matches typical rodent **Wake/NREM/REM** (61% / 37% / 2%) |
| `pw_spectrum.csv` shape | 628 rows × 5 cols `[hz, s_0, s_1, s_2, s_4]` | First "row" is actually `BL1,BL1,BL1,BL1,BL1` (sub-header); data rows then go `hz=0` → `hz=125.2` in 0.2 Hz steps. **125.2 Hz = Nyquist of 250.4** |
| `Channels.csv` provenance | **NOT raw `.dat` data** — derived feature | Values are floats in `[0, 98]`, mean ≈ 8, std ≈ 1.8; zero correlation with any raw channel at the matching sample window. Likely a smoothed envelope/RMS used as input to the sleep scorer. |
| `Channels.csv` length | 21,634,560 rows = 24 h × 250.4 Hz | matches BL window exactly |
| Seizure CSV cols | `sec_start, sec_end, dur` | tab-separated |
| Seizure timestamp origin | **seconds from BL window start** | `max(sec_end)` ranges 85,579–86,391 s for 5 sampled animals — i.e. they live in `[0, 86400]` |
| Per-animal `seiz/` files | `*_DGE_SWDs.csv` (17,280 rows = per 5-s epoch SWD count), `*_Seiz_Totals.csv` (24 rows × `[N_event, mean_dur, ZT, SWDs, Day]` = per-ZT-hour tally), `*_Seizures.csv` (= top-level Seizures.csv, **byte-identical** for GRIN2B_129 BL1) | inspection |

### Filename convention (still inferred — confirm with lab)

`TAINI_<deviceID>_<slot>_<line>_<animalID>_<condition>-<YYYY_MM_DD>-0000.dat`

- `deviceID` ∈ {1044, 1045, 1047, 1048} → TainiTec transmitter ID
- `slot` ∈ {A, B, C, D} → receiver slot / animal position
- `condition` ∈ {Baseline, Baseline_Attempt2, BaselineRedone2, Redo, Redo2, …} → recording label
- `0000` = file index (no multi-file sessions seen)

### Channel-activity profile (first 100k samples, GRIN2B_131)

```text
ch00: std=22  ch01: std=15  ch02: std=37  ch03: std=42
ch04: std=34  ch05: std=22  ch06: std=19  ch07: std=28
ch08: std=20  ch09: std=29  ch10: std=13  ch11: std=39
ch12: std=97  ch13: std=37  ch14: std=18  ch15: std=24
```

`ch12` looks like the cleanest live EEG. `ch01`, `ch10` look like inactive/reference. Without lab confirmation we **cannot map specific indices to {EEG_1..EEG_14, EMG_1, EMG_2}** — see open question 3 below.

## 2026-06-19 Updates

### New data files received

Two new files were added to the share and incorporated:

**`H:/Gonzalez-Sulser-CN-data-share/Chronic EEG recordings/grin2b_eeg_channels.csv`**
Confirmed channel layout (Python 0-based index → electrode label, hemisphere):

| Python idx | Electrode | Hemisphere | Group |
|---|---|---|---|
| 0 | S1_Tr | R | EEGArray |
| 1 | EMG | R | **EMGArray** ← was assumed at idx 14 |
| 2 | M2_Fra | R | EEGArray |
| 3 | M2_anterior | R | EEGArray |
| 4 | M1_anterior | R | EEGArray |
| 5 | V2_ML | R | EEGArray |
| 6 | V1_M | R | EEGArray |
| 7 | S1Hl_S1Fl | R | EEGArray |
| 8 | V1_M | L | EEGArray |
| 9 | V2_ML | L | EEGArray |
| 10 | S1Hl_S1Fl | L | EEGArray |
| 11 | M1_anterior | L | EEGArray |
| 12 | M2_anterior | L | EEGArray |
| 13 | M2_Fra | L | EEGArray |
| 14 | EMG | L | **EMGArray** ← was assumed at idx 15 |
| 15 | S1_Tr | L | EEGArray |

**Key correction:** EMG channels are at indices **1 and 14** (interleaved), not 14–15 as previously assumed.
`TainiRecordingInterface._CHANNEL_MAP` has been updated accordingly.

**`H:/Gonzalez-Sulser-CN-data-share/Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv`**
Provides per-subject seizure summary statistics and, crucially, **sex and genotype** for 29 GRIN2B animals:
`grin2b_subjects_metadata.yaml` updated with `sex` (M/F) and `genotype` (Het/Wt) for:
129, 130, 131, 137, 138, 139, 140, 227, 228, 229, 236, 237, 238, 239, 240, 241,
362, 363, 364, 365, 366, 367, 368, 369, 371, 373, 375, 378, 382.
Animals 132, 383, 401, 402, 404, 424, 430, 433 not in CSV — still TODO.

### Code changes (2026-06-19)

1. **`TainiRecordingInterface`** — now inherits from `BaseRecordingExtractorInterface`
   (wraps `spikeinterface.core.BinaryRecordingExtractor`). Uses `frame_slice` to restrict
   to the BL window (lazy, no full-file load), sets `t_start` annotation so neuroconv
   writes the correct `starting_time` in the `ElectricalSeries`.
   Channel map updated to confirmed layout from `grin2b_eeg_channels.csv`.

2. **`SeizureInterface`** — `add_to_nwbfile` now uses `ndx_events.AnnotatedEventsTable`
   (ndx-events ≥ 0.2.2) instead of `pynwb.epoch.TimeIntervals`.
   `stop_time` and `duration` stored as ragged (VectorIndex) columns on a single
   "seizure" event-type row.

3. **`pyproject.toml`** — added `ndx-events>=0.2.2` to `[grin2b]` optional dependencies.

### Code changes (2026-07-07)

1. **`SeizureInterface`** — reverted to `pynwb.epoch.TimeIntervals` (one row per seizure,
   `start_time`/`stop_time`/`duration` columns), matching the pattern used by
   `SleepStateInterface`. `ndx-events` dependency removed from `pyproject.toml`.

## Remaining Assumptions (still to validate)

1. **Channel order in `.dat`:** ~~assumed~~ **CONFIRMED** from `grin2b_eeg_channels.csv`.
   EMG at indices 1 (Right) and 14 (Left); EEG at all other indices.
2. **NeuroNexus EEG grid model number** and per-channel anatomical targets — required for `ElectrodeGroup.location` and an electrodes-table column.
3. **ADC → volts gain** — the `.dat` values are dimensionless 12-bit; we need the TainiTec full-scale range (e.g. ±0.5 mV → conversion = 0.5e-3 / 2048).
4. **Sleep code legend** — `0=Wake, 1=NREM, 2=REM` **confirmed by paper** (3 states reported). The pw_spectrum file uses `s_0, s_1, s_2, s_4` (skipping `s_3`) — state 4 origin still unknown; not mentioned in paper. Ask lab.
5. **`Channels.csv` exact derivation** — likely RMS envelope of one EEG and one EMG channel; would be useful to know which raw channels were chosen and the smoothing window so we can either reproduce or, ideally, omit.
6. **BL window start time-of-day** — the BL1 start (sample 18,088,897 ≈ 20 h into recording) is consistent across animals on the same date, suggesting a fixed offset (probably to skip a 20 h acclimation window, with BL1 then aligning to ZT0 / lights-on).
7. **Slot letter (A/B/C/D)** → animal position in transmitter grid (cosmetic only).
8. **Species & strain** — **Long-Evans** (confirmed from paper, 2026-06-25).
9. **One file = one animal** — confirmed by xlsx (one row pair per `<File, Animal ID>`).

## Open Questions (also see metadata_request_email.md)

Resolved by Phase 2 inspection:

- [x] TAINI `.dat` dtype = int16 LE, sample rate = 250.4 Hz, no header, 16ch interleaved
- [x] Seizure CSV time reference = seconds from BL window start (verified: max sec_end ≈ 86,400)
- [x] BL1/BL2 sample offsets = `Sample_start_end_GRIN2B.xlsx` (BL1 = 18,088,897 → 39,723,456 in `.dat`)
- [x] Top-level vs `seiz/` `Seizures.csv` are byte-identical → use one
- [x] Sleep epoch length = 5 s; epoch count = 17,280 = 24 h

Still open (asked in `metadata_request_email.md`):

- [x] DOI of the GRIN2B publication and full author list — **doi:10.1111/epi.18606** (Hristova et al. 2025)
- [x] **Channel order** in `.dat` — confirmed from `grin2b_eeg_channels.csv` (2026-06-19)
- [x] EMG placement — **neck muscles** (confirmed from paper)
- [x] Strain — **Long-Evans** (confirmed from paper)
- [x] Sleep states Wake/NREM/REM confirmed from paper (3 states; state 4 still unknown)
- [x] Analysis code repos — confirmed from paper Data Availability statement
- [ ] **ADC → volts gain** (TainiTec full-scale; e.g. ±0.5 mV → `conversion = 0.5e-3 / 2048`)
- [ ] NeuroNexus EEG grid model number and per-channel stereotaxic coordinates
- [ ] **State 4** (`s_4` in `pw_spectrum.csv`) — 3 sleep states in paper; origin of column 4 unclear
- [ ] **Lights-on clock time** at Edinburgh facility (12:12 L:D confirmed; ZT0 time not stated)
- [ ] Subject DOB / age at recording, weight per animal
- [ ] Sex/genotype for animals 132, 383, 401, 402, 404, 424, 430, 433
- [ ] Light-cycle protocol (12:12? lights-on Zeitgeber time, time-of-day) and whether BL1 starts at ZT0
- [ ] Per-session **time-of-day** start (filename only encodes the date) with timezone (Edinburgh, Europe/London)
- [ ] Why ~37 animals' processed data but only 21 raw `.dat` files in the share — where are the other raw recordings?
- [ ] Existing GRIN2B repo / TAINI reader code (URL)
- [ ] `Channels.csv` exact derivation (which raw channels selected, smoothing window)
- [ ] List of all 5 SFARI lines and which is the next priority after GRIN2B

## Interface Mapping (post Phase 2)

| Stream | Interface | source_data | Status |
|--------|-----------|-------------|--------|
| Raw EEG/EMG (`.dat`) | **CUSTOM** `TainiTecRecordingInterface` wrapping `spikeinterface.core.BinaryRecordingExtractor` | `file_path`, `num_channels=16`, `sampling_frequency=250.4`, `dtype="int16"` | Format verified; channel-name/gain mapping pending lab |
| Sleep states (`*-dge_ok.csv`) | **CUSTOM** `SleepStateInterface` → `TimeIntervals` | `csv_path`, `bl_start_sample`, `fs=250.4`, `epoch_s=5` | Schema verified; label legend pending |
| Seizure intervals (`*_Seizures.csv`) | **CUSTOM** `SeizureInterface` → `TimeIntervals` | `csv_path`, `bl_offset_s` | Schema verified |
| SWD per-epoch counts (`*_DGE_SWDs.csv`) | **CUSTOM** `SwdCountsInterface` → `processing/behavior` `TimeSeries` (rate=0.2 Hz, 17,280 samples) | `csv_path`, `bl_start_sample` | Schema verified |
| Per-ZT seizure totals (`*_Seiz_Totals.csv`) | **CUSTOM** `SeizureTotalsInterface` → scratch `DynamicTable` | `csv_path` | Schema verified; may be derivable from `Seizures.csv` (if so, drop) |
| State-power spectra (`*-pw_spectrum.csv`) | **CUSTOM** `StatePowerSpectrumInterface` → `processing/ecephys` `DecompositionSeries` | `csv_path` | Schema verified; meaning of `s_4` pending |
| Light cycle / BL windows (`Sample_start_end_GRIN2B.xlsx`) | **CUSTOM** `LightCycleInterface` → drives `session_start_time` and `epochs` table | `xlsx_path`, `animal_id`, `dat_filename` | Schema verified |
| Subject metadata | YAML (per-animal) → `Subject` | `subjects_metadata.yaml` | Source spreadsheet pending |
| `Channels.csv` (derived envelope) | **NOT CONVERTED** — derived feature, will not be republished | n/a | Decision pending lab confirmation |

## Conversion Plan (high-level)

**Phase 5 deliverables (per the canonical NeuroConv repo template):**

```text
src/gonzalez_sulser_lab_to_nwb/
  grin2b/
    __init__.py
    grin2bnwbconverter.py            # NWBConverter class wiring all interfaces
    grin2b_convert_session.py        # Single-session entry point with stub_test
    grin2b_convert_all_sessions.py   # Batch over Sample_start_end_GRIN2B.xlsx
    interfaces/
      taini_recording_interface.py   # Custom — wraps SpikeInterface BinaryRecordingExtractor
      sleep_state_interface.py       # Custom — TimeIntervals / BehavioralEpochs
      seizure_interface.py           # Custom — TimeIntervals
      light_cycle_interface.py       # Custom — drives session_start_time
    metadata/
      grin2b_general_metadata.yaml
      grin2b_subjects_metadata.yaml
  utils/
    taini_io.py                      # binary read helpers
```

Lines 2–5 (other SFARI lines) get sibling subpackages once GRIN2B is solid.

## Phase 3 — Metadata Collection

Metadata YAMLs created at `src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/`:
- [`grin2b_general_metadata.yaml`](src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_general_metadata.yaml) — NWBFile-level, Device, ElectrodeGroup, LightCycle, SleepScoring
- [`grin2b_subjects_metadata.yaml`](src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_subjects_metadata.yaml) — all 37 animals with stubs for lab-provided fields

### Known / auto-derivable metadata

| Field | Value | Source |
|---|---|---|
| institution | University of Edinburgh | SoW |
| lab | Gonzalez-Sulser Lab | SoW |
| experimenter | Hung, Natalie; Gonzalez-Sulser, Alfredo | SoW |
| species | Rattus norvegicus | SoW ("SFARI Autism Rat Models Consortium") |
| session n_channels | 16 (14 EEG + 2 EMG) | SoW + inspection |
| sampling_frequency | 250.4 Hz | inspection |
| timezone | Europe/London | institution (Edinburgh) |
| session_date | parsed from .dat filename (YYYY_MM_DD) | filename |
| BL start/end samples | per-animal from xlsx | Sample_start_end_GRIN2B.xlsx |
| keywords | EEG, EMG, sleep, seizure, circadian, GRIN2B, SFARI, rat | SoW |

### Still needed from lab (all 37 animals)

- sex, date_of_birth, weight, strain, genotype (WT vs het)
- DOI of GRIN2B publication → `related_publications`
- Session time-of-day → combined with filename date → `session_start_time`
- Channel order (which indices = EEG / EMG) → electrode table
- ADC → volts gain → `conversion` parameter
- NeuroNexus model + anatomical targets → `ElectrodeGroup.description` + electrode `location`
- Sleep state label mapping (0/1/2 → Wake/NREM/REM; meaning of state 4)
- Light-cycle lights-on time

### Data integrity issues found

1. **Animal 424 / xlsx mismatch**: The xlsx maps GRIN2B_424 to `TAINI_1044_C_GRIN2B_366-2022_04_12-0000.dat`
   with BL windows that *overlap* with GRIN2B_366's windows in the same file. This is a data management error.
   The actual file on disk is `TAINI_1044_C_Grin2B_424_Redo-2022_06_04-0000.dat` (present but not in xlsx).
   **Lab must provide correct BL1/BL2 sample offsets for the 424_Redo file.**

2. **16 `.dat` files missing from share**: Referenced in xlsx but not present on `H:/Gonzalez-Sulser-CN-data-share/`:
   Animals 362, 363, 364, 365, 366, 367, 368, 369, 371, 382, 383, 401, 402, 404, 430, 433.
   These are the spring 2022 cohort. Lab needs to provide path or transfer the files.

## Phase 4 — Synchronization Analysis

### Conclusion: single-clock — no cross-system sync required

All data streams in this dataset derive from a **single TainiTec `.dat` file per animal per recording**.
There is no multi-clock problem. Alignment is purely arithmetic:

```text
Reference clock:  TainiTec .dat sample index (at fs = 250.4 Hz)

Sleep CSVs:       t_sleep [s] = epoch_index × 5.0
                  t_dat  [s] = BL_start_sample / 250.4 + t_sleep
                  t_abs       = session_start_time + timedelta(seconds=t_dat)

Seizure CSVs:     t_seiz [s] = sec_start (already from BL window start)
                  t_dat  [s] = BL_start_sample / 250.4 + t_seiz
                  t_abs       = session_start_time + timedelta(seconds=t_dat)

DGE_SWDs.csv:     same epoch grid as sleep CSVs (17,280 × 5 s)

Raw EEG/EMG:      starting_time = BL_start_sample / 250.4
                  (relative to session_start_time, set via set_aligned_starting_time())
```

No `temporally_align_data_interfaces()` override needed beyond applying the BL offset.

### Session start time

`session_start_time` = date from `.dat` filename (YYYY_MM_DD) + time-of-day from lab
(pending from Natalie) + `Europe/London` timezone.

Until time-of-day is confirmed, we default to `T00:00:00+00:00` with a warning logged.
The BL windows (starting ≈20 h into the file) are then indexed from that origin.

### NWB epoch table (BL1 / BL2)

We will populate `nwbfile.add_epoch()` for BL1 and BL2 per session using the
sample-index windows from the xlsx, converted to seconds:

```python
bl1_start_s = bl1_start_sample / 250.4
bl1_stop_s  = bl1_stop_sample  / 250.4
nwbfile.add_epoch(start_time=bl1_start_s, stop_time=bl1_stop_s, tags=["BL1"])
```

## Phase 6 — NWBInspector Validation

Ran `nwbinspector` on the stub NWB file (`GRIN2B_129_BL1.nwb`, stub_test=True). Two messages:

| Severity | Check | Message | Status |
|---|---|---|---|
| BEST_PRACTICE_VIOLATION (LOW) | `check_electrical_series_unscaled_data` | `ElectricalSeries` has `dtype=int16`, `conversion=1.0` — data not in Volts | **Pending lab**: ADC gain unknown; `conversion` will be set once lab confirms the TainiTec full-scale range (item 1 of metadata request) |
| CRITICAL (LOW) | `check_subject_age` | Subject missing `age` and `date_of_birth` | **Pending lab**: per-animal DOB/age not yet provided; see item 5 of metadata request |

No structural or schema errors. The two warnings are unresolvable without lab-provided metadata and are documented as TODOs.

## Spyglass Compatibility (Aim 2)

Spyglass requires:
- `ElectrodeGroup` with `device` filled
- `LFP` data in a `processing/ecephys` module if downsampled
- Consistent `electrode_id` across files
- Subject metadata fields populated

Will revisit after Phase 6 testing.

## 2026-06-25 — Paper Findings (Hristova et al., Epilepsia 2025)

The lab shared the published GRIN2B paper. Key metadata extracted and applied:

**Full citation:**
> Hristova K, Fasol MCM, McLaughlin N, Nawaz MS, Taskiran M, Buller-Peralta I,
> Harris AP, Sutherland A, Bassi A, Ocampo-Garces A, Escudero J, Kind PC,
> Gonzalez-Sulser A. Absence seizures and sleep–wake abnormalities in a rat model
> of GRIN2B neurodevelopmental disorder. *Epilepsia.* 2025;66:4996–5013.
> doi:10.1111/epi.18606

### Confirmed by paper

| Question | Answer | Notes |
|---|---|---|
| **Strain** | **Long-Evans** | "Long-Evans Grin2b heterozygous knockout rats" |
| **RRID** | RGD_14394515 | Model ID: LE-Grin2bem1Mcwi (Medical College of Wisconsin Gene Editing Rat Resource Center) |
| **Genotypes** | Grin2b+/− (Het) and Grin2b+/+ (WT littermates) | SFARI Autism Research Initiative support |
| **Sex** | Both male and female | Sexes compared in paper; no significant sex × genotype interactions |
| **EMG placement** | **Neck muscles** | "electromyography electrodes in the neck muscles" |
| **EEG channels** | **14-channel skull-surface electrode grid** | Confirms 14 EEG + 2 EMG = 16 channels total |
| **All electrodes independent** | Yes | "All electrodes are independent of one another and are not interconnected" (no reference/ground grid) |
| **Recording system** | TaiNi wireless multichannel (Tainitec, UK), 250.4 Hz | Reference: Jiang et al. 2017, Sci Rep 7:8086 |
| **Recording duration** | 72–96 h per session; 24-h windows analyzed | "recorded for 72 to 96 h (for 24-h sleep and seizure analysis)" |
| **Recovery / acclimation** | ≥1 week post-surgery recovery + ≥24 h room habituation | Briefly anesthetized with isoflurane to connect implants before recording |
| **Light cycle** | 12-h light / 12-h dark | "12-h light and dark phases" (exact lights-on time not stated in paper) |
| **Sleep states** | Wake, NREM, REM — 3 states only | State 4 in pw_spectrum.csv not mentioned in paper; still ask lab |
| **Sleep scorer code** | [AUTOMATIC-SLEEP-SCORER](https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER) | Same pipeline as Buller-Peralta et al. 2022 (SYNGAP1 paper) |
| **SWD detector code** | [SWD-Automatic-Identification](https://github.com/Gonzalez-Sulser-Team/SWD-Automatic-Identification) | Also: [zenodo:12700972](https://zenodo.org/records/12700972) |
| **SWD detection criterion** | Harmonic peaks at 5–10 Hz in power spectra | "periodic high-amplitude oscillations between 5 and 10 Hz" |
| **EEG targets (from Figure 2A)** | S1-Tr, M2-FrA, M2-Ant, M1-Ant, V2-ML, V1-M, S1Hl/Fl — bilateral | Labels match `grin2b_eeg_channels.csv` exactly |
| **DOI** | 10.1111/epi.18606 | Updated in `grin2b_general_metadata.yaml` `related_publications` |

### Updated in this session

1. **`grin2b_general_metadata.yaml`**: `related_publications` set to `doi:10.1111/epi.18606`;
   `experiment_description` rewritten from paper abstract; full experimenter list added;
   `EMGArray` description updated to "neck muscles"; `EEGArray` location/description updated
   with confirmed cortical targets; `SleepScoring` scorer field updated with GitHub URLs.

2. **`grin2b_subjects_metadata.yaml`**: `strain` updated to `"Long-Evans"` for all 37 animals.

### Still open after paper

- [ ] **ADC → volts gain** — not in paper; still need TainiTec full-scale range from lab
- [ ] **NeuroNexus model number** and stereotaxic coordinates per channel
- [ ] **State 4** (`s_4` column in `pw_spectrum.csv`) — paper only mentions Wake/NREM/REM; ask lab
- [ ] **Lights-on clock time** at Edinburgh facility — paper confirms 12:12 L:D but not exact ZT0 time
- [ ] **Per-animal DOB / age at recording** — paper tracks adults but no per-animal dates
- [ ] **Sex/genotype** for animals 132, 383, 401, 402, 404, 424, 430, 433 — still not in any source
- [ ] **Missing raw `.dat` files** for ~16 animals — paper does not resolve

## 2026-06-25 — Supplementary Methods Findings

The supplementary information file resolved several more open questions:

| Question | Answer | Source |
|---|---|---|
| **ZT0 / lights-on time** | **07:00** | "SWDs and brain state data was analysed over 48 hours starting at zeitgeber time 07:00 am of the day after connection" |
| **BL1 start = ZT0** | **Confirmed** — BL1 starts at 07:00 the day after connection | Same sentence above |
| **NeuroNexus model** | **Custom H16-Rat EEG16_Functional** (NeuroNexus, United States) | Surgery section |
| **State 4 = SWD** | **Confirmed** — "All epochs identified to contain SWDs were classed separately from the other three brain states" → `s_4` = average PSD during seizure epochs | Sleep scoring section |
| **Ground electrode** | Separate cerebellar screw (-11.5 mm AP, ±0.5 mm ML), connected to grid via silver paint | Surgery section |
| **Reference** | Grid plus-symbol reference point aligned over bregma (plus structural holding screws at +4 mm AP, ±0.5 mm lateral) | Surgery section |
| **Surgery age** | 9–16 weeks at implantation | Surgery section |
| **Housing** | Mixed genotype cages before surgery; single-housed after surgery | Animals section |
| **SWD detection electrode** | Right hemisphere primary somatosensory cortex, AP -3.0 mm, ML 2.8 mm from bregma | Sleep scoring section |
| **Sleep scoring channel** | EEG channel over primary somatosensory cortex (either hemisphere) + one EMG channel, selected per-animal based on artefact level | Sleep scoring section |
| **Sleep scoring window** | 5-s non-overlapping epochs, 0.2–125 Hz, multitaper spectral analysis in R | Sleep scoring section |
| **SWD-in-sleep assignment** | SWDs occurring during wake: first 5 s epoch prior; SWDs in NREM/wake-NREM transitions: first 30 s (6 epochs) prior used for context | Sleep scoring section |
| **Spectral normalisation** | Baseline-corrected: normalized to average spectral power across REM+NREM+Wake per animal | Sleep scoring section |
| **Validation** | 90.8% overall agreement with visual scoring (17 animals, 4 h each, 10:00–14:00); κ = 0.83 | Sleep scoring section |
| **Software** | R + RStudio; ggplot2, car, lmerTest; SciPy welch for PSD; NumPy polyfit for spectral slope | Statistical Analysis / Sleep scoring |

### Updated in this session (supplementary)

1. **`grin2b_general_metadata.yaml`**: `lights_on_time` set to `"07:00"` (confirmed); NeuroNexus model name and ground screw details added to device description; state 4 updated to `SWD`.
2. **`state_power_spectrum_interface.py`**: `s_4` label changed from `Unknown_state_4` to `SWD`; module docstring, table description, and column descriptions updated.

### Still open after supplementary

- [ ] **ADC → volts gain** — not in paper or supplementary; ask lab
- [ ] **Per-channel stereotaxic coordinates** — SWD detection channel known (AP -3.0, ML 2.8); full grid layout not provided
- [ ] **Power spectrum units** — normalised to within-animal average; absolute units (µV²/Hz?) still unclear
- [ ] **Sex/genotype** for animals 132, 383, 401, 402, 404, 424, 430, 433
- [ ] **Missing raw `.dat` files** for ~16 animals

## 2026-07-09 — Split TainiRecordingInterface into separate EEG/EMG ElectricalSeries

Previously `TainiRecordingInterface` wrote all 16 channels (14 EEG + 2 EMG) as a single
`ElectricalSeries_{baseline_name}`, spanning two `ElectrodeGroup`s (EEGArray/EMGArray) in
one series. Rewrote it to write **two** `ElectricalSeries` instead, one per signal type,
while keeping a single shared electrode table (16 rows total, same as before) — only the
series and their `ElectrodeGroup` linkage are now separated.

### Changes

1. **`taini_recording_interface.py`** — constructor now takes a required `signal_type:
   Literal["EEG", "EMG"]` argument instead of writing all channels. Internally:
   - `es_key` is set to `f"{signal_type}ElectricalSeries"` (passed to
     `BaseRecordingExtractorInterface.__init__`), so each instance's `get_metadata()`
     populates its own `metadata["Ecephys"][es_key]`.
   - After the existing BL-window `frame_slice` and per-channel property assignment
     (`group_name`, `brain_area`, `hemisphere`, `filtering`, `location`), the recording is
     further restricted via `recording_extractor.select_channels(channel_ids=...)` to only
     the channels belonging to that signal type's `ElectrodeGroup` ("EEGArray" for EEG,
     "EMGArray" for EMG). Note: this spikeinterface version (0.104.3) uses
     `select_channels`, not the older `channel_slice` method.
   - `get_metadata()` names the series `f"{signal_type}ElectricalSeries{baseline_name}"`
     (e.g. `EEGElectricalSeriesBL1`, `EMGElectricalSeriesBL1`).
   - Two instances (one per signal_type) must be created per session, both pointed at the
     same `.dat` file and BL window. `neuroconv.tools.spikeinterface.add_electrodes_to_nwbfile`
     deduplicates electrode rows by `channel_id`, so the second instance's call appends only
     its own (new) channels to the electrode table built by the first — the table ends up
     with all 16 rows, written once, shared by both `ElectricalSeries`.

2. **`grin2bnwbconverter.py`** — `data_interface_classes["Recording"]` replaced with two
   entries, `EEGRecording` and `EMGRecording`, both mapped to `TainiRecordingInterface`.

3. **`convert_session.py`** — `source_data`/`conversion_options` now populate both
   `EEGRecording` and `EMGRecording` (same `file_path`, `bl_start_sample`, `bl_stop_sample`,
   `baseline_name`; differing only in `signal_type`).

Verified end-to-end with a `stub_test=True` run for GRIN2B_129 BL1: NWB file now contains
`acquisition/EEGElectricalSeriesBL1` (14 channels) and `acquisition/EMGElectricalSeriesBL1`
(2 channels), both referencing a single 16-row electrode table with `group` correctly set to
`EEGArray`/`EMGArray` per row.

### TODO

- [x] Update `notebooks/read_grin2b_nwb.ipynb` visualization code — now loads
  `EEGElectricalSeriesBL1` and `EMGElectricalSeriesBL1` separately (with updated
  per-series channel index maps for the raw-trace plots) instead of a single combined
  `ElectricalSeries_{baseline}`.
