"""The ontology terms in grin2b_general_metadata.yaml must reach the file as HERD references.

NeuroConv reads them from metadata["ExternalResources"] and ignores any other key, so a block under an
outdated name produces a file with no references and no error.
"""

from datetime import datetime, timezone
from pathlib import Path

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
        subject=Subject(subject_id="GRIN2B-129", species="Rattus norvegicus", strain="Long-Evans", genotype=genotype, sex="M"),
    )
    device = nwbfile.create_device(name="TainiTecWirelessEEG")
    group = nwbfile.create_electrode_group(name="EEGArray", description="EEG", location="cortex", device=device)
    nwbfile.add_electrode(location="S1_Tr", group=group)
    return nwbfile


def test_yaml_terms_are_written_as_herd_references():
    metadata = load_dict_from_file(GENERAL_METADATA)
    nwbfile = _nwbfile(genotype="Het")

    add_external_resources_to_nwbfile(nwbfile, metadata=metadata)

    references = nwbfile.external_resources.to_dataframe()
    assert dict(zip(references["key"], references["entity_id"])) == {
        "Rattus norvegicus": "NCBITaxon:10116",
        "Long-Evans": "RRID:RGD_2308852",
        "Het": "RRID:RGD_14394515",
        "S1_Tr": "UBERON:0008933",
        "cortex": "UBERON:0000956",
    }


def test_wild_type_genotype_is_not_annotated():
    metadata = load_dict_from_file(GENERAL_METADATA)
    nwbfile = _nwbfile(genotype="Wt")

    add_external_resources_to_nwbfile(nwbfile, metadata=metadata)

    assert "Wt" not in set(nwbfile.external_resources.to_dataframe()["key"])
