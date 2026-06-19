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

### Single session

```python
from gonzalez_sulser_lab_to_nwb.grin2b.convert_session import session_to_nwb

session_to_nwb(
    data_dir="H:/Gonzalez-Sulser-CN-data-share",
    output_dir="/path/to/nwb_output",
    animal_id=129,
    baseline="BL1",
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
    --baseline BL1 \
    --stub-test
```

## Data streams converted

| Stream | Source | NWB location |
|---|---|---|
| Raw EEG/EMG | TainiTec `.dat` (int16, 250.4 Hz) | `acquisition/ElectricalSeries_BL{N}` |
| Sleep states | `*-dge_ok.csv` (5-s epochs) | `processing/behavior/sleep_states` |
| Seizure events | `*_Seizures.csv` | `processing/behavior/seizure_events` |
| SWD epoch counts | `*_DGE_SWDs.csv` | `processing/behavior/swd_epoch_counts` |
| Seizure ZT totals | `*_Seiz_Totals.csv` | `processing/behavior/seizure_totals_by_zt` |
| State power spectra | `*-pw_spectrum.csv` | `processing/ecephys/sleep_state_power_spectra` |

## Project tracking

See [project_track.md](project_track.md) for conversion progress across all SFARI lines.
See [conversion_notes.md](conversion_notes.md) for data-inspection findings and open questions.
