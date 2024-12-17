import pytest

from mdto.gegevensgroepen import *
from mdto.utilities import _pronominfo_fido, _pronominfo_siegfried


def test_pronom_siegfried(voorbeeld_archiefstuk_xml):
    """Test siegfried-based PRONOM detection"""
    expected = BegripGegevens(
        "Extensible Markup Language", VerwijzingGegevens("PRONOM-register"), "fmt/101"
    )
    got = _pronominfo_siegfried(voorbeeld_archiefstuk_xml)
    assert expected == got


def test_pronom_fido(voorbeeld_archiefstuk_xml):
    """Test fido-based PRONOM detection"""
    expected = BegripGegevens(
        "Extensible Markup Language", VerwijzingGegevens("PRONOM-register"), "fmt/101"
    )
    got = _pronominfo_fido(voorbeeld_archiefstuk_xml)
    assert expected == got
