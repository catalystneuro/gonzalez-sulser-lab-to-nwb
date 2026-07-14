# Conversion Notes — Gonzalez-Sulser Lab to NWB

## Project Overview

Conversion of chronic EEG/EMG recordings from the Gonzalez-Sulser lab (University of Edinburgh) to NWB. Part of the SFARI Autism Rat Models Consortium (ARC). The lab has collected chronic EEG across **five SFARI lines** to study circadian rhythms, sleep–wake cycles, and seizure activity. Data is acquired wirelessly using a **TainiTec** system with **NeuroNexus EEG grids (14 EEG + 2 EMG channels)** over multi-day sessions (~3–4 days each), with two 24-h baseline (BL1/BL2) windows extracted per animal for analysis. The lab has automated sleep-state classification and seizure/SWD-scoring pipelines.

- **Lab POC:** Natalie Hung / Niamh McLaughlin
- **PI:** Prof. Alfredo Gonzalez-Sulser
- **CN team:** Ben Dichter, Alessandra Trapani
- **Repo:** <https://github.com/catalystneuro/gonzalez-sulser-lab-to-nwb>
- **Strategy:** Develop against the published GRIN2B line first; validate/extend to the remaining 4 lines afterward.
- **The 5 SFARI lines:** GRIN2B (in progress), SCN2A (next priority — hand-off to the Bender team), SYNGAP-GAP Deletion, NLGN3, 16p11.2, CDKL5. SCN2A uses screw electrodes through an interface board instead of the NeuroNexus grid; otherwise the recording/analysis pipeline is the same — the `TainiRecordingInterface` will need a screw-electrode channel-map variant for that line.
- **Downstream targets:** DANDI Archive (GRIN2B public; others embargoed) + Spyglass ingestion.
- **Publication:** Hristova K, Fasol MCM, McLaughlin N, Nawaz MS, Taskiran M, Buller-Peralta I, Harris AP, Sutherland A, Bassi A, Ocampo-Garces A, Escudero J, Kind PC, Gonzalez-Sulser A. Absence seizures and sleep–wake abnormalities in a rat model of GRIN2B neurodevelopmental disorder. *Epilepsia.* 2025;66:4996–5013. doi:10.1111/epi.18606

## Data Streams

| Stream | Format | File Pattern | NeuroConv Interface |
|---|---|---|---|
| Raw EEG/EMG | TainiTec `.dat` (int16 LE, 16ch interleaved, no header, 250.4 Hz) | `TAINI_<deviceID>_<band>_<line>_<animalID>_<condition>-<YYYY_MM_DD>-0000.dat` | `TainiRecordingInterface` (custom, wraps `spikeinterface.core.BinaryRecordingExtractor`) — instantiated twice per session (`signal_type="EEG"` / `"EMG"`) |
| Sleep state labels | CSV, 1 col (`sleep.score`), 17,280 rows (5-s epochs × 24 h) | `<line>_<animalID>/<line>_<animalID>_BL{1,2}-dge_ok.csv` | `SleepStateInterface` (custom) → `TimeIntervals` |
| Sleep power spectrum | CSV, 628 rows × cols `[hz, s_0, s_1, s_2, s_4]` | `..._BL{1,2}-pw_spectrum.csv` | `StatePowerSpectrumInterface` (custom) → `DynamicTable` in `processing["ecephys"]` |
| Sleep scoring input (`Channels.csv`) | CSV, 21.6M rows × 2 cols | `..._BL{1,2}_Channels.csv` | **Not converted** — derived envelope/RMS feature, not raw data; will not be republished |
| Seizure timestamps | CSV, tab-sep, cols `sec_start, sec_end, dur` | `Seizure timestamps/<line>_<animalID>_BL{1,2}_Seizures.csv` | `SeizureInterface` (custom) → `TimeIntervals` in `processing["behavior"]` |
| SWD per-epoch counts | CSV, 1 col, 17,280 rows | `<subject_dir>/seiz/<line>_<animalID>_BL{1,2}_DGE_SWDs.csv` | `SwdCountsInterface` (custom) → `TimeSeries` (rate=0.2 Hz) in `processing["behavior"]` |
| Per-ZT seizure totals | CSV, 24 rows × `[N_event, mean_dur, ZT, SWDs, Day]` | `<subject_dir>/seiz/<line>_<animalID>_BL{1,2}_Seiz_Totals.csv` | `SeizureTotalsInterface` (custom) → `DynamicTable` in `processing["behavior"]` |
| Light cycle / BL windows | XLSX | `Light cycle timing metadata/Sample_start_end_GRIN2B.xlsx` | No dedicated interface — parsed directly in `convert_session.py` to drive `session_start_time` and per-session BL sample offsets |
| Subject metadata | YAML (curated from lab CSVs + paper) | `src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_subjects_metadata.yaml` | `Subject` |

## Directory Structure

**Raw data share** (`H:/Gonzalez-Sulser-CN-data-share/`, read-only mount):

```text
Chronic EEG recordings/                    # 21 .dat files, ~2.2 GB each
  TAINI_<dev>_<band>_<line>_<animalID>_<cond>-<date>-0000.dat
  grin2b_eeg_channels.csv                  # confirmed channel layout (idx -> electrode label, hemisphere, group)
Light cycle timing metadata/
  Sample_start_end_GRIN2B.xlsx             # rows = sessions; cols = Animal ID, Line, File, Baseline, Start, End
Seizure timestamps/                        # 73 CSVs (per animal x BL1/BL2)
  GRIN2B_<animalID>_BL{1,2}_Seizures.csv
Sleep state classifications/               # 37 per-animal folders
  GRIN2B_<animalID>/
    GRIN2B_<animalID>_BL{1,2}-dge_ok.csv         # sleep.score, 17,280 epochs (5-s x 24h)
    GRIN2B_<animalID>_BL{1,2}-pw_spectrum.csv    # 628 rows; cols hz, s_0..s_2, s_4
    GRIN2B_<animalID>_BL{1,2}_Channels.csv       # 21.6M rows; derived feature, not raw
    sbh_<animalID>_BL{1,2}.png                   # sleep hypnogram plot
    spec_<animalID>_BL{1,2}.png                  # spectrogram plot
    seiz/
      GRIN2B_<animalID>_BL{1,2}_DGE_SWDs.csv     # spike-wave discharge per-epoch counts
      GRIN2B_<animalID>_BL{1,2}_Seiz_Totals.csv  # per-ZT seizure tallies
      GRIN2B_<animalID>_BL{1,2}_Seizures.csv     # byte-identical to top-level Seizures.csv
Subject metadata/
  GRIN2B_CDKL5_Seizures_Overall.csv        # sex/genotype for 29 of 37 animals
```

**Repository** (`src/gonzalez_sulser_lab_to_nwb/`):

```text
grin2b/
  grin2bnwbconverter.py           # Grin2bNWBConverter — wires all 7 interfaces
  convert_session.py              # session_to_nwb() — single (animal, baseline) entry point
  convert_all_sessions.py         # batch over all (animal, baseline) pairs, ProcessPoolExecutor
  interfaces/
    taini_recording_interface.py  # raw EEG/EMG
    sleep_state_interface.py
    seizure_interface.py          # SeizureInterface, SwdCountsInterface, SeizureTotalsInterface
    state_power_spectrum_interface.py
  metadata/
    grin2b_general_metadata.yaml
    grin2b_subjects_metadata.yaml
notebooks/read_grin2b_nwb.ipynb   # reads back an output NWB file and plots traces
inspect_data.py, inspection_report.json   # one-off Phase-2 data-audit script (not a test suite)
```

No `light_cycle_interface.py` exists — the light-cycle protocol is captured as static fields in `grin2b_general_metadata.yaml`, and per-session BL windows are read directly from the xlsx in `convert_session.py`. There is currently no `tests/` directory.

## File Inventory & Counts

- **Raw `.dat` files present:** 21 (animals 129–132, 137–140, 227–229, 236–241, 373, 378, 424 — the spring 2021/summer 2022 cohort).
- **Animals with sleep/seizure processed data:** 37 (129–140, 227–241, 362–369, 371, 373, 375, 378, 382, 383, 401, 402, 404, 430, 433).
- **Gap:** 16 animals (362–369, 371, 382, 383, 401, 402, 404, 430, 433) have processed sleep/seizure data but no raw `.dat` on the share. Per Alfredo (2026-07-14), the lab has most of these — they need to be uploaded by Natalie/Niamh.
- **`GRIN2B_424` xlsx error:** the xlsx maps animal 424 to `TAINI_1044_C_GRIN2B_366-2022_04_12-0000.dat` with BL windows that overlap animal 366's windows in the same file. The actual on-disk file for 424 is `TAINI_1044_C_Grin2B_424_Redo-2022_06_04-0000.dat` (present, but not referenced in the xlsx). Correct BL1/BL2 sample offsets for this file are still needed from the lab.

## Sessions / Subjects

- **Animals (GRIN2B line):** 37, identified by 3-digit IDs (e.g. `GRIN2B_129`); all confirmed Long-Evans (`LE-Grin2bem1Mcwi`, RRID:RGD_14394515), Grin2b+/− (Het) or Grin2b+/+ (WT) littermates.
- **Age:** not available per-animal as an exact DOB; lab confirmed animals were 16–19 weeks old at recording. `Subject.age` is set to the ISO 8601 range `P16W/P19W` for all animals (DANDI-compliant alternative to `date_of_birth`); weight is not available and is omitted.
- **Sex/genotype gap:** 8 animals (132, 383, 401, 402, 404, 424, 430, 433) still have `TODO` placeholders for `sex`/`genotype` in `grin2b_subjects_metadata.yaml` — not present in any source seen so far.
- **Per animal:** two baselines (BL1, BL2), each a 24-h window (21,634,560 samples at 250.4 Hz) extracted from a 72–96 h raw recording. BL1 starts at Zeitgeber time 07:00 (lights-on) the day after headstage connection; BL2 immediately follows BL1. Published sleep/seizure numbers are averaged across BL1+BL2 where both are usable — a few animals may have only one usable baseline, and this is not currently flagged per-animal anywhere.
- **Recording device:** TainiTec transmitters (device IDs 1044, 1045, 1047, 1048); up to 4 animals recorded in parallel on the same date.
- **Filename convention** (confirmed): `TAINI_<deviceID>_<band>_<line>_<animalID>_<condition>-<YYYY_MM_DD>-0000.dat`
  - `deviceID` — TainiTec transmitter ID.
  - Second field (previously called "slot") — confirmed to be the TainiTec **receiver frequency band** (A/B/C/D); all transmitters sharing a band use the same letter (not a physical animal position).
  - `condition` — recording label (`Baseline`, `Baseline_Attempt2`, `Redo`, etc.).
  - `-0000` suffix — always `0000`; no multi-file sessions observed.
  - Date — recording start date, local Edinburgh time (no time-of-day is encoded in the filename).

## Existing Resources

- **Publication:** Hristova et al. 2025, Epilepsia, doi:10.1111/epi.18606 (full citation above).
- **Sleep-scoring code:** [`Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER`](https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER) (R; also used in Buller-Peralta et al. 2022, Brain Commun, doi:10.1093/braincomms/fcac263).
- **SWD/seizure-detection code:** [`Gonzalez-Sulser-Team/SWD-Automatic-Identification-2025`](https://github.com/Gonzalez-Sulser-Team/SWD-Automatic-Identification-2025) (also archived at [zenodo:12700972](https://zenodo.org/records/12700972)).
- **TainiTec reference `.dat` reader:** a Python snippet was provided by TainiTec support confirming our de-interlacing approach (`dat_raw[c::16]` per channel matches their own `parse_dat()`). Their example script hardcodes `sample_rate = 256.4`, which is inconsistent with the 250.4 Hz derived independently from `Channels.csv` row counts and the xlsx BL windows — we keep 250.4 Hz (corroborated by two lab-provided artifacts) and treat 256.4 as a stale/generic placeholder in TainiTec's demo code.
- **Data source:** local mount at `H:/Gonzalez-Sulser-CN-data-share/` (read-only share).

## Interface Mapping

| Interface | Writes | Status |
|---|---|---|
| `TainiRecordingInterface` (×2: EEG/EMG) | Two `ElectricalSeries` (`EEGElectricalSeries<baseline>`, `EMGElectricalSeries<baseline>`) sharing one 16-row electrode table, distinct `ElectrodeGroup`s (`EEGArray`/`EMGArray`) | Channel map, ADC gain (`13000 µV / 4096 codes ≈ 3.174 µV/code`, applied via `set_channel_gains`), and per-channel AP/ML stereotaxic coordinates (keyed by `(label, hemisphere)`, not TAINI pin) are all implemented. |
| `SleepStateInterface` | `TimeIntervals` (`sleep_states`) in `processing["behavior"]` | Functional; state-code mapping (0=Wake, 1=NREM, 2=REM, 4=SWD) now matches `StatePowerSpectrumInterface`. |
| `SeizureInterface` | `TimeIntervals` (`seizure_events`) in `processing["behavior"]` | Functional. |
| `SwdCountsInterface` | `TimeSeries` (`swd_epoch_counts`, rate 0.2 Hz) in `processing["behavior"]` | Functional. |
| `SeizureTotalsInterface` | `DynamicTable` (`seizure_totals_by_zt`) in `processing["behavior"]` | Functional; column semantics (`N_event`, `mean_dur`, `Day`) still marked TODO for lab confirmation in the table description. |
| `StatePowerSpectrumInterface` | `DynamicTable` (`sleep_state_power_spectra`) in `processing["ecephys"]` | Functional; state labels (Wake/NREM/REM/SWD) confirmed from paper supplement; absolute PSD units (µV²/Hz vs. normalized) still unconfirmed. |
| Light cycle / BL windows | No dedicated interface — parsed in `convert_session.py` | Drives `session_start_time` (anchored to the confirmed 07:00 BL1 start, see Temporal Alignment) and per-session BL sample offsets passed to every other interface. |

`Grin2bNWBConverter` (`grin2bnwbconverter.py`) registers all 7 data interfaces above. `convert_session.py::session_to_nwb()` resolves file paths per `(animal_id, baseline)`, conditionally includes each optional stream if its CSV exists on disk, and merges general + per-subject metadata YAMLs. `convert_all_sessions.py` batches this over every `(animal, baseline)` pair with a `.dat` file present, using `ProcessPoolExecutor` and per-session error capture. CLI `argparse` blocks in both scripts are currently commented out in favor of hardcoded local paths in `__main__` — not yet portable/CI-ready.

Dependencies (`pyproject.toml`, `[grin2b]` extra): `neuroconv`, `spikeinterface>=0.100`, `pynwb>=2.8`, `pandas`, `openpyxl`, `pyyaml`, `hdmf`. `ndx-events` was tried for the seizure table at one point and then reverted in favor of plain `pynwb.epoch.TimeIntervals` — it is not a current dependency.

## Metadata

- **`grin2b_general_metadata.yaml`**: `NWBFile` (experiment description, institution, lab, full experimenter list, keywords, `related_publications: doi:10.1111/epi.18606`), `LightCycle` (12:12 LD, lights-on 07:00, Europe/London), `SleepScoring` (epoch duration, scorer/SWD-detector repo links, confirmed `state_labels` 0/1/2/4 = Wake/NREM/REM/SWD). `Device`/`ElectrodeGroup`/per-channel electrode metadata are deliberately **not** set in this yaml — they are computed programmatically in `TainiRecordingInterface.get_metadata()`/`__init__()` (ADC gain, stereotaxic coordinates, ground/reference details), which is documented in both files as the single source of truth; a duplicate `Device`/`ElectrodeGroup` block here would silently win over the code-computed values via `dict_deep_update(code_metadata, yaml_metadata)` in `convert_session.py`.
- **`grin2b_subjects_metadata.yaml`**: all 37 `GRIN2B_<id>` entries with `species`, `strain` ("Long-Evans"), `age` (`P16W/P19W`), boilerplate `description` (IACUC/RRID text); `genotype`/`sex` populated for 29/37 animals, `TODO` placeholders remain for the other 8 (132, 383, 401, 402, 404, 424, 430, 433). Missing/`TODO` fields are filtered out at conversion time in `convert_session.py` before being merged into the NWB `Subject` metadata (so a `TODO` string never leaks into an output file); `sex` defaults to `"U"` and `species` to `"Rattus norvegicus"` if absent.

## Temporal Alignment

Single-clock design — every stream in a session derives from one TainiTec `.dat` file per animal, so alignment is purely arithmetic (no cross-device sync needed):

```text
Reference clock:  TainiTec .dat sample index (fs = 250.4 Hz)

Sleep CSVs:       t_dat = bl_start_sample / 250.4 + epoch_index * 5.0
Seizure CSVs:     t_dat = bl_start_sample / 250.4 + sec_start   (sec_start already relative to BL start)
SWD counts:       same 5-s epoch grid as sleep CSVs
Raw EEG/EMG:      starting_time = bl_start_sample / 250.4 (via recording_extractor.annotate(t_start=...))
```

`session_start_time` (sample 0 of the `.dat` file) is computed by `_compute_session_start_time()` in `convert_session.py`. The `.dat` filename only encodes the recording start *date* (no time-of-day is logged by the lab), so the timestamp is back-computed from the one confirmed anchor: BL1 always starts at Zeitgeber time **07:00** local (`Europe/London`) time the day after headstage connection. `session_start_time` is set so that `session_start_time + bl1_start_sample/250.4` equals 07:00 on `filename_date + 1 day`; a BL2 file for the same animal reuses this same `session_start_time`, so its own BL offset lands on the correct absolute time automatically (verified across a UK daylight-saving transition). If an animal has no BL1 window at all, this falls back to midnight of the filename date (time-of-day unknown for that animal).

## Open Questions

Items that need input from the lab (Natalie Hung / Niamh McLaughlin / Alfredo Gonzalez-Sulser) before they can be resolved:

- **16 missing raw `.dat` files** (animals 362–369, 371, 382, 383, 401, 402, 404, 430, 433) — lab says most exist and need uploading; not yet on the share.
- **`GRIN2B_424` BL1/BL2 sample offsets** for the correct on-disk file (`..._Grin2B_424_Redo-2022_06_04-0000.dat`) — xlsx currently points at the wrong file with overlapping windows vs. animal 366.
- **Sex/genotype** still missing for 8 animals (132, 383, 401, 402, 404, 424, 430, 433).
- **Power spectrum units** (`s_0…s_4` in `pw_spectrum.csv`) — known to be baseline-corrected/normalized per-animal, but absolute units (µV²/Hz?) unconfirmed.
- **`Seiz_Totals.csv` column semantics** (`N_event`, `mean_dur`, `Day` encoding) not fully confirmed.
- **Single-baseline caveat** — confirm which (if any) animals have only BL1 or only BL2 usable, so downstream averages aren't silently mis-computed; not flagged per-animal in any source yet.
- **Sleep state classifications folder README** — no per-file documentation exists yet from the lab for what each file/plot in `Sleep state classifications/<animal>/` represents beyond what's been reverse-engineered here.

## TODOs

Internal code/repo work, not blocked on the lab:

1. ~~Wire up the 07:00 BL1 start time~~ — **done.** `_parse_recording_date()` replaced by `_compute_session_start_time()` in `convert_session.py`: back-computes `session_start_time` (sample 0 of the `.dat` file) from the lab-confirmed anchor (BL1 sample offset = Zeitgeber time 07:00 the day after connection), so both the BL1 and BL2 NWB files for an animal share a correct absolute clock. Falls back to midnight only if an animal has no BL1 window at all.
2. ~~Reconcile `sleep_state_interface.py`~~ — **done.** State-code mapping now matches `state_power_spectrum_interface.py` (0=Wake, 1=NREM, 2=REM, 4=SWD); docstring, `_STATE_LABELS`, and table/column descriptions no longer say "unconfirmed"/`"Unknown"`.
3. ~~Clean up stale `Electrodes.channel_conversion` TODO~~ — **done.** Removed the dead `Electrodes`/`Device`/`ElectrodeGroup` blocks from `grin2b_general_metadata.yaml` (they were silently overriding the code-computed values via `dict_deep_update`); the ground-screw/reference/independence details they held were folded into `TainiRecordingInterface.get_metadata()`, which is now documented as the single source of truth for this metadata.
4. **No automated tests** exist for the interfaces or conversion pipeline; CLI entry points (`argparse`) are commented out in favor of hardcoded local paths in `convert_session.py`/`convert_all_sessions.py`.
5. **SCN2A sub-package**: needs a screw-electrode channel-map variant of `TainiRecordingInterface` (no NeuroNexus grid) — design pending a call with Niamh.
6. **Generalize the pipeline to the other 4 SFARI lines** — only the metadata YAML files (general + subjects) should remain line-specific; interfaces/converter/conversion scripts should be parameterized rather than GRIN2B-hardcoded.
7. **Major refactor of the conversion pipeline design**: write **one NWB file per subject** containing the **full raw recording** (not just the BL1/BL2 slices), with an **epoch table** marking the BL1 and BL2 windows within it. Under this design, `processing/behavior` and `processing/ecephys` hold both baselines' derived tables/series side by side, one pair per baseline instead of one file per baseline:
   - `processing/behavior`:
     - `seizure_events` → `seizure_events_baseline_window_1`, `seizure_events_baseline_window_2` (`TimeIntervals`)
     - `sleep_states` → `sleep_states_baseline_window_1`, `sleep_states_baseline_window_2` (`TimeIntervals`)
     - `swd_epoch_counts` → `swd_epoch_counts_baseline_window_1`, `swd_epoch_counts_baseline_window_2` (`TimeSeries`)
     - `seizure_totals_by_zt` → `seizure_totals_by_zt_baseline_window_1`, `seizure_totals_by_zt_baseline_window_2` (`DynamicTable`)
   - `processing/ecephys`:
     - `sleep_state_power_spectra` → `sleep_state_power_spectra_baseline_window_1`, `sleep_state_power_spectra_baseline_window_2` (`DynamicTable`), with columns renamed from `s_0`/`s_1`/`s_2`/`s_4` to the actual state names (`Wake`/`NREM`/`REM`/`SWD`).
