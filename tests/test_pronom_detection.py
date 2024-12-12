import pytest
import mdto
from mdto.gegevensgroepen import *


def test_pronom_siegfried(voorbeeld_archiefstuk_xml):
    """Test siegfried-based PRONOM detection"""
    expected = BegripGegevens(
        "Extensible Markup Language", VerwijzingGegevens("PRONOM-register"), "fmt/101"
    )
    got = mdto._pronominfo_siegfried(voorbeeld_archiefstuk_xml)
    assert expected == got


def test_pronom_fido(voorbeeld_archiefstuk_xml):
    """Test fido-based PRONOM detection"""
    expected = BegripGegevens(
        "Extensible Markup Language", VerwijzingGegevens("PRONOM-register"), "fmt/101"
    )
    got = mdto._pronominfo_fido(voorbeeld_archiefstuk_xml)
    assert expected == got
