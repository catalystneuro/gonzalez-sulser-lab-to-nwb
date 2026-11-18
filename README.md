# gonzalez-sulser-lab-to-nwb

Conversion of the Gonzalez-Sulser lab's chronic EEG and EMG recordings to the
[Neurodata Without Borders](https://nwb-overview.readthedocs.io/) (NWB) format, built on
[NeuroConv](https://neuroconv.readthedocs.io/).

The `hristova_2025` conversion covers the GRIN2B rats of Hristova et al. (2025), "Absence seizures and sleep-wake
abnormalities in a rat model of GRIN2B neurodevelopmental disorder" (Epilepsia,
[doi:10.1111/epi.18606](https://doi.org/10.1111/epi.18606)). Grin2b heterozygous knockout rats and wild-type
littermates were recorded for 72 to 96 hours with a TainiTec wireless system (14 EEG and 2 EMG channels, 250.4 Hz).
Each NWB file holds one animal: the full raw EEG and EMG, the two 24-h baseline windows the lab analyzed, and the
lab's sleep states, seizure events, SWD flags, hourly seizure counts and spectra per brain state. The files are shared
in [DANDI:001888](https://dandiarchive.org/dandiset/001888).

## Installation

Install [git](https://github.com/git-guides/install-git) and [conda](https://docs.conda.io/en/latest/miniconda.html),
then, from a terminal:

```bash
git clone https://github.com/catalystneuro/gonzalez-sulser-lab-to-nwb
cd gonzalez-sulser-lab-to-nwb
conda env create --file make_env.yml
conda activate gonzalez-sulser-lab-to-nwb-env
```

This creates a conda environment with the package installed in editable mode, so that changes to the code and
metadata files apply without installing again. Without conda, use Python 3.11 or 3.12 and run
`pip install --editable ".[test]"` in the cloned folder.

## Quick start

```bash
hristova-2025 convert "<data folder>" "<output folder>"
hristova-2025 stage "<output folder>" --dandi-instance dandi-sandbox
hristova-2025 upload "<output folder>" --dandi-instance dandi-sandbox
```

`convert` writes one NWB file per animal to the output folder and inspects it with NWB Inspector; `stage` validates
the files and compares them with the draft of the dandiset; `upload` sends them. See
[Converting sessions](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/converting_sessions.md).

## Documentation

The conversion pipeline in general, in [docs/](docs/):

- [The conversion pipeline](docs/conversion_pipeline.md): NWB, NeuroConv, the parts of a conversion and the steps from
  recordings to DANDI.
- [Building a new conversion pipeline](docs/new_conversion_pipeline.md): converting another experiment to NWB.

The Hristova 2025 conversion, in [hristova_2025/docs/](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/):

- [Data organization](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/data_organization.md): the data share layout, subjects, the recording protocol and the lab files.
- [Converting sessions](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/converting_sessions.md): converting sessions, and the output files.
- [Data streams](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/data_streams.md): the raw signals and the lab's processed streams, and how they are aligned.
- [Metadata](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/metadata.md): editing the metadata files, subject metadata, ontology terms.
- [NWB file structure](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/nwb_file_structure.md): what is stored where, and how to read a file.
- [Spyglass ingestion](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/spyglass_ingestion.md): ingesting the files into Spyglass.
- [DANDI staging](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/dandi_staging.md): validating and uploading the files.
- [Troubleshooting](src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/troubleshooting.md): conversion errors.

The notebook in `src/gonzalez_sulser_lab_to_nwb/hristova_2025/001888_demo/` streams and reads the files on DANDI.

## Repository layout

```text
src/gonzalez_sulser_lab_to_nwb/hristova_2025/
├── cli.py                    hristova-2025 command
├── convert_session.py        conversion of one subject
├── convert_all_sessions.py   conversion of all subjects
├── nwbconverter.py           NWBConverter of the dataset
├── interfaces/               data interfaces (TainiTec recording, baseline windows, lab's processed files)
├── inspection.py             NWB Inspector reports and conversion summary
├── upload_to_DANDI.py        validation and upload to DANDI
├── metadata/                 metadata files
├── docs/                     documentation of this conversion
└── 001888_demo/              notebook that reads the files on DANDI
tests/                        tests of the lab's conventions, missing windows, subject metadata and ontology terms
```

## Citation

If you use these files, please cite the paper above, and [NeuroConv](https://github.com/catalystneuro/neuroconv) and
[NWB](https://www.nwb.org/) for the conversion.
