# gonzalez-sulser-lab-to-nwb

NWB conversion scripts for the [Gonzalez-Sulser Lab](https://www.ed.ac.uk/centre-neuroregeneration/research/gonzalez-sulser-group) (University of Edinburgh),
using [NeuroConv](https://github.com/catalystneuro/neuroconv).

Converts chronic wireless EEG/EMG recordings from the TainiTec system (14 EEG + 2 EMG channels,
250.4 Hz) together with automated sleep-state classifications, seizure event timestamps, and
Zeitgeber-aligned seizure totals. Data are from rats carrying SFARI autism-risk mutations
(GRIN2B and other lines).

## Installation

```bash
conda activate gonzalez-sulser-lab-to-nwb-env
pip install -e ".[grin2b]"
```

## Usage

One NWB file is written per subject, containing the subject's full raw EEG/EMG recording plus an epochs table marking the BL1/BL2 baseline windows. Derived sleep/seizure/power-spectrum streams are written once per available baseline window into the same file.

### Single session

```python
from gonzalez_sulser_lab_to_nwb.grin2b.convert_session import session_to_nwb

session_to_nwb(
    data_dir="H:/Gonzalez-Sulser-CN-data-share",
    output_dir="/path/to/nwb_output",
    animal_id=129,
    stub_test=False,
)
```

### All sessions

```python
from gonzalez_sulser_lab_to_nwb.grin2b.convert_all_sessions import dataset_to_nwb

dataset_to_nwb(
    data_dir="H:/Gonzalez-Sulser-CN-data-share",
    output_dir="/path/to/nwb_output",
    max_workers=4,
)
```

### Stub test (fast pipeline check)

```bash
python -m gonzalez_sulser_lab_to_nwb.grin2b.convert_session \
    --data-dir "H:/Gonzalez-Sulser-CN-data-share" \
    --output-dir "/tmp/nwb_stub" \
    --animal-id 129 \
    --stub-test
```

## Data streams converted

| Stream | Source | NWB location |
|---|---|---|
| Raw EEG/EMG (full recording) | TainiTec `.dat` (int16, 250.4 Hz) | `acquisition/EEGElectricalSeries`, `acquisition/EMGElectricalSeries` |
| BL1/BL2 baseline windows | `Sample_start_end_GRIN2B.xlsx` | `epochs` (tagged `BL1`/`BL2`) |
| Sleep states | `*-dge_ok.csv` (5-s epochs) | `processing/behavior/sleep_states_baseline_window_{1,2}` |
| Seizure events | `*_Seizures.csv` | `processing/behavior/seizure_events_baseline_window_{1,2}` |
| SWD epoch counts | `*_DGE_SWDs.csv` | `processing/behavior/swd_epoch_counts_baseline_window_{1,2}` |
| Seizure ZT totals | `*_Seiz_Totals.csv` | `processing/behavior/seizure_totals_by_zt_baseline_window_{1,2}` |
| State power spectra | `*-pw_spectrum.csv` | `processing/ecephys/sleep_state_power_spectra_baseline_window_{1,2}` |

## Project tracking

See [project_track.md](project_track.md) for conversion progress across all SFARI lines.
See [conversion_notes.md](conversion_notes.md) for data-inspection findings and open questions.
