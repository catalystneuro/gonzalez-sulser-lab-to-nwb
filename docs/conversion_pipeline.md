# The conversion pipeline

This page explains how a conversion in this repository turns a lab's recordings into NWB files and shares them on
DANDI. Each conversion project has its own documentation next to its code; for the GRIN2B recordings of Hristova et
al. (2025), see [hristova_2025/docs](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/).

## NWB and NeuroConv

[NWB](https://nwb-overview.readthedocs.io/) (Neurodata Without Borders) is a standard file format for neurophysiology
data. One NWB file holds the data of a session together with its metadata: subject, devices, electrodes, and the
meaning and units of each signal. Files that follow the standard can be read by the same tools and shared on
[DANDI](https://dandiarchive.org), the archive for NWB data.

The conversions are built on [NeuroConv](https://neuroconv.readthedocs.io/), which reads acquisition formats and
writes them to NWB, and on [PyNWB](https://pynwb.readthedocs.io/), the Python API of NWB.

## Parts of a conversion

A conversion project is a folder under `src/gonzalez_sulser_lab_to_nwb/`, named after the paper it converts:

| Part | Role |
|---|---|
| data interfaces (`interfaces/`) | Each reads one data stream (for example the raw EEG of a TainiTec `.dat` file, or the lab's sleep scores) and adds it to an NWB file. NeuroConv provides interfaces for common formats; the project adds its own for lab-specific files. |
| converter (`nwbconverter.py`) | Combines the interfaces of a session into one file and puts their times on one clock. |
| metadata files (`metadata/`) | YAML files with the metadata that is not in the data files, such as the experimenters, the subject description and the ontology terms. |
| session conversion (`convert_session.py`) | Finds the files of one session, builds its metadata and runs the converter. |
| batch conversion (`convert_all_sessions.py`) | Lists every session of the data folder and converts them. |
| inspection and staging (`inspection.py`, `upload_to_DANDI.py`) | NWB Inspector reports after converting, and the upload to DANDI. |
| command line (`cli.py`) | One command per step. |
| `docs/` and `001888_demo/` | How to run the conversion, and a notebook that reads the files on DANDI. |

## From recordings to DANDI

A conversion runs in these steps:

1. Convert: write one NWB file per session. Sessions already converted are skipped, so new recordings can be added
   and converted without converting the others again.
2. Inspect: run [NWB Inspector](https://nwbinspector.readthedocs.io/) on each file, which checks it against the
   standard and its best practices.
3. Review: look at the files and the inspection summary, and fix the metadata or the code where needed.
4. Stage: validate the files and the dandiset metadata as DANDI does, and compare them with the files already on the
   draft of the dandiset.
5. Upload: send the files to the draft of the dandiset. Publishing a version freezes the draft and gives it a DOI.

## Keeping a conversion correct

- Metadata lives in YAML files and in the lab's own sheets, so that it can be corrected and reviewed without changing
  code.
- The tests in `tests/` check the conventions taken from the lab's analysis code (scaling, sample indexing, codes),
  so that a change to the code that breaks them fails.
- NWB Inspector runs after each conversion, and DANDI's validation before each upload.
- Ontology terms (species, strain, brain regions, experimenters, institution) are written into the files, so that the
  values can be found by their standard identifiers.

To convert a new experiment, see [Building a new conversion pipeline](new_conversion_pipeline.md).
