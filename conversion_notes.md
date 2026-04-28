# Conversion Notes — Gonzalez-Sulser Lab to NWB

## Project Overview

Conversion of chronic EEG/EMG recordings from the Gonzalez-Sulser lab (University of Edinburgh) to NWB. Part of the SFARI Autism Rat Models Consortium (ARC). The lab has collected chronic EEG across **five SFARI lines** to study circadian rhythms, sleep–wake cycles, and seizure activity. Data is acquired wirelessly using a **TainiTec** system with **NeuroNexus EEG grids (14 EEG + 2 EMG channels)** over multi-day sessions (~3 days each). The lab has automated sleep-state classification and seizure scoring pipelines.

- **Lab POC:** Natalie Hung
- **PI:** Prof. Alfredo Gonzalez-Sulser
- **CN team:** Ben Dichter, Alessandra Trapani
- **Repo:** https://github.com/catalystneuro/gonzalez-sulser-lab-to-nwb (to be created)
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

```
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

## Assumptions (to validate)

1. **TAINI `.dat` binary layout:** int16, 16 channels (14 EEG + 2 EMG) interleaved sample-by-sample, no header. Inferred from file size (2.22 GB) ÷ (16 ch × 2 bytes × 250.4 Hz) ≈ 3.2 days, consistent with SoW "~3 days".
2. **Sampling rate:** 250.4 Hz (TainiTec default for 16-ch wireless headstage). To confirm with lab — could also be 250 Hz exactly or 19531.25 Hz raw with downsample.
3. **Endianness / dtype:** little-endian int16 assumed.
4. **Channel order in `.dat`:** assumed `[EEG_1..EEG_14, EMG_1, EMG_2]`. Actual mapping must come from the lab.
5. **EEG grid layout:** NeuroNexus EEG grid — exact part number / electrode coordinates not in share.
6. **Sleep epochs:** 5-second epochs (17,280 epochs × 5 s = 86,400 s = 24 h). Class labels in `sleep.score` column likely encode {Wake, NREM, REM, artifact}; mapping needed.
7. **`Channels.csv` two columns:** assumed = the EEG and EMG channel selected for sleep scoring (1 each). Derivable from raw `.dat` and channel selection in `*_Channels.csv` (which currently shows all-zeros in the head — possibly an index file rather than data; needs deeper inspection).
8. **BL1 / BL2 = day-1 / day-2** of the multi-day recording, with start/end sample indices given in `Sample_start_end_GRIN2B.xlsx`. Used to align sleep and seizure timestamps to absolute time within the raw `.dat`.
9. **Slot letter (A/B/C/D)** in TAINI filename = TainiTec receiver slot, not channel mapping.
10. **Species:** Rat (per SoW "SFARI Autism Rat Models Consortium"). Strain TBD (Long-Evans? Sprague-Dawley?).
11. **Seizure CSV time origin:** `sec_start` / `sec_end` are seconds from the start of the BL window (not from start of `.dat`). Needs confirmation — if from start of BL, we add the BL1/BL2 offset from the xlsx to align to session time.
12. **`pw_spectrum.csv`:** likely a per-state averaged power spectrum (5 columns = 5 sleep states or 5 frequency bands). Columns named `s_0, s_1, s_2, s_4` (note `s_3` missing) — possibly state codes. Likely a *derived* product; we may publish as a `processing` module table or omit.
13. **One file = one animal:** each `.dat` contains a single animal's 16 channels (TainiTec one-headstage-per-transmitter model).

## Open Questions (also see metadata_request_email.md)

- [ ] DOI of the GRIN2B publication and full author list
- [ ] TAINI `.dat` exact format spec (dtype, channel order, sample rate, header bytes if any)
- [ ] NeuroNexus EEG grid model and electrode positions (anatomical targets per channel)
- [ ] EMG placement (neck? trapezius?)
- [ ] Surgery / implantation protocol details for `ElectrodeGroup` description
- [ ] Sleep-state label encoding (which integer = Wake/NREM/REM/artifact?)
- [ ] Seizure CSV time reference (from BL start? from `.dat` start? UTC?)
- [ ] `sleep.score` codes legend
- [ ] Subject metadata table (DOB, sex, weight, genotype WT vs HET, treatment group, surgery date, sacrifice date)
- [ ] Light-cycle protocol (12:12? lights-on Zeitgeber time)
- [ ] Per-session start time with timezone (Edinburgh local = Europe/London)
- [ ] Why are there 37 animals' processed data but only 21 raw `.dat` files?
- [ ] Existing GRIN2B repo / TAINI reader code (URL)
- [ ] Are the duplicate `Seizures.csv` (top-level vs `seiz/`) identical?
- [ ] List of all 5 SFARI lines and which is the next priority after GRIN2B

## Conversion Plan (high-level)

**Phase 5 deliverables (per the canonical NeuroConv repo template):**

```
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
