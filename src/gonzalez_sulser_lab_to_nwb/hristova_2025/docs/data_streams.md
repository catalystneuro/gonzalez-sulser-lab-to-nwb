# Data streams

Each NWB file holds one animal's full raw recording and the lab's processed streams of its baseline windows. This
page describes each stream, the lab file it comes from and how it is aligned. Where each one is stored is in
[NWB file structure](nwb_file_structure.md).

| Stream | Lab file | Interface |
|---|---|---|
| raw EEG and EMG | `.dat` | `TainiRecordingInterface` |
| baseline windows | `Sample_start_end_GRIN2B.xlsx` | `BaselineEpochsInterface` |
| sleep states | `*-dge_ok.csv` | `SleepStateInterface` |
| seizure events | `*_Seizures.csv` | `SeizureInterface` |
| SWD epoch flags | `*_DGE_SWDs.csv` | `SwdEpochsInterface` |
| seizure counts per Zeitgeber hour | `*_Seiz_Totals.csv` | `SeizureTotalsInterface` |
| mean spectrum per brain state | `*-pw_spectrum.csv` | `StatePowerSpectrumInterface` |

## Timing

Every stream comes from one `.dat` file, so the streams share one clock and no synchronization signal is needed.
Times in the NWB file are seconds from the first `.dat` sample (`session_start_time`):

- raw signal: sample `i` is at `i / 250.4`.
- baseline window: from `start / 250.4` to `(end + 1) / 250.4`, with `start` and `end` the 0-based sample indices of
  the xlsx.
- processed streams: the lab's times count from the start of their window, so the window's start time is added.

The file names give the recording date but not the time of day. BL1 starts at lights-on (07:00 Edinburgh time) the
day after the recording date, so `session_start_time` is that time minus BL1's start sample divided by 250.4. The
subtraction is done in UTC, so it stays right across a daylight-saving change.

## Raw signal

The `.dat` files have no header: 16 channels interleaved sample by sample, int16 little-endian, at 250.4 Hz
(21,634,560 samples are exactly 24 h). The values are unsigned 12-bit ADC codes, 0 to 4095, over a 13 mV
peak-to-peak range. As in TainiTec's `parse_dat.m`, one code is 13000 / 4095 = 3.1746 uV; the conversion also
subtracts 6.5 mV so that code 2047.5 is 0 V (`parse_dat.m` returns 0 to 13 mV). The lab's `*_Channels.csv` files
match this scaling.

The raw codes are written unchanged, with the gain and offset in the series' `conversion` and `offset`. Two kinds of
values are outside 0 to 4095:

- 32767: a sample lost to radio packet loss, written by TainiTec on all 16 channels at once. Between 0.5% and 20% of
  the samples of a window, depending on the animal. The lab's pipeline sets them to 0 and interpolates over them;
  exclude them before analysis.
- fewer than 0.02% of samples just above 4095 at saturation, and occasional isolated corrupted values.

Channel order of the `.dat` columns (from `grin2b_eeg_channels.csv`), with AP/ML coordinates in mm from bregma:

| Column | Label | Hemisphere | AP | ML |
|---|---|---|---|---|
| 0, 15 | S1_Tr | R, L | -3.0 | 2.8 |
| 1, 14 | EMG | R, L | | |
| 2, 13 | M2_Fra | R, L | 3.6 | 1.2 |
| 3, 12 | M2_anterior | R, L | 1.5 | 1.2 |
| 4, 11 | M1_anterior | R, L | 1.5 | 2.8 |
| 5, 9 | V2_ML | R, L | -5.0 | 3.0 |
| 6, 8 | V1_M | R, L | -7.0 | 3.0 |
| 7, 10 | S1Hl_S1Fl | R, L | -1.0 | 2.8 |

The 14 EEG channels and the 2 EMG channels are written as two series of the same electrode table.

## Baseline windows

One epochs-table row per window, tagged `baseline_window_1` (BL1) or `baseline_window_2` (BL2). The row also gives
the EEG and EMG channel the lab's sleep scorer used for the window, from `metadata/sleep_scoring_channels.yaml`. These
were found by matching each window's `*_Channels.csv` against the 16 raw channels; every window matched one M2
anterior EEG channel and one EMG channel. The paper's supplementary methods name an S1 channel; the lab confirmed this
is an error in the paper.

## Sleep states

`*-dge_ok.csv` has one column, `sleep.score`, with one value per 5-s epoch (17,280 per window): 0 = Wake, 1 = NREM,
2 = REM. These are the scores before the scorer relabels SWD epochs as state 4; the relabelled file is not in the
share. The SWD flags are in the SWD epochs table.

## Seizure events

`*_Seizures.csv` (tab-separated) has one row per spike-wave discharge, with `sec_start`, `sec_end` and `dur` in
seconds from the start of the window. Written as intervals with a `duration` column.

## SWD epoch flags

`*_DGE_SWDs.csv` has one column, `DGE_SWDs`, with one value per 5-s epoch: 6 = SWD, 4 = no SWD. `cepstral_analysis.m`
marks the detected events on the 0.2-s grid of the detection spectrogram and keeps every 25th point, so an epoch is
flagged when the point near its start falls inside an SWD. Written as a boolean `is_swd` per epoch.

## Seizure counts per Zeitgeber hour

`*_Seiz_Totals.csv` has 24 rows with columns `N_event`, `mean_dur`, `ZT`, `SWDs` and `Day`. `ZT` and `SWDs` are the
seizure count of each hour of the window; an event that crosses an hour boundary counts in the hour in which it ends.
`N_event`, `mean_dur` and `Day` are window totals in the first row, with the other rows zero. In every GRIN2B file the
totals equal the count and mean duration of the window's `Seizures.csv`, so only the hourly counts are written.

## Mean spectrum per brain state

`*-pw_spectrum.csv` has columns `hz`, `s_0`, `s_1`, `s_2` and `s_4` (Wake, NREM, REM, SWD), 628 rows from 0 to
125.2 Hz in 0.2 Hz steps, and a spurious first row of labels that is skipped. From `sleep_score_library.R`: the
multitaper spectrum (6 tapers) of each 5-s epoch of one EEG channel in mV, as log10(power + 1e-6) / 2, minus each
frequency's 5th percentile over the window, smoothed with similar neighbouring epochs, then averaged over the epochs
of each state. The values are dimensionless log10 amplitudes, not a power spectral density. These are standard
outputs of the lab's scorer; the spectra in the paper were computed another way.

## Not converted

- `*_Channels.csv`: the two scorer channels of each window in mV, with packet-loss samples set to 0. The same data are
  in the raw series.
- `sbh_*.png` and `spec_*.png`: the lab's hypnogram and spectrogram plots.
- `seiz/*_Seizures.csv`: identical to the files in `Seizure timestamps/`.
