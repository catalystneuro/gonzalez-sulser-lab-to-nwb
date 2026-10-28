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
| Raw EEG/EMG | TainiTec `.dat` (int16 LE, 16ch interleaved, no header, 250.4 Hz) | `TAINI_<deviceID>_<band>_<line>_<animalID>_<condition>-<YYYY_MM_DD>-0000.dat` | `TainiRecordingInterface` (custom, wraps `spikeinterface.core.BinaryRecordingExtractor`) — instantiated twice per subject (`signal_type="EEG"` / `"EMG"`), writing the **full recording** (not a BL slice) |
| BL1/BL2 baseline windows | XLSX sample offsets | `Sample_start_end_GRIN2B.xlsx` | `BaselineEpochsInterface` (custom) → NWB `epochs` table (tags `BL1`/`BL2`), marking the baseline windows within the full recording |
| Sleep state labels | CSV, 1 col (`sleep.score`), 17,280 rows (5-s epochs × 24 h) | `<line>_<animalID>/<line>_<animalID>_BL{1,2}-dge_ok.csv` | `SleepStateInterface` (custom) → `TimeIntervals`, instantiated once per available baseline |
| Sleep power spectrum | CSV, 628 rows × cols `[hz, s_0, s_1, s_2, s_4]` | `..._BL{1,2}-pw_spectrum.csv` | `StatePowerSpectrumInterface` (custom) → `DynamicTable` in `processing["ecephys"]`, instantiated once per available baseline; `s_0..s_4` columns renamed to `Wake`/`NREM`/`REM`/`SWD` |
| Sleep scoring input (`Channels.csv`) | CSV, 21.6M rows × 2 cols | `..._BL{1,2}_Channels.csv` | **Not converted** — derived envelope/RMS feature, not raw data; will not be republished |
| Seizure timestamps | CSV, tab-sep, cols `sec_start, sec_end, dur` | `Seizure timestamps/<line>_<animalID>_BL{1,2}_Seizures.csv` | `SeizureInterface` (custom) → `TimeIntervals` in `processing["behavior"]`, instantiated once per available baseline |
| SWD per-epoch flags | CSV, 1 col, 17,280 rows, codes 6 = SWD / 4 = no SWD | `<subject_dir>/seiz/<line>_<animalID>_BL{1,2}_DGE_SWDs.csv` | `SwdEpochsInterface` (custom) → `TimeIntervals` (`swd_epochs`, boolean `is_swd`) in `processing["behavior"]` |
| Per-ZT-hour seizure counts | CSV, 24 rows × `[N_event, mean_dur, ZT, SWDs, Day]` | `<subject_dir>/seiz/<line>_<animalID>_BL{1,2}_Seiz_Totals.csv` | `SeizureTotalsInterface` (custom) → `DynamicTable` (`seizure_counts_by_zt_hour`, from `ZT`/`SWDs` only) in `processing["behavior"]` |
| Subject metadata | YAML (curated from lab CSVs + paper) | `src/gonzalez_sulser_lab_to_nwb/grin2b/metadata/grin2b_subjects_metadata.yaml` | `Subject` |

## Directory Structure

**Raw data share** (`H:/Gonzalez-Sulser-CN-data-share/`, read-only mount):

```text
Chronic EEG recordings/                    # 24 .dat files, ~2.1-2.9 GB each
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
  grin2bnwbconverter.py           # Grin2bNWBConverter — wires 13 interface slots (recording + epochs + 5 streams x 2 baselines)
  convert_session.py              # session_to_nwb() — one NWB file per subject (both baselines)
  convert_all_sessions.py         # batch over all subjects with a .dat file present, ProcessPoolExecutor
  interfaces/
    taini_recording_interface.py  # raw EEG/EMG, full recording 
    baseline_epochs_interface.py  # BaselineEpochsInterface — BL1/BL2 rows in the NWB epochs table
    sleep_state_interface.py
    seizure_interface.py          # SeizureInterface, SwdEpochsInterface, SeizureTotalsInterface
    state_power_spectrum_interface.py
  metadata/
    grin2b_general_metadata.yaml
    grin2b_subjects_metadata.yaml
notebooks/read_grin2b_nwb.ipynb   # reads back an output NWB file and plots traces
inspect_data.py, inspection_report.json   # one-off Phase-2 data-audit script (not a test suite)
```

Per-baseline interfaces (`SleepStates`, `Seizures`, `SwdCounts`, `SeizureTotals`, `StatePowerSpectrum`) are each registered once in `Grin2bNWBConverter` and take `file_paths` as a dict keyed by baseline label (`"baseline_window_1"`/`"baseline_window_2"`, the same strings used as epochs-table tags). Each writes one merged table with a `baseline_window` column, and each file is aligned to the epochs-table row with the matching tag (`get_baseline_start_times()` in `baseline_epochs_interface.py`). A baseline with no CSV for a given stream is left out of that stream only. The light-cycle protocol is captured as static fields in `grin2b_general_metadata.yaml`; per-subject BL windows are read directly from the xlsx in `convert_session.py`. `tests/test_missing_baseline.py` covers the missing-baseline case (run with `pytest tests`).

## File Inventory & Counts

- **Raw `.dat` files present:** 24 (animals 129–132, 137–140, 227–229, 236–241, 373, 375, 378, 401, 402, 404, 424). These are all 24 non-excluded animals, and all are convertible. The 401/402/404 files were shared on 2026-10-28.
- **Animals with sleep/seizure processed data:** 37 (129–140, 227–241, 362–369, 371, 373, 375, 378, 382, 383, 401, 402, 404, 430, 433).
- **Excluded animals (13):** 362–369, 371, 382, 383, 430, 433. These were excluded from Hristova et al. 2025 after a breeding mix-up (the wild types had an unusually high number of seizures); the exclusion is described in the paper. They have processed sleep/seizure data but no raw `.dat` on the share, and the PI prefers not to publish them. `convert_session.EXCLUDED_ANIMAL_IDS` lists them: `session_to_nwb()` refuses them and `convert_all_sessions` skips them.
- **`GRIN2B_424` xlsx filename error (resolved in code):** the xlsx rows for 424 (rows 70–71) have 424's own Start/End offsets but their `File` column names animal 366's recording, `TAINI_1044_C_GRIN2B_366-2022_04_12-0000.dat`. The 424 file on the share is `TAINI_1044_C_Grin2B_424_Redo-2022_06_04-0000.dat` (66,244,248 samples, so the xlsx BL2 end sample 61,042,512 fits). Treated as a copy-paste error in the filename only: `convert_session._DAT_FILE_CORRECTIONS` maps 424 to the Redo file and keeps the xlsx offsets. The resulting `session_start_time` is 2022-06-04 11:17 BST (BL1 at 07:00 on 2022-06-05).

## Sessions / Subjects

- **Animals (GRIN2B line):** 37, identified by 3-digit IDs (e.g. `GRIN2B_129`); all confirmed Long-Evans (`LE-Grin2bem1Mcwi`, RRID:RGD_14394515), Grin2b+/− (Het) or Grin2b+/+ (WT) littermates.
- **Age:** not available per-animal as an exact DOB; lab confirmed animals were 16–19 weeks old at recording. `Subject.age` is set to the ISO 8601 range `P16W/P19W` for all animals (DANDI-compliant alternative to `date_of_birth`); weight is not available and is omitted.
- **Sex/genotype:** set for all 37 animals in `grin2b_subjects_metadata.yaml`, all matching `Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv`. That CSV lists every GRIN2B animal; 132, 401, 402, 404 and 424 had been left as `TODO` by mistake and were filled from it on 2026-10-28 (132 Wt M, 401/402/404 Wt F, 424 Het M). The excluded-animal list the PI sent on 2026-10-20 also agrees with it.
- **Per animal:** one NWB file containing the full 72–96 h raw recording, with two baselines (BL1, BL2) — each a 24-h window (21,634,560 samples at 250.4 Hz) — marked as rows in the NWB epochs table. BL1 starts at Zeitgeber time 07:00 (lights-on) the day after headstage connection; BL2 immediately follows BL1. Published sleep/seizure numbers are averaged across BL1+BL2 where both are usable — a few animals may have only one usable baseline, and this is not currently flagged per-animal anywhere.
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
| `TainiRecordingInterface` (×2: EEG/EMG) | Two `ElectricalSeries` (`EEGElectricalSeries`, `EMGElectricalSeries`), each covering the **full raw recording** (`starting_time=0`), sharing one 16-row electrode table, distinct `ElectrodeGroup`s (`EEGArray`/`EMGArray`) | Channel map, ADC gain (`13000 µV / 4095 ≈ 3.1746 µV/code`, as in TainiTec's `parse_dat.m`, applied via `set_channel_gains`), and per-channel AP/ML stereotaxic coordinates (keyed by `(label, hemisphere)`, not TAINI pin) are all implemented. Packet-loss samples (`32767`) are kept and documented in the series description. |
| `BaselineEpochsInterface` | NWB `epochs` table rows for BL1 and/or BL2 (tags `["BL1"]`/`["BL2"]`) | Marks the baseline windows within the full recording; replaces the old per-baseline-file design. |
| `SleepStateInterface` | `TimeIntervals` (`sleep_states`, `baseline_window` column) in `processing["behavior"]` | Functional; state-code mapping (0=Wake, 1=NREM, 2=REM, 4=SWD) matches `StatePowerSpectrumInterface`. |
| `SeizureInterface` | `TimeIntervals` (`seizure_events`, `baseline_window` column) in `processing["behavior"]` | Functional. Table is skipped if no baseline has any seizure (e.g. GRIN2B_238). |
| `SwdEpochsInterface` | `TimeIntervals` (`swd_epochs`, 5-s epochs, boolean `is_swd`, `baseline_window` column) in `processing["behavior"]` | Functional; code meaning from `cepstral_analysis.m`. |
| `SeizureTotalsInterface` | `DynamicTable` (`seizure_counts_by_zt_hour`, `baseline_window` column) in `processing["behavior"]` | Functional; writes the hourly `SWDs` counts only (see Lab analysis code below). |
| `StatePowerSpectrumInterface` | `DynamicTable` (`sleep_state_power_spectra`, `baseline_window` column) in `processing["ecephys"]`, columns named `Wake`/`NREM`/`REM`/`SWD` (renamed from `s_0`/`s_1`/`s_2`/`s_4`) | Functional; units derived from the lab's R code (see Lab analysis code below). These are standard outputs of the lab's sleep pipeline; the spectra in the paper were computed another way (Alfredo, 2026-10-20). |

`Grin2bNWBConverter` (`grin2bnwbconverter.py`) registers 8 interface slots: `EEGRecording`, `EMGRecording`, `BaselineEpochs`, and one slot for each of the 5 per-baseline stream interfaces. `convert_session.py::session_to_nwb()` resolves the `.dat` file and any available BL1/BL2 windows per `animal_id`, collects each stream's CSVs into a dict keyed by baseline label (a missing CSV is left out of that stream), and merges general + per-subject metadata YAMLs into a single NWB file per subject. `convert_all_sessions.py` batches this over every animal with a `.dat` file present (one `session_to_nwb()` call per animal, covering both baselines), using `ProcessPoolExecutor` and per-subject error capture. CLI `argparse` blocks in both scripts are currently commented out in favor of hardcoded local paths in `__main__` — not yet portable/CI-ready.

Dependencies (`pyproject.toml`, `[grin2b]` extra): `neuroconv`, `spikeinterface>=0.100`, `pynwb>=2.8`, `pandas`, `openpyxl`, `pyyaml`, `hdmf`. `ndx-events` was tried for the seizure table at one point and then reverted in favor of plain `pynwb.epoch.TimeIntervals` — it is not a current dependency.

**NeuroConv version:** the HERD annotation support (`neuroconv.tools.external_resources`) is not in a released NeuroConv yet; the pipeline runs against a local NeuroConv checkout of the `herd-anatomy-annotation` branch ([catalystneuro/neuroconv#2151](https://github.com/catalystneuro/neuroconv/pull/2151), which builds on #2149 and #2148). That also brings NeuroConv `main`'s dict-based ecephys metadata (#1934, #1941), so `TainiRecordingInterface.get_metadata()` now emits a top-level `Devices` registry and `Ecephys["ElectrodeGroups"]` / `Ecephys["ElectricalSeries"]` keyed by metadata key (groups link to the device via `device_metadata_key`), and the interface passes `metadata_key=` instead of the deprecated `es_key=`. Pin `neuroconv` in `pyproject.toml` once the HERD work is released.

## Metadata

- **`grin2b_general_metadata.yaml`**: `NWBFile` (experiment description, institution, lab, full experimenter list, keywords, `related_publications: doi:10.1111/epi.18606`), `LightCycle` (12:12 LD, lights-on 07:00, Europe/London), `SleepScoring` (epoch duration, scorer/SWD-detector repo links, confirmed `state_labels` 0/1/2/4 = Wake/NREM/REM/SWD). `Device`/`ElectrodeGroup`/per-channel electrode metadata are deliberately **not** set in this yaml — they are computed programmatically in `TainiRecordingInterface.get_metadata()`/`__init__()` (ADC gain, stereotaxic coordinates, ground/reference details), which is documented in both files as the single source of truth; a duplicate `Device`/`ElectrodeGroup` block here would silently win over the code-computed values via `dict_deep_update(code_metadata, yaml_metadata)` in `convert_session.py`.
- **Ontology annotation (HERD)** — `grin2b_general_metadata.yaml` carries an `ExternalResources` block in NeuroConv's file-wide format (`species` / `strain` / `genotype` / `brain_regions` maps, each keyed by the exact value string it annotates, each term an explicit `{id, uri}`). NeuroConv's `run_conversion` writes these as HERD references under `/general/external_resources`; there is no call in `convert_session.py`. NeuroConv ignores any other key, so files converted while the YAML still used the older `ontology` key (including the 2026-10-21 and 2026-10-28 runs) have no references; `tests/test_external_resources.py` guards against this. Terms: species `NCBITaxon:10116`; strain `Long-Evans` → `RRID:RGD_2308852` (Crl:LE, Charles River), since the RGD report for `LE-Grin2bem1Mcwi` states the line was made by editing Crl:LE embryos; genotype `Het` → `RRID:RGD_14394515` (`LE-Grin2bem1Mcwi`), with `Wt` left unannotated because wild-type littermates carry no engineered allele; the per-channel location labels (`S1_Tr`, `M2_Fra`, ...), which are lab acronyms, and the two `ElectrodeGroup.location` values (`cortex` → `UBERON:0000956`, `trapezius muscle` → `UBERON:0002380`) map to UBERON. A Het stub (GRIN2B_129) gets 13 references and a WT stub (GRIN2B_401) 12. Until 2026-10-28 the strain was annotated with the line RRID, before NeuroConv had a genotype map.
- **`grin2b_subjects_metadata.yaml`**: all 37 `GRIN2B_<id>` entries with `species`, `strain` ("Long-Evans"), `age` (`P16W/P19W`), boilerplate `description` (IACUC/RRID text); `genotype`/`sex` populated for all 37 animals from `GRIN2B_CDKL5_Seizures_Overall.csv`. Missing/`TODO` fields are filtered out at conversion time in `convert_session.py` before being merged into the NWB `Subject` metadata (so a `TODO` string never leaks into an output file); `sex` defaults to `"U"` and `species` to `"Rattus norvegicus"` if absent.

## Temporal Alignment

Single-clock design — every stream in a session derives from one TainiTec `.dat` file per animal, so alignment is purely arithmetic (no cross-device sync needed):

```text
Reference clock:  TainiTec .dat sample index (fs = 250.4 Hz), sample 0 = session_start_time

Sleep CSVs:       t_dat = bl_start_sample / 250.4 + epoch_index * 5.0
Seizure CSVs:     t_dat = bl_start_sample / 250.4 + sec_start   (sec_start already relative to BL start)
SWD counts:       same 5-s epoch grid as sleep CSVs
BL1/BL2 windows:  epochs table rows at [bl_start_sample / 250.4, (bl_stop_sample + 1) / 250.4]
Raw EEG/EMG:      full recording, starting_time = 0 (no BL slicing — BL windows are epochs-table rows, not data slices)
```

`session_start_time` (sample 0 of the `.dat` file) is computed by `_compute_session_start_time()` in `convert_session.py`. The `.dat` filename only encodes the recording start *date* (no time-of-day is logged by the lab), so the timestamp is back-computed from the one confirmed anchor: BL1 always starts at Zeitgeber time **07:00** local (`Europe/London`) time the day after headstage connection. `session_start_time` is set so that `session_start_time + bl1_start_sample/250.4` equals 07:00 on `filename_date + 1 day`; BL2 (and the full raw recording) share this same `session_start_time`, so BL2's own sample offset lands on the correct absolute time automatically (verified across a UK daylight-saving transition). If an animal has no BL1 window at all, this falls back to midnight of the filename date (time-of-day unknown for that animal).

## Conversion Run Log (2026-07-29)

Full (non-stub) `convert_all_sessions`-equivalent run against `H:/Gonzalez-Sulser-CN-data-share` → `H:/gonzalez-nwbfiles`, using env `gonzalez-sulser-lab-to-nwb-env`. Full interactive report: see conversation artifact ["GRIN2B Conversion Report"](https://claude.ai/code/artifact/5eedb72e-7bfa-46dd-8abc-0b2750ae3533).

- **37** animals total (xlsx + subjects yaml). **20** have a raw `.dat` on the share and were attempted (animal 424's on-disk file is orphaned from the xlsx — see `GRIN2B_424 xlsx error` above — so it's excluded from auto-discovery). **17/20 converted successfully.**
- **3 failures — missing single-baseline source CSV (data gap, not code):**
  - `GRIN2B_140`, `GRIN2B_378`: missing `..._BL1-pw_spectrum.csv` (BL2 copy exists).
  - `GRIN2B_375`: missing `..._BL1_Seizures.csv` entirely (BL1 sleep/PSD data exist).
- **1 failure — genuine code bug, fixed:** `GRIN2B_238` scored zero seizures in both BL1 and BL2 (header-only CSVs); `SeizureInterface` crashed trying to dtype-infer an empty `duration` VectorData column. Fixed in `interfaces/seizure_interface.py` — `add_to_nwbfile` now skips writing the `seizure_events` table when it ends up with zero rows, instead of crashing. Re-ran individually and GRIN2B_238 now converts cleanly (not yet committed).
- **17 animals blocked — no raw `.dat` on share:** 362–369, 371, 382, 383, 401, 402, 404, 424, 430, 433 (unchanged from prior gap analysis — lab needs to upload).
- Real per-subject conversion time is ~15–17 min (full multi-day recording, real writes); output files ~1.0–1.6 GB each.

## Midway Review Follow-up (2026-10-20/21)

Alfredo replied on 2026-10-20 after meeting with Katerina Hristova (first author). Changes made on branch `midway-meeting-updates`:

- **Excluded animals:** 13 animals added to `EXCLUDED_ANIMAL_IDS` (see File Inventory). Not converted or published.
- **GRIN2B_140, GRIN2B_378 (no BL1 power spectrum):** the lab's power-spectrum script crashes for these two and was never fixed; the lab does not consider a BL1 spectrum worth producing. Both animals now convert, with the BL2 spectrum only.
- **GRIN2B_375 (no BL1 seizure outputs):** 375 had no seizures in BL1, and the lab's MATLAB script sometimes writes no file in that case. BL1 `_Seizures.csv`, `_DGE_SWDs.csv` and `_Seiz_Totals.csv` are all absent, so `seizure_events`, `swd_epoch_counts` and `seizure_totals_by_zt` hold BL2 rows only. Sleep states and power spectra cover both baselines.
- **Root cause of the 140/375/378 failures:** the per-baseline interfaces paired CSVs with epochs-table rows by position and required one CSV per baseline, so a BL2-only stream either crashed or would have been aligned to BL1. They now take `file_paths` keyed by baseline label. Regression test: `tests/test_missing_baseline.py` (fails on `main`, passes here).
- **GRIN2B_424:** wired up via `_DAT_FILE_CORRECTIONS` (see File Inventory).
- **Verified (2026-10-21):** full conversions of 140, 375, 378 and 424 to `H:/gonzalez-nwbfiles` succeed (11–19 min each when run 4 in parallel, 1.2–1.3 GB each). NWB Inspector (`--config dandi`) reports only best-practice suggestions (placeholder descriptions on the `hemisphere`/`filtering` electrode columns, binary-valued integer columns, single-row table). Contents:
  - 140: BL2 power spectrum only; 1 seizure in BL1, none in BL2.
  - 375: the BL2 seizures CSV is header-only, so 375 has zero seizures in both baselines and no `seizure_events` table (same handling as 238). `seizure_totals_by_zt` and `swd_epoch_counts` hold BL2 only.
  - 378: BL2 power spectrum only; 7 seizures in BL1, 12 in BL2.
  - 424: all streams for both baselines; 1,121 seizures in BL1, 1,172 in BL2. `session_start_time` 2022-06-04 11:17 BST, 73.5 h recording.

Expected convertible set after these changes: the 17 previously converted animals plus 140, 375, 378 and 424 = 21, i.e. every non-excluded animal with a raw file.

## Animals 401, 402, 404 (2026-10-28)

The lab shared the raw `.dat` files for the three remaining non-excluded animals. Their filenames match the xlsx `File` column, so no correction is needed, and `convert_all_sessions` picks them up automatically. All CSV streams exist for both baselines.

| Animal | `.dat` file | Length | `session_start_time` | Seizures BL1 / BL2 |
|---|---|---|---|---|
| 401 | `TAINI_1048_A_Grin2B_401-2022_05_03-0000.dat` | 72.5 h | 2022-05-03 13:48 BST | 39 / 64 |
| 402 | `TAINI_1045_D_Grin2B_402-2022_05_03-0000.dat` | 72.5 h | 2022-05-03 13:48 BST | 1 / 1 |
| 404 | `TAINI_1048_A_GRIN2B_404-2022_04_28-0000.dat` | 93.9 h | 2022-04-28 13:23 BST | 1 / 0 |

- Full conversions to `H:/gonzalez-nwbfiles` succeeded with no code changes (15–17 min each, 3 in parallel; 1.1–1.5 GB). 404 has no BL2 seizures, so `seizure_events` holds BL1 rows only.
- Seizure counts reproduce the per-animal averages in `GRIN2B_CDKL5_Seizures_Overall.csv` (51.5, 1, 0.5).
- NWB Inspector (`--config dandi`) reports only the best-practice suggestions already seen on the other animals.
- The `32767` dropout rate within the baselines (401: 8.5% / 6.2%, 402: 1.1% / 1.0%, 404: 1.6% / 1.6%) is within the range of the other animals (see Open Questions).
- These files were written before the sex/genotype fix and have `sex="U"` and no genotype. 401, 402, 404, 132 and 424 need to be reconverted.

Convertible set: 24 animals, every non-excluded animal.

## Lab analysis code (2026-10-28)

The open questions on dropped samples, power-spectrum units, `Seiz_Totals` columns and `DGE_SWDs` codes were resolved from the lab's public code in [`AUTOMATIC-SLEEP-SCORER`](https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER) and checked against the GRIN2B files:

- **ADC scaling and dropped samples** — `MATLAB_FILES/parse_dat.m` (TainiTec's reader) converts codes to mV as `code / 4095 * 13.0` and defines `MISSED_PACKET_SYMBOL = 2^15-1` for radio packet loss, which it sets to 0. `Channels.csv` matches this scaling (code 2594 → 8.23492 mV in GRIN2B_129 BL1), so the gain is now 13000/4095 µV/code (it was /4096, 0.02% low). The R scorer (`rat.patchsgn` in `Sleep_autoscore_Beta.R`) interpolates over the zeroed gaps. We keep `32767` in the raw data and document it in the `ElectricalSeries` description. Rates within the baselines range from 0.5% to 20% of samples (highest in 238).
- **Power spectra** — `rat.spectr`, `rat.mtspec`, `rat.norm` and `rat.lsmth` in `R_SleepAutoscorer_FILES/sleep_score_library.R`: per-5-s-epoch multitaper spectrum (6 DPSS tapers) of one EEG channel in mV, `log10(power + 1e-6) / 2`, minus each frequency's 5th percentile across the window's epochs, smoothed across similar neighbouring epochs, then averaged per state (`rat.spctr_by_state`). Dimensionless, not µV²/Hz.
- **`Seiz_Totals.csv`** — `MATLAB_FILES/cepstral_analysis.m`: `ZT`/`SWDs` are hourly seizure counts (an event crossing an hour boundary counts in the hour it ends); `N_event`, `mean_dur` and `Day` are window totals in row 0 with rows 1–23 zero-padded. In all 47 GRIN2B files the totals equal the `_Seizures.csv` row count and mean `dur`, and `Day` equals the sum of `SWDs`, so only the hourly counts are written.
- **`DGE_SWDs.csv`** — same script: detected events are marked as 6 (else 4) on the 0.2-s spectrogram grid and every 25th point is kept, one per 5-s epoch. The sleep scorer (`correct.C`) turns 6 into state 4 = SWD. Written as boolean `is_swd`.
- **Single-baseline caveat** — not an issue: for all 24 animals, `N_events` and `Total_duration` in `GRIN2B_CDKL5_Seizures_Overall.csv` equal the mean of BL1 and BL2, so both baselines were used.

## Open Questions

- GRIN2B_424: which recording were its sleep/seizure outputs computed from (the 366 file named in the xlsx, or an earlier 424 session), and can it be shared?
- Scoring EEG channel: `Taini_CheckChoose.m` only offers `.dat` columns 4/13, which the lab's channel table labels M2_anterior R/L; the paper says S1. Is the channel table or the paper right?

## TODOs

Internal code/repo work, not blocked on the lab:

1. ~~Wire up the 07:00 BL1 start time~~ — **done.** `_parse_recording_date()` replaced by `_compute_session_start_time()` in `convert_session.py`: back-computes `session_start_time` (sample 0 of the `.dat` file) from the lab-confirmed anchor (BL1 sample offset = Zeitgeber time 07:00 the day after connection), so both the BL1 and BL2 NWB files for an animal share a correct absolute clock. Falls back to midnight only if an animal has no BL1 window at all.
2. ~~Reconcile `sleep_state_interface.py`~~ — **done.** State-code mapping now matches `state_power_spectrum_interface.py` (0=Wake, 1=NREM, 2=REM, 4=SWD); docstring, `_STATE_LABELS`, and table/column descriptions no longer say "unconfirmed"/`"Unknown"`.
3. ~~Clean up stale `Electrodes.channel_conversion` TODO~~ — **done.** Removed the dead `Electrodes`/`Device`/`ElectrodeGroup` blocks from `grin2b_general_metadata.yaml` (they were silently overriding the code-computed values via `dict_deep_update`); the ground-screw/reference/independence details they held were folded into `TainiRecordingInterface.get_metadata()`, which is now documented as the single source of truth for this metadata.
4. **Test coverage is minimal** (`tests/test_missing_baseline.py` only); CLI entry points (`argparse`) are commented out in favor of hardcoded local paths in `convert_session.py`/`convert_all_sessions.py`.
5. **SCN2A sub-package**: needs a screw-electrode channel-map variant of `TainiRecordingInterface` (no NeuroNexus grid) — design pending a call with Niamh.
6. **Generalize the pipeline to the other 4 SFARI lines** — only the metadata YAML files (general + subjects) should remain line-specific; interfaces/converter/conversion scripts should be parameterized rather than GRIN2B-hardcoded.
7. ~~Major refactor of the conversion pipeline design~~ — **done.** Now writes **one NWB file per subject** (`session_to_nwb()` in `convert_session.py`) containing the **full raw recording** via `TainiRecordingInterface` (BL slicing removed), with a new `BaselineEpochsInterface` adding **epochs**-table rows tagged `BL1`/`BL2`. `processing/behavior` and `processing/ecephys` hold both baselines' derived tables/series side by side (each per-baseline interface class instantiated once per available baseline, with a `baseline_label` suffixing the NWB object name):
   - `processing/behavior`: `seizure_events_baseline_window_{1,2}` (`TimeIntervals`), `sleep_states_baseline_window_{1,2}` (`TimeIntervals`), `swd_epoch_counts_baseline_window_{1,2}` (`TimeSeries`), `seizure_totals_by_zt_baseline_window_{1,2}` (`DynamicTable`).
   - `processing/ecephys`: `sleep_state_power_spectra_baseline_window_{1,2}` (`DynamicTable`), columns renamed from `s_0`/`s_1`/`s_2`/`s_4` to `Wake`/`NREM`/`REM`/`SWD`.
   - Verified end-to-end with a `stub_test=True` conversion of GRIN2B_129: correct `acquisition` series names, epochs table with correct BL1/BL2 start/stop times, all baseline-suffixed behavior/ecephys objects present, and renamed PSD columns. Also verified `Subject.subject_id = "GRIN2B-129"` (dash) and `session_id = "2021-03-26"` (recording date from the `.dat` filename) — see Sessions/Subjects.
   - `convert_all_sessions.py` and `README.md` updated to the new per-subject batching (`session_to_nwb`, one call per animal instead of per `(animal, baseline)` pair).
   - `notebooks/read_grin2b_nwb.ipynb` updated to read the new object names and derive BL1's time origin from the epochs table instead of `ElectricalSeries.starting_time` (which is now always 0).
8. **Move `Device.manufacturer` to a `DeviceModel`** — pynwb 4.0 deprecates `Device.manufacturer` (`DeprecationWarning` on every conversion: "use DeviceModel.manufacturer and link to that DeviceModel from this Device"). In `TainiRecordingInterface.get_metadata()`, move `manufacturer: "TainiTec"` (and the model, e.g. the TainiTec headstage / NeuroNexus H16-Rat EEG16 grid) into a top-level `metadata["DeviceModels"]` entry and link it from the `TainiTecWirelessEEG` device via `device_model_metadata_key`.
