import pytest
import lxml.etree as ET
from pathlib import Path
from mdto import (
    Informatieobject,
    IdentificatieGegevens,
    VerwijzingGegevens,
    BeperkingGebruikGegevens,
    BegripGegevens,
    create_bestand,
)


def test_informatieobject_xml_validity(mdto_xsd):
    """Test if running to_xml() on a informatieobject procudes valid MDTO XML"""
    # create a schema object from the MDTO XSD
    mdto_schema = ET.XMLSchema(ET.parse(mdto_xsd))
    # create informatieobject
    informatieobject = Informatieobject(
        naam="Verlenen kapvergunning",
        identificatie=IdentificatieGegevens("abcd-1234", "Corsa (Geldermalsen)"),
        archiefvormer=VerwijzingGegevens("Geldermalsen"),
        beperkingGebruik=BeperkingGebruikGegevens(
            BegripGegevens("nvt", VerwijzingGegevens("geen"))
        ),
        waardering=BegripGegevens(
            "V", VerwijzingGegevens("Begrippenlijst Waarderingen MDTO")
        ),
    )

    # lxml is silly, and does not bind namespaces to nodes until _after_ they've been serialized.
    # See: https://stackoverflow.com/questions/22535284/strange-lxml-behavior
    # As a workaround, we serialize the ElemenTree object to a string, and then deserialize this
    # namespaced string. There are other ways to fix this, but their decreased readability does not
    # outweigh mildly complicating this test.
    informatieobject_xml = ET.fromstring(ET.tostring(informatieobject.to_xml()))

    # validate against schema
    assert mdto_schema.validate(informatieobject_xml)


def test_automatic_bestand_xml_validity(mdto_xsd, voorbeeld_archiefstuk_xml):
    """Test if running to_xml() on a automatically generated Bestand procudes valid MDTO XML"""
    # create a schema object from the MDTO XSD
    mdto_schema = ET.XMLSchema(ET.parse(mdto_xsd))

    # use this .py file for automatic metadata generation
    example_file = Path(__file__)
    # create Bestand object from README.md + existing informatieobject
    bestand = create_bestand(
        example_file,
        "abcd-1234",
        "Corsa",
        voorbeeld_archiefstuk_xml,
        url="https://example.com/",
    )

    # see comment about lxml above
    bestand_xml = ET.fromstring(ET.tostring(bestand.to_xml()))

    # validate against schema
    assert mdto_schema.validate(bestand_xml)
