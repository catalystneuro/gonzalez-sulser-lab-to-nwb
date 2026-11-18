# NWB file structure

Each file holds the full recording of one animal. Times are in seconds from the first sample of the recording
(`session_start_time`, Edinburgh time; see [Data streams](data_streams.md#timing)).

| Path in the file | Content |
|---|---|
| `acquisition/EEGElectricalSeries` | raw EEG, 14 channels, 250.4 Hz, the full recording (72 to 96 h) |
| `acquisition/EMGElectricalSeries` | raw EMG, 2 channels, same samples |
| `intervals/epochs` | one row per baseline window (BL1, BL2) |
| `processing/behavior/sleep_states` | sleep state of each 5-s epoch of each window |
| `processing/behavior/sleep_states/meanings_tables/sleep_state_meanings` | meaning and HED tags of each sleep state |
| `processing/behavior/seizure_events` | one row per spike-wave discharge |
| `processing/behavior/swd_epochs` | SWD flag of each 5-s epoch of each window |
| `processing/behavior/seizure_counts_by_zt_hour` | seizure count per Zeitgeber hour of each window |
| `processing/ecephys/sleep_state_power_spectra` | mean spectrum per brain state of each window |
| `general/extracellular_ephys/electrodes` | electrode table, 14 EEG and 2 EMG rows |
| `general/devices` | the TainiTec transmitter and its device model |
| `general/subject` | subject ID, sex, genotype, species, strain, age, description |
| `general/hed_schema` | HED schema versions of the HED tags (`HedLabMetaData`, ndx-hed) |
| `general/external_resources` | ontology (HERD) references of the experimenters, institution, species, strain, locations and sleep states |

A table is missing when the lab has no file for it: no `seizure_events` for an animal without seizures, no
`swd_epochs` for GRIN2B_424 (see [Data organization](data_organization.md#exceptions)).

## Raw series

The data are the raw TainiTec codes (int16). `conversion` and `offset` give volts: `volts = data * conversion +
offset`, with `conversion` = 13 mV / 4095 and `offset` = -6.5 mV. `get_data_in_units()` in PyNWB applies them. Samples
lost to radio packet loss hold the code 32767 on all channels; exclude them before analysis.

Both series point to rows of the electrode table: the EEG series to the 14 EEG rows, the EMG series to the 2 EMG
rows. The electrode table lists the EEG rows first, so a row number is not the column of the `.dat` file; use
`channel_name`.

## Electrode table

| Column | Content |
|---|---|
| `location` | the area: the full name with the paper's abbreviation, for example `primary motor cortex, anterior (M1-Ant)`, or `trapezius muscle` for the EMG electrodes |
| `channel_name` | the lab's label and the hemisphere, for example `M2_anterior_R`; the same names as the sleep-scoring channels of the epochs table |
| `hemisphere` | `R` or `L` |
| `x` | stereotaxic anterior-posterior position, in microns from bregma, positive posterior (NaN for EMG) |
| `z` | stereotaxic medial-lateral position, in microns from bregma, positive right (NaN for EMG) |
| `group`, `group_name` | `EEGArray` (H16-Rat EEG16 grid, cerebral cortex) or `EMGArray` (trapezius muscle) |
| `filtering` | `none` |

The axes follow NWB's convention for `x`, `y` and `z` (+x posterior, +y inferior, +z right, in microns). The depth
(`y`) of skull-surface electrodes is not defined, so the table has no `y` column.

## Epochs

`intervals/epochs` has one row per baseline window, tagged `baseline_window_1` or `baseline_window_2`, with the
columns `sleep_scoring_eeg_channel` and `sleep_scoring_emg_channel` (the `channel_name` of the channels the lab's
sleep scorer used). To get the raw data of a window, select the samples between its start and stop time.

## Processed tables

Every processed table has a `baseline_window` column with the tag of its window, so both windows are in one table.

- `sleep_states`: `start_time`, `stop_time`, `sleep_score` (0, 1, 2) and `sleep_state` (`Wake`, `NREM`, `REM`). Its
  meanings table `sleep_state_meanings` has one row per state: `value`, `meaning` and `HED` (for example
  `Asleep, sc:Sleep-stage-REM` for REM).
- `seizure_events`: `start_time`, `stop_time` and `duration`.
- `swd_epochs`: `start_time`, `stop_time` and `is_swd`.
- `seizure_counts_by_zt_hour`: `zeitgeber_hour` (0 to 23) and `number_of_seizure_events`. Not time-aligned.
- `sleep_state_power_spectra`: `frequency_hz` and one column per state (`Wake`, `NREM`, `REM`, `SWD`), dimensionless
  log10 amplitude (see [Data streams](data_streams.md#mean-spectrum-per-brain-state)). Not time-aligned.

The descriptions of the tables in the file say how the lab computed each one.

## Reading a file

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO("sub-GRIN2B-129_ses-2021-03-26_ecephys.nwb", "r") as io:
    nwbfile = io.read()
    epochs = nwbfile.epochs.to_dataframe()
    bl1 = epochs[epochs["tags"].apply(lambda tags: "baseline_window_1" in tags)].iloc[0]

    eeg = nwbfile.acquisition["EEGElectricalSeries"]
    first = int(round(bl1["start_time"] * eeg.rate))
    one_hour = eeg.data[first : first + int(3600 * eeg.rate)]  # first hour of BL1, raw codes; 32767 = packet loss
    volts = one_hour * eeg.conversion + eeg.offset

    sleep_states = nwbfile.processing["behavior"]["sleep_states"].to_dataframe()
    seizures = nwbfile.processing["behavior"]["seizure_events"].to_dataframe()

    # HED tags and ontology terms of the sleep states
    meanings = nwbfile.processing["behavior"]["sleep_states"].meanings_tables["sleep_state_meanings"].to_dataframe()
    hed_schema_version = nwbfile.lab_meta_data["hed_schema"].hed_schema_version
    references = nwbfile.external_resources.to_dataframe()  # key, entity_id, entity_uri, ...
```

PyNWB reads the HED columns from the schema cached in the file. Validating the tags against the HED schemas needs
`ndx-hed` (`pip install ndx-hed`; see the demo notebook).

Files on DANDI can be streamed without downloading them; `001888_demo/dandi_001888_tutorial.ipynb` shows how, and
[Neurosift](https://neurosift.app) opens them in the browser.
