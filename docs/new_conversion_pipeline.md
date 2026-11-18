# Building a new conversion pipeline

This page explains how to extend the conversion in this repository and how to convert a new experiment to NWB. It
builds on [The conversion pipeline](conversion_pipeline.md), which describes the parts of a conversion.

## Extending the Hristova 2025 conversion

Start from [Converting sessions](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/converting_sessions.md) and the
code in `src/gonzalez_sulser_lab_to_nwb/hristova_2025/`.

### More animals of the same line

Put their files in the data share and add their rows to the lab sheets; no code change is needed. See
[Adding animals](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/converting_sessions.md#adding-animals).

### A new processed stream

A lab file with one file per baseline window (for example a new table from the sleep scorer) needs:

1. An interface in `interfaces/` that subclasses `BaseBaselineStreamInterface` (in `baseline_epochs_interface.py`).
   Set `table_name`, `table_description`, `column_descriptions` (one per column), `table_class` (`TimeIntervals` for
   a table with `start_time` and `stop_time`, `DynamicTable` otherwise) and `module_name` (`behavior` or `ecephys`),
   and write `read_file`, which reads one file into a DataFrame with times in seconds from the start of its window.
   The base class aligns the times to the recording, adds the `baseline_window` column and writes one table for both
   windows. `SeizureInterface` in `seizure_interface.py` is a short example.
2. An entry in `data_interface_classes` of `nwbconverter.py`, after `BaselineEpochs`.
3. Its file pattern in `STREAM_FILES` of `convert_session.py`, under the same name as in the converter.
4. A test in `tests/` with a small generated file, as in `tests/test_lab_pipeline_conventions.py`.

A stream that is not split by window (one file for the whole recording) subclasses NeuroConv's `BaseDataInterface`
directly and writes its times in seconds from `session_start_time`.

### Another SFARI line recorded with TainiTec

The lab recorded other lines (CDKL5, 16p11.2, SYNGAP, NLGN3, SCN2A) with the same TainiTec system and analyzed them
with the same scorer. A line published in its own paper gets its own conversion folder, named after the paper, for
example `src/gonzalez_sulser_lab_to_nwb/<author>_<year>/`:

1. Copy `convert_session.py`, `convert_all_sessions.py`, `nwbconverter.py`, `cli.py`, `metadata/` and `docs/` from
   `hristova_2025/`, and import the interfaces, `inspection.py` and `upload_to_DANDI.py` from `hristova_2025` instead
   of copying them.
2. In `convert_session.py`, set the line's files and settings: `WINDOWS_FILE` (its `Sample_start_end_<line>.xlsx`),
   `LINE` (its value in the `Line` column of the subject sheet), `GENOTYPE` (the line's allele name for `Het`),
   `get_subject_key` (the prefix of its file names, for example `CDKL5_<id>`), `STREAM_FILES`,
   `EXCLUDED_ANIMAL_IDS`, `DAT_FILE_CORRECTIONS` and `SKIPPED_STREAMS`.
3. In `metadata/general_metadata.yaml`, update the experiment description, keywords, experimenters, related
   publication, the `Subject` block (description and strain) and their ontology terms. Fill
   `metadata/sleep_scoring_channels.yaml` for the line's animals.
4. If the electrodes differ (the SCN2A rats have screw electrodes on an interface board instead of the NeuroNexus
   grid), subclass `TainiRecordingInterface` and override `channels`, `locations`, `coordinates_mm`, `electrode_groups`
   and `device_description`, and add each new location to `anatomical_structures` in the metadata; use the subclass
   in the converter.
5. In the copied `cli.py`, import the shared modules from `gonzalez_sulser_lab_to_nwb.hristova_2025`, set the
   default dandiset ID of the line (`stage --dandiset-id` also takes it), and add the command to
   `[project.scripts]` in `pyproject.toml`. An unpublished line goes to an embargoed dandiset.
6. Convert one animal with `--stub-test`, check the file, then convert the line.

## Converting a new experiment

### 1. List the data and metadata

Write down, for one session:

- the files of each data stream (raw recordings, scores, event tables, spectra) and how they are organized;
- how the streams are synchronized, and which clock is the reference;
- the metadata: subjects, devices, electrode positions, and where each value comes from (a sheet, the paper, the
  lab's analysis code).

[Data organization](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/data_organization.md) is this list for the
Hristova 2025 conversion.

### 2. Find NeuroConv interfaces for each stream

[NeuroConv](https://neuroconv.readthedocs.io/) reads many acquisition formats and writes them to NWB. Each format has
a data interface; the [conversion gallery](https://neuroconv.readthedocs.io/en/main/conversion_examples_gallery/index.html)
shows a short example for each one.

For data no interface reads, write a small interface. Here the TainiTec `.dat` files are read by
`TainiRecordingInterface`, which subclasses NeuroConv's `BaseRecordingExtractorInterface` around SpikeInterface's
`BinaryRecordingExtractor`, and the lab's CSV files by subclasses of `BaseDataInterface`.

### 3. Combine them in a converter

An `NWBConverter` combines the interfaces of a session and aligns their times (see `nwbconverter.py`). Write a
function that converts one session, then one that finds and converts all sessions (`convert_session.py` and
`convert_all_sessions.py` here).

### 4. Keep the metadata in YAML files

Put the metadata that does not come from the data files in YAML files, and read per-subject values (sex, genotype)
from the lab's own sheets, so that there is one source for each value (see
[Metadata](../src/gonzalez_sulser_lab_to_nwb/hristova_2025/docs/metadata.md)). Add ontology terms for species, strain,
locations, experimenters and institution, and HED tags for categorical labels such as sleep states.

### 5. Check and share

- Convert one session with `stub_test=True` and open it with PyNWB or [Neurosift](https://neurosift.app).
- Run [NWB Inspector](https://nwbinspector.readthedocs.io/) on the files and fix its critical messages.
- Upload to [DANDI](https://docs.dandiarchive.org/user-guide-sharing/uploading-data/), trying the sandbox first.
- Write a notebook that reads the files from DANDI, as `hristova_2025/001888_demo/`.

### Starting a new repository

[cookiecutter-my-lab-to-nwb-template](https://github.com/catalystneuro/cookiecutter-my-lab-to-nwb-template) creates a
conversion repository with the same layout as this one. The
[nwb-convert](https://github.com/catalystneuro/claude-skills/tree/main/nwb-convert) skill for Claude Code walks
through the steps above in a conversation: it inspects the data, asks for the metadata, and writes a conversion
repository on NeuroConv and PyNWB with an example notebook. For conversions without code,
[NWB GUIDE](https://nwb-guide.readthedocs.io/) is a desktop application that walks through the same steps for the
formats NeuroConv supports.
