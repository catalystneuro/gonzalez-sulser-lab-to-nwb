# Building a new conversion pipeline

This page outlines how to convert a new experiment to NWB, using this repository as an example, for instance another
SFARI rat line recorded with the same TainiTec system. It builds on [The conversion pipeline](conversion_pipeline.md),
which describes the parts of a conversion. It is a starting point; the linked documentation covers each step in
detail.

## 1. List the data and metadata

Write down, for one session:

- the files of each data stream (raw recordings, sleep scores, seizure tables, spectra) and how they are organized;
- how the streams are synchronized, and which clock is the reference;
- the metadata: subjects, devices, electrode positions, and where each value comes from (a sheet, the paper, the
  lab's analysis code).

[Data organization](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/data_organization.md) is this list for the
Hristova 2025 conversion.

## 2. Find NeuroConv interfaces for each stream

[NeuroConv](https://neuroconv.readthedocs.io/) reads many acquisition formats and writes them to NWB. Each format has
a data interface; the [conversion gallery](https://neuroconv.readthedocs.io/en/main/conversion_examples_gallery/index.html)
shows a short example for each one.

For data no interface reads, write a small interface. Here the TainiTec `.dat` files are read by
`TainiRecordingInterface`, which subclasses NeuroConv's `BaseRecordingExtractorInterface` around SpikeInterface's
`BinaryRecordingExtractor`, and the lab's CSV files by subclasses of `BaseDataInterface` (see
`src/gonzalez_sulser_lab_to_nwb/hristova_2025/interfaces/`).

For another line recorded with TainiTec and analysed with the same scorer, the interfaces can be reused as they are.
A line with another electrode layout (for example the screw electrodes of the SCN2A line) needs its own channel table
in `taini_recording_interface.py`.

## 3. Combine them in a converter

An `NWBConverter` combines the interfaces of a session and aligns their times (see
`src/gonzalez_sulser_lab_to_nwb/hristova_2025/nwbconverter.py`). Write a function that converts one session, then one
that finds and converts all sessions (`convert_session.py` and `convert_all_sessions.py` here).

## 4. Keep the metadata in YAML files

Put the metadata that does not come from the data files in YAML files, and read per-subject values (sex, genotype)
from the lab's own sheets, so that there is one source for each value (see
[Metadata](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/metadata.md)).

## 5. Check and share

- Convert one session with `stub_test=True` and open it with PyNWB or [Neurosift](https://neurosift.app).
- Run [NWB Inspector](https://nwbinspector.readthedocs.io/) on the files and fix its critical messages.
- Upload to [DANDI](https://docs.dandiarchive.org/user-guide-sharing/uploading-data/), trying the sandbox first.

## Starting a new repository

[cookiecutter-my-lab-to-nwb-template](https://github.com/catalystneuro/cookiecutter-my-lab-to-nwb-template) creates a
conversion repository with the same layout as this one. The
[nwb-convert](https://github.com/catalystneuro/claude-skills/tree/main/nwb-convert) skill for Claude Code walks
through the steps above in a conversation: it inspects the data, asks for the metadata, and writes a conversion
repository on NeuroConv and PyNWB with an example notebook. For conversions without code,
[NWB GUIDE](https://nwb-guide.readthedocs.io/) is a desktop application that walks through the same steps for the
formats NeuroConv supports.
