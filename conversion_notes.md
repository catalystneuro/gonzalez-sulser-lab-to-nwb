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

## Remaining Assumptions (still to validate)

1. **Channel order in `.dat`:** assumed `[EEG_1..EEG_14, EMG_1, EMG_2]` per SoW phrasing, but TainiTec's wire order may put EMG first or interleave them. Must be confirmed by lab.
2. **NeuroNexus EEG grid model number** and per-channel anatomical targets — required for `ElectrodeGroup.location` and an electrodes-table column.
3. **ADC → volts gain** — the `.dat` values are dimensionless 12-bit; we need the TainiTec full-scale range (e.g. ±0.5 mV → conversion = 0.5e-3 / 2048).
4. **Sleep code legend** — `0/1/2` ⇄ `Wake/NREM/REM` is our best guess from rodent sleep distributions; **needs explicit confirmation**. The pw_spectrum file uses `s_0, s_1, s_2, s_4` (skipping `s_3`) — possibly an additional artifact/seizure state ID we haven't seen in `dge_ok.csv`. To confirm.
5. **`Channels.csv` exact derivation** — likely RMS envelope of one EEG and one EMG channel; would be useful to know which raw channels were chosen and the smoothing window so we can either reproduce or, ideally, omit.
6. **BL window start time-of-day** — the BL1 start (sample 18,088,897 ≈ 20 h into recording) is consistent across animals on the same date, suggesting a fixed offset (probably to skip a 20 h acclimation window, with BL1 then aligning to ZT0 / lights-on).
7. **Slot letter (A/B/C/D)** → animal position in transmitter grid (cosmetic only).
8. **Species & strain** — rat per SoW; strain not yet provided.
9. **One file = one animal** — confirmed by xlsx (one row pair per `<File, Animal ID>`).

## Open Questions (also see metadata_request_email.md)

Resolved by Phase 2 inspection:

- [x] TAINI `.dat` dtype = int16 LE, sample rate = 250.4 Hz, no header, 16ch interleaved
- [x] Seizure CSV time reference = seconds from BL window start (verified: max sec_end ≈ 86,400)
- [x] BL1/BL2 sample offsets = `Sample_start_end_GRIN2B.xlsx` (BL1 = 18,088,897 → 39,723,456 in `.dat`)
- [x] Top-level vs `seiz/` `Seizures.csv` are byte-identical → use one
- [x] Sleep epoch length = 5 s; epoch count = 17,280 = 24 h

Still open (asked in `metadata_request_email.md`):

- [ ] DOI of the GRIN2B publication and full author list
- [ ] **Channel order** in `.dat`: which indices = EEG_1..EEG_14 vs EMG_1, EMG_2 (which `chN` are reference/ground if any)
- [ ] **ADC → volts gain** (TainiTec full-scale; e.g. ±0.5 mV → `conversion = 0.5e-3 / 2048`)
- [ ] NeuroNexus EEG grid model and electrode positions (anatomical targets per channel)
- [ ] EMG placement (neck? trapezius?)
- [ ] Surgery / implantation protocol details for `ElectrodeGroup` description
- [ ] **Sleep-state label encoding**: confirm `0=Wake, 1=NREM, 2=REM`; what is state `4` referenced by `pw_spectrum.csv` columns?
- [ ] Subject metadata table (DOB, sex, weight, genotype WT vs HET, treatment group, surgery date, sacrifice date)
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

## Spyglass Compatibility (Aim 2)

Spyglass requires:
- `ElectrodeGroup` with `device` filled
- `LFP` data in a `processing/ecephys` module if downsampled
- Consistent `electrode_id` across files
- Subject metadata fields populated

Will revisit after Phase 6 testing.
