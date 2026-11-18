# Metadata

The metadata of the NWB files that is not in the data files is kept in YAML files in
`src/gonzalez_sulser_lab_to_nwb/hristova_2025/metadata/`, and the per-subject values in the lab's subject sheet, so
that they can be corrected without changing code. After an edit, convert the affected subjects again with
`--overwrite` (see [Converting sessions](converting_sessions.md)).

## Files

| File | Content |
|---|---|
| `metadata/general_metadata.yaml` | experiment description, institution, lab, experimenters, keywords, related publication; the subject fields shared by every animal (species, strain, age, description); HED tags of the sleep states; ontology terms |
| `metadata/sleep_scoring_channels.yaml` | the EEG and EMG channel the lab's sleep scorer used for each animal and window |
| `Subject metadata/GRIN2B_CDKL5_Seizures_Overall.csv` (data share) | sex and genotype of each animal |

Device, electrode group, electrode and series metadata (ADC scaling, channel layout, coordinates, the grid and ground
screw) are set in `interfaces/taini_recording_interface.py`, since they follow from the `.dat` format. Do not add them
to the YAML: its values replace the interface's.

Settings about which data are converted are constants at the top of `convert_session.py`:

- `EXCLUDED_ANIMAL_IDS`: animals that are never converted.
- `DAT_FILE_CORRECTIONS`: raw file names that replace the xlsx `File` column.
- `SKIPPED_STREAMS`: streams left out for an animal.
- `STREAM_FILES`: the path of each processed stream's file in the data share.

## How a session's metadata is built

For each subject, `session_to_nwb` merges, in this order:

1. The metadata of the interfaces (devices, electrodes, series).
2. `general_metadata.yaml`.
3. Values set by the code:
   - `session_id`: the recording date of the `.dat` file name.
   - `session_start_time`: BL1's lights-on minus BL1's offset (see [Data streams](data_streams.md#timing)).
   - `session_description`: the subject and its baseline windows.
   - `Subject.subject_id`, `sex` and `genotype`, from the subject sheet.

## Subject metadata

`get_subject_metadata` reads the subject sheet, keeps the rows with `Line` equal to `Grin2b`, and finds the animal by
`ID`. It fails if the animal is missing or listed twice. The values are mapped as:

| Sheet | NWB `Subject` |
|---|---|
| `ID` 129 | `subject_id` `GRIN2B-129` |
| `Sex` `Male` / `Female` | `sex` `M` / `F` |
| `Genotype` `Het` | `genotype` `LE-Grin2bem1Mcwi` (the RGD name of the line, RRID:RGD_14394515) |
| `Genotype` `Wt` | `genotype` `WT` |

`strain` is the background strain, `Long-Evans`, for every animal. `age` is `P16W/P19W`: the animals were 16 to 19
weeks old at recording, and dates of birth are not available.

## Ontology terms

The `ExternalResources` block of `general_metadata.yaml` maps values of the files to ontology terms, which NeuroConv
writes into each NWB file as HERD references (the `herd_references` column of the conversion summary counts them).
Each map is keyed by the exact value it annotates:

- `experimenter`: the ORCID iD of each experimenter, from the Crossref record of the paper. McLaughlin and
  Buller-Peralta have none there and are left out.
- `institution`: the ROR ID of the University of Edinburgh.
- `species`: NCBI Taxonomy.
- `strain`: the RRID of Crl:LE (Charles River), the Long-Evans background the line was made in.
- `anatomical_structures`: UBERON terms for the electrode locations (for example
  `primary motor cortex, anterior (M1-Ant)`) and the electrode group locations (`cerebral cortex`,
  `trapezius muscle`). UBERON has no rat-specific subdivisions of these areas, so each maps to its general area.

NeuroConv has no map for `genotype`, so the genotype carries no reference; the RRID of the line is in the subject
description.

The sleep states have their own ontology terms, in the `SleepStates` block (see below).

A new location string or experimenter needs an entry with exactly the same spelling; the `herd_references` column of
the conversion summary shows whether the terms reached the files.

## HED tags of the sleep states

The `SleepStates` block of `general_metadata.yaml` describes each value of the `sleep_state` column:

```yaml
SleepStates:
  hed_schema_version: '["8.4.0", "sc:score_2.1.0"]'
  description: Meaning of each sleep state label. ...
  states:
    Wake: { meaning: Wakefulness., HED: Awake, ontology_term: { id: "NBO:0000066", uri: ... } }
    NREM: { meaning: Non-rapid eye movement (NREM) sleep., HED: Asleep, ontology_term: { id: "NBO:0000161", ... } }
    REM: { meaning: Rapid eye movement (REM) sleep., HED: "Asleep, sc:Sleep-stage-REM", ontology_term: { id: "NBO:0000159", ... } }
```

`SleepStateInterface` writes it as a `MeaningsTable` on the `sleep_state` column, with the schema versions in the
file's `HedLabMetaData` ([ndx-hed](https://github.com/hed-standard/ndx-hed)), and links each state to its
[Neuro Behavior Ontology](https://www.ebi.ac.uk/ols4/ontologies/nbo) term in the file's HERD. The tags use the HED
standard schema and the SCORE library (`sc:`), as in the
[proposed NWB best practice for sleep states](https://github.com/NeurodataWithoutBorders/nwbinspector/pull/775). The
conversion validates the tags against the schema and fails on an invalid tag. The block must define exactly the
states Wake, NREM and REM.

## Sleep-scoring channels

`sleep_scoring_channels.yaml` maps each subject to its channels per window, as electrode-table channel names:

```yaml
GRIN2B_129: { BL1: [M2_anterior_R, EMG_R], BL2: [M2_anterior_R, EMG_R] }
```

The channels were found by matching each window's `*_Channels.csv` against the raw channels, and agree with the
`eeg`/`emg` columns of the lab's `rat_day_index_GRIN2B.csv`. A subject not listed gets no channel columns in its
epochs table.
