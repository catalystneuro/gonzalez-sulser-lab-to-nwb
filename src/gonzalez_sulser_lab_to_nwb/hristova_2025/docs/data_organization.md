# Data organization

The conversion reads the lab's data share (`H:/Gonzalez-Sulser-CN-data-share` on the CatalystNeuro machine). It covers
the GRIN2B rats of Hristova K, et al. "Absence seizures and sleep-wake abnormalities in a rat model of GRIN2B
neurodevelopmental disorder." Epilepsia. 2025;66:4996-5013.
[doi:10.1111/epi.18606](https://doi.org/10.1111/epi.18606).

## Folder layout

```text
Chronic EEG recordings/
  TAINI_<device>_<band>_<line>_<id>_<label>-<YYYY_MM_DD>-0000.dat   raw recording, one per animal (24 files)
  grin2b_eeg_channels.csv                                          channel layout of the .dat files
Light cycle timing metadata/
  Sample_start_end_GRIN2B.xlsx                                     BL1/BL2 sample windows of each animal
Subject metadata/
  GRIN2B_CDKL5_Seizures_Overall.csv                                sex and genotype of each animal
Sleep state classifications/
  GRIN2B_<id>/
    GRIN2B_<id>_BL{1,2}-dge_ok.csv                                 sleep scores, one per 5-s epoch
    GRIN2B_<id>_BL{1,2}-pw_spectrum.csv                            mean spectrum per brain state
    GRIN2B_<id>_BL{1,2}_Channels.csv                               scorer input (not converted)
    sbh_<id>_BL{1,2}.png, spec_<id>_BL{1,2}.png                    lab plots (not converted)
    seiz/
      GRIN2B_<id>_BL{1,2}_DGE_SWDs.csv                             SWD flag, one per 5-s epoch
      GRIN2B_<id>_BL{1,2}_Seiz_Totals.csv                          seizure counts per Zeitgeber hour
      GRIN2B_<id>_BL{1,2}_Seizures.csv                             copy of the file in Seizure timestamps/
Seizure timestamps/
  GRIN2B_<id>_BL{1,2}_Seizures.csv                                 seizure start, end and duration
Analysed_GRIN2B_424 1/                                             the lab's re-analysis of GRIN2B_424 (see below)
additional recordings/                                             16p11.2 recordings, not part of this conversion
```

The paper, its supplementary material and the lab's emails are also in the share root.

## Subjects

The lab files list 37 GRIN2B rats (Long-Evans, LE-Grin2bem1Mcwi heterozygous knockouts and wild-type littermates).
13 of them (362 to 369, 371, 382, 383, 430, 433) were excluded from the paper after a breeding mix-up, and the PI
asked that they not be published. They have no raw recording on the share and are listed in
`EXCLUDED_ANIMAL_IDS` in `convert_session.py`, which refuses to convert them.

The other 24 animals are converted, one NWB file each:

| Genotype | Male | Female |
|---|---|---|
| Het (Grin2b+/-) | 129, 130, 131, 227, 228, 229, 373, 424 | 137, 138, 139, 236, 237, 239, 241 |
| WT (Grin2b+/+) | 132, 375, 378 | 140, 238, 240, 401, 402, 404 |

The animals were 16 to 19 weeks old at recording. They were recorded in groups of up to four, in March and
July-August 2021 and April-June 2022.

## Recording protocol

Each animal carried a 16-channel TainiTec wireless transmitter connected to a NeuroNexus H16-Rat EEG16 skull-surface
grid (14 EEG electrodes) and two EMG wires in the trapezius muscles, and was recorded continuously for 72 to 96 hours
at 250.4 Hz. The rats were kept on a 12:12 light-dark cycle with lights on at 07:00 (Zeitgeber time 0, Edinburgh
time).

The lab analyzed two consecutive 24-h baseline windows of each recording. BL1 starts at lights-on the day after the
transmitter was connected, and BL2 follows it. Each window is 21,634,560 samples.

## Raw recordings

File names follow `TAINI_<device>_<band>_<line>_<id>_<label>-<YYYY_MM_DD>-0000.dat`:

- `device`: the transmitter ID (1044, 1045, 1047 or 1048).
- `band`: the receiver frequency band (A to D). Some files leave it out.
- `label`: the recording attempt (`Baseline`, `Baseline_Attempt2`, `Redo`, ...).
- the date: the day the recording started, in Edinburgh time. The time of day is not recorded.

The binary layout (16 int16 channels interleaved, no header) and the channel order are described in
[Data streams](data_streams.md#raw-signal). `grin2b_eeg_channels.csv` gives the label and hemisphere of each column.

## Lab sheets

`Sample_start_end_GRIN2B.xlsx` has one row per animal and baseline, with columns `Animal ID`, `Line`, `File`,
`Baseline` (`BL1` or `BL2`), `Start` and `End`. Start and End are 1-based inclusive sample numbers in the `.dat` file
(MATLAB indexing); the conversion subtracts 1. The conversion finds each animal's raw file from the `File` column.

`GRIN2B_CDKL5_Seizures_Overall.csv` has one row per animal of the GRIN2B and CDKL5 lines, with columns `ID`,
`Genotype` (`Het` or `Wt`), `Sex` (`Male` or `Female`), `Line` (`Grin2b` or `Cdkl5`), and the animal's mean seizure
count and duration over BL1 and BL2. The conversion reads the sex and genotype from it (see [Metadata](metadata.md)).

## Lab analysis code

The processed files were written by the lab's public code, which the conversion follows for scaling, sample indexing
and codes:

- [AUTOMATIC-SLEEP-SCORER](https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER): TainiTec's `.dat` reader
  (`parse_dat.m`), the channel picker (`Taini_CheckChoose.m`), the SWD tables (`cepstral_analysis.m`) and the R sleep
  scorer and spectra (`Sleep_autoscore_Beta.R`, `sleep_score_library.R`). Also used in Buller-Peralta et al., Brain
  Commun 2022 ([doi:10.1093/braincomms/fcac263](https://doi.org/10.1093/braincomms/fcac263)).
- [SWD-Automatic-Identification-2025](https://github.com/Gonzalez-Sulser-Team/SWD-Automatic-Identification-2025)
  ([zenodo:12700972](https://zenodo.org/records/12700972)): the SWD detector.

## Exceptions

- GRIN2B_424: the `File` column of its xlsx rows names animal 366's recording. The Start and End values are right for
  424's own file, `TAINI_1044_C_Grin2B_424_Redo-2022_06_04-0000.dat`, which `DAT_FILE_CORRECTIONS` in
  `convert_session.py` substitutes. The lab's first analysis of 424 had also read 366's recording; on 2026-11-11 the
  lab re-ran it on 424's own file (`Analysed_GRIN2B_424 1/`), and the new files replaced the old ones in the standard
  folders. The re-analysed `DGE_SWDs.csv` holds the full 0.2-s detection grid instead of one value per 5-s epoch, so
  424 is converted without the SWD epoch table (`SKIPPED_STREAMS`) until the lab sends the per-epoch file.
  `GRIN2B_CDKL5_Seizures_Overall.csv` still gives 424's seizure count from the first analysis.
- GRIN2B_140 and GRIN2B_378: no BL1 power spectrum (the lab's script fails for them). Their files have the BL2
  spectrum only.
- GRIN2B_375: no seizure in either window. The BL1 seizure files are missing and the BL2 `Seizures.csv` is empty, so
  the file has no seizure event table, and the SWD epochs and seizure totals cover BL2 only.
- GRIN2B_238: no seizure in either window, so its file has no seizure event table.
