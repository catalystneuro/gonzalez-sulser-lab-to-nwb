"""The ontology terms in grin2b_general_metadata.yaml must reach the file as HERD references.

NeuroConv reads them from the maps of metadata["ExternalResources"] it knows and writes nothing for any
other key, so a map under an outdated name produces a file without those references.
"""

import json
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import jsonschema
from neuroconv.tools.external_resources import add_external_resources_to_nwbfile
from neuroconv.utils import load_dict_from_file
from pynwb import NWBFile
from pynwb.file import Subject

GENERAL_METADATA = (
    Path(__file__).parents[1] / "src" / "gonzalez_sulser_lab_to_nwb" / "grin2b" / "metadata" / "grin2b_general_metadata.yaml"
)


def _nwbfile(genotype: str) -> NWBFile:
    nwbfile = NWBFile(
        session_description="test",
        identifier="test",
        session_start_time=datetime(2021, 3, 26, tzinfo=timezone.utc),
        experimenter=["Hristova, Katerina", "McLaughlin, Niamh"],
        institution="University of Edinburgh",
        subject=Subject(subject_id="GRIN2B-129", species="Rattus norvegicus", strain="Long-Evans", genotype=genotype, sex="M"),
    )
    device = nwbfile.create_device(name="TainiTecWirelessEEG")
    group = nwbfile.create_electrode_group(name="EEGArray", description="EEG", location="cortex", device=device)
    nwbfile.add_electrode(location="S1_Tr", group=group)
    return nwbfile


def test_yaml_maps_match_neuroconv_schema():
    base_schema = json.loads((files("neuroconv") / "schemas" / "base_metadata_schema.json").read_text())
    schema = {
        "type": "object",
        "properties": {"ExternalResources": base_schema["properties"]["ExternalResources"]},
        "definitions": base_schema["definitions"],
    }
    metadata = load_dict_from_file(GENERAL_METADATA)

    jsonschema.validate({"ExternalResources": metadata["ExternalResources"]}, schema)


def test_yaml_terms_are_written_as_herd_references():
    metadata = load_dict_from_file(GENERAL_METADATA)
    nwbfile = _nwbfile(genotype="Het")

    add_external_resources_to_nwbfile(nwbfile, metadata=metadata)

    references = nwbfile.external_resources.to_dataframe()
    assert dict(zip(references["key"], references["entity_id"])) == {
        "Hristova, Katerina": "orcid:0009-0000-4079-8676",
        "University of Edinburgh": "ror:01nrxwf90",
        "Rattus norvegicus": "NCBITaxon:10116",
        "Long-Evans": "RRID:RGD_2308852",
        "S1_Tr": "UBERON:0008933",
        "cortex": "UBERON:0000956",
    }
