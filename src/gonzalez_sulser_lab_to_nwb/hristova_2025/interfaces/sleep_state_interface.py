"""Sleep states scored by the lab's automated sleep scorer, one per 5-s epoch.

Source: Sleep state classifications/<subject>/<subject>_BL{N}-dge_ok.csv, one column "sleep.score" with 17,280 rows
(24 h of 5-s epochs). Codes 0 = Wake, 1 = NREM, 2 = REM (Hristova et al. 2025, supplementary methods). dge_ok.csv is
the scorer's output before SWD epochs are relabelled to 4 (correct.C in Sleep_autoscore_Beta.R,
AUTOMATIC-SLEEP-SCORER), so it holds only 0-2; the SWD flags are in the swd_epochs table (SwdEpochsInterface).

Each state label is annotated with HED tags and an ontology term from metadata["SleepStates"]
(metadata/general_metadata.yaml); see add_sleep_state_meanings.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from hdmf.common import HERD, DynamicTable, MeaningsTable
from ndx_hed import HedLabMetaData, HedTags
from ndx_hed.utils.hed_nwb_validator import HedNWBValidator
from pynwb import NWBFile, get_type_map
from pynwb.epoch import TimeIntervals

from .baseline_epochs_interface import BaseBaselineStreamInterface

EPOCH_DURATION_S = 5.0
SLEEP_STATE_LABELS = {0: "Wake", 1: "NREM", 2: "REM"}
SLEEP_STATE_COLUMN = "sleep_state"


def add_sleep_state_meanings(nwbfile: NWBFile, table: DynamicTable, sleep_states_metadata: dict) -> None:
    """Annotate the sleep_state column of a table with the meaning, HED tags and ontology term of each state.

    Adds the HED schema versions to the file (HedLabMetaData), a MeaningsTable named "sleep_state_meanings" with
    the columns value, meaning and HED, and a HERD reference from each value of the MeaningsTable to its ontology
    term. Raises if the HED tags do not validate against the schema.

    Parameters
    ----------
    nwbfile : NWBFile
    table : DynamicTable
        The table with the sleep_state column.
    sleep_states_metadata : dict
        "hed_schema_version", "description", and "states": state label -> "meaning", "HED" and "ontology_term"
        ({"id", "uri"}).
    """
    states = sleep_states_metadata["states"]
    if set(states) != set(SLEEP_STATE_LABELS.values()):
        raise ValueError(f"metadata['SleepStates'] defines {sorted(states)}; expected {sorted(SLEEP_STATE_LABELS.values())}.")

    hed_lab_metadata = HedLabMetaData(hed_schema_version=sleep_states_metadata["hed_schema_version"])
    nwbfile.add_lab_meta_data(hed_lab_metadata)

    meanings = MeaningsTable(target=table[SLEEP_STATE_COLUMN], description=sleep_states_metadata["description"])
    meanings.add_column(name="HED", description="HED annotation of each sleep state.", col_cls=HedTags)
    for value, state in states.items():
        meanings.add_row(value=value, meaning=state["meaning"], HED=state["HED"])
    table.add_meanings_table(meanings)

    issues = HedNWBValidator(hed_lab_metadata).validate_file(nwbfile)
    if issues:
        raise ValueError(f"HED validation found {len(issues)} issues: {issues}")

    # NeuroConv adds the terms of metadata["ExternalResources"] to this same HERD before writing.
    if nwbfile.external_resources is None:
        nwbfile.external_resources = HERD(type_map=get_type_map())
    for value, state in states.items():
        term = state["ontology_term"]
        nwbfile.external_resources.add_ref(
            container=meanings["value"], key=value, entity_id=term["id"], entity_uri=term["uri"]
        )


def read_epoch_codes(file_path: Path, column: str, valid_codes: set[int]) -> tuple[np.ndarray, np.ndarray]:
    """Read one code per 5-s epoch from a lab CSV; return the codes and the epoch start times from window start."""
    codes = pd.read_csv(file_path)[column].to_numpy(dtype=np.int64)
    unexpected = set(np.unique(codes).tolist()) - valid_codes
    if unexpected:
        raise ValueError(f"{file_path}: unexpected {column} codes {sorted(unexpected)} (expected {sorted(valid_codes)}).")
    return codes, np.arange(len(codes)) * EPOCH_DURATION_S


class SleepStateInterface(BaseBaselineStreamInterface):
    """Automated sleep-state scores (5-s epochs), written to processing/behavior/sleep_states."""

    keywords = ["sleep", "sleep state", "EEG", "NREM", "REM", "Wake"]
    table_name = "sleep_states"
    table_class = TimeIntervals
    table_description = (
        "Automated sleep state classifications in 5-second epochs produced by the Gonzalez-Sulser lab scoring "
        "pipeline (https://github.com/Gonzalez-Sulser-Team/AUTOMATIC-SLEEP-SCORER), from its *-dge_ok.csv output. "
        "State codes: 0=Wake, 1=NREM, 2=REM. These are the scores before spike-wave discharge (SWD) epochs are "
        "relabelled, so epochs containing SWDs are scored as Wake, NREM or REM here. The scorer labels the epochs "
        "flagged in the swd_epochs table (is_swd) as SWD (state 4); that relabelled output is not part of the shared "
        "data."
    )
    column_descriptions = dict(
        sleep_score="Integer sleep state code (0=Wake, 1=NREM, 2=REM).",
        sleep_state="Human-readable sleep state label derived from sleep_score.",
    )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, stub_test=stub_test)
        add_sleep_state_meanings(nwbfile, nwbfile.processing["behavior"][self.table_name], metadata["SleepStates"])

    def read_file(self, file_path: Path) -> pd.DataFrame:
        scores, start_times = read_epoch_codes(file_path, "sleep.score", set(SLEEP_STATE_LABELS))
        return pd.DataFrame(
            dict(
                start_time=start_times,
                stop_time=start_times + EPOCH_DURATION_S,
                sleep_score=scores,
                sleep_state=[SLEEP_STATE_LABELS[score] for score in scores],
            )
        )
