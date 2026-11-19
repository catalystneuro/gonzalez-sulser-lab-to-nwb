# Spyglass ingestion notes

Tracks the Spyglass pull requests and issues that ingesting the DANDI:001888 files depends on, while they are under
development, and the open questions about what else to ingest. Remove the tracking part once the PRs are all merged
into LorenFrankLab/spyglass and the environment installs a Spyglass release. How to set up Spyglass, ingest the files
and run the notebooks is in [docs/spyglass_ingestion.md](../docs/spyglass_ingestion.md). The overview for the
Spyglass team is the tracking issue on this repository (to be opened).

Check the live state of each link before acting on it.

## Current build

`spyglass-env.yaml` and `bootstrap_wsl.sh` install the tag `gonzalez-sulser-example-v1` of
https://github.com/catalystneuro/spyglass (`268541a5`), the head of branch `gonzalez-sulser-integration`. It is
upstream `master` (`da36473c`) with these branches merged, in order:

1. `feature/eeg-ingestion` of LorenFrankLab/spyglass (`aac13e01`, #1638);
2. `herd-external-resources` of the fork (`a83f0903`, #1722);
3. `hed-annotations` of the fork (`8d025e3f`, #1723);
4. `sleep-scoring` of the fork (`6ae9e586`, #1726).

The merge conflicts were all in the lists of tables (`__init__.py`, `populate_all_common.py`, `CHANGELOG.md`,
`docs/src/ForDevelopers/UsingNWB.md`) and were resolved by keeping both sides.

Checked on 2026-11-19 against a freshly reset database, with an env built by `bootstrap_wsl.sh` from the tag: all 24
files ingest with no `InsertError` rows in about 100 s, and the three notebooks run.

Installed from the tag, Spyglass reports its version as `1`: setuptools-scm reads the tag name's trailing `v1` as the
version. Nothing in the ingestion depends on it.

## Spyglass PRs

| Data | Branch | Upstream PR |
| --- | --- | --- |
| EEG/EMG series (`ImportedEEG`, `.Electrode`) | `feature/eeg-ingestion` (edeno) | https://github.com/LorenFrankLab/spyglass/pull/1638, open; follows https://github.com/LorenFrankLab/spyglass/issues/1634 |
| HERD external resources (`OntologyTerm`, `ExternalResources`) | `herd-external-resources` (fork) | https://github.com/LorenFrankLab/spyglass/pull/1722, draft |
| HED annotations (`HedMetadata`, `HedAnnotation`) | `hed-annotations` (fork) | https://github.com/LorenFrankLab/spyglass/pull/1723, draft |
| Sleep scoring and seizures (`SleepStateScoring`, `SeizureEvents`) | `sleep-scoring` (fork) | https://github.com/LorenFrankLab/spyglass/pull/1726, draft |

The HERD and HED PRs were opened for the Uchida lab ingestion (DANDI:001935) and name no lab; these files use them
unchanged. `sleep-scoring` is the follow-up promised on #1634
(https://github.com/LorenFrankLab/spyglass/issues/1634#issuecomment-5677814596). It selects a sleep scoring table by
its `sleep_state` column and a seizure table by the name `seizure_events`; the PR, opened as a draft on 2026-11-19,
asks the Spyglass team whether those conventions suit them. Its tests pass on upstream's CI setup (pynwb 3, numpy
1.26).

## Other upstream work these files depend on

| Link | State | Relevance |
| --- | --- | --- |
| https://github.com/LorenFrankLab/spyglass/issues/1694 | issue, open | pynwb>=4 / hdmf>=6. The files are NWB 2.11 and need pynwb 4.2 / hdmf 6.2; the bootstrap installs them over Spyglass's pins. |
| https://github.com/LorenFrankLab/spyglass/pull/1609 | PR, open | Spyglass pins `numpy<2` and `scipy<1.13` until this lands; the bootstrap overrides both because ndx-hed needs numpy 2. |
| https://github.com/LorenFrankLab/ndx-franklab-novela/pull/26 | PR, open | Reworks novela's pyproject, keeps `hdmf<5`. |

## Known gaps

- `Electrode` takes its region from the electrode group, so every EEG electrode is in `cerebral cortex`. The cortical
  area and channel name of each screw (the `location` and `channel_name` columns of the electrodes table) have no
  Spyglass column; the notebooks read them from the file.
- `DataAcquisitionDevice` stays empty: it needs an `ndx_franklab_novela.DataAcqDevice`, and the files have a plain
  `Device` (`TainiTecWirelessEEG`).
- `TaskEpoch` stays empty: the files have no task table. The baseline windows are in `IntervalList` from the epochs
  table.
- Not ingested: `swd_epochs` (spike-wave discharge flags per epoch), `seizure_counts_by_zt_hour` and
  `sleep_state_power_spectra`. They stay in the NWB files.
- GRIN2B-228 is heterozygous but its file has 2 seizures, against 887 to 2121 in the other heterozygous rats. The
  source file has the same 2 rows, so this is a question for the lab, not an ingestion error.

## Idea to pitch: the sleep analysis as a Spyglass pipeline

The files carry the lab's analysis results: the sleep scoring, the seizure detection, the spike-wave discharge
flags, the hourly seizure counts and the power spectrum of each state, computed by the lab's
[AUTOMATIC-SLEEP-SCORER](https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER). With `ImportedEEG` and the
sleep tables in Spyglass, the same analysis could run as Spyglass computed tables: for example a state power spectrum
table that depends on `ImportedEEG` and `SleepStateScoring`, and a scoring table computed from the EEG and EMG with
versioned parameters, next to the imported one. This needs the lab to agree that the method can be reproduced
outside their code, and the Spyglass team to agree on where such tables belong. It is only an idea for now; nobody has
started on it.

## When a PR changes or merges

1. Rebuild the branch `gonzalez-sulser-integration` on the fork from upstream `master` and the PR branches still
   open, and tag it (`gonzalez-sulser-example-v2`, ...).
2. Point `spyglass-env.yaml` and `bootstrap_wsl.sh` at the new tag, or at a Spyglass release once everything is
   merged.
3. Rebuild the env, reset the database, ingest the 24 files and re-run the notebooks, as in the docs. Update the
   notebooks if table names or fetchers changed.
4. Update this file, the docs and the tracking issue.
