import dataclasses
import hashlib
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, TextIO

from . import helpers

import lxml.etree as ET
import validators

# globals
MDTO_MAX_NAAM_LENGTH = 80


# setup logging
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
logging.addLevelName(
    # colorize warning messages
    logging.WARNING,
    "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING),
)


class XMLSerializable:
    """Provides a to_xml() method for converting MDTO dataclasses to XML."""

    def _mdto_ordered_fields(self) -> List:
        """Sort dataclass fields by their order in the MDTO XSD.

        This method should be overridden when the order of fields in
        a dataclass does not match the order required by the MDTO XSD.

        Such mismatches occur because Python only allows optional arguments
        at the _end_ of a function's signature, while MDTO allows optional
        attributes to appear anywhere.
        """
        return dataclasses.fields(self)

    def to_xml(self, root: str) -> ET.Element:
        """Transform dataclass to XML tree.

        Args:
            root (str): name of the new root tag

        Returns:
            ET.Element: XML representation of object new root tag
        """
        root_elem = ET.Element(root)
        # get dataclass fields, but in the order required in the MDTO XSD
        fields = self._mdto_ordered_fields()

        # TODO: add a call to yet-to-be-implemented .validate() method here
        # This call will raise an error if the value(s) of field a in a dataclass are not of the right type

        # process all fields in dataclass
        for field in fields:
            field_name = field.name
            field_value = getattr(self, field_name)
            self._process_dataclass_field(root_elem, field_name, field_value)

        return root_elem

    def _process_dataclass_field(
        self, root_elem: ET.Element, field_name: str, field_value: Any
    ):
        """Recursively process a dataclass field, and append its XML representation to `root_elem`."""

        if field_value is None:
            # skip fields with no value
            return
        elif isinstance(field_value, (list, tuple, set)):
            # serialize all *Gegevens objects in a sequence
            for mdto_gegevens in field_value:
                root_elem.append(mdto_gegevens.to_xml(field_name))
        elif isinstance(field_value, XMLSerializable):
            # serialize *Gegevens object
            root_elem.append(field_value.to_xml(field_name))
        else:
            # serialize primitive
            new_elem = ET.SubElement(root_elem, field_name)
            # XML serialization can only happen on string values
            new_elem.text = str(field_value)


@dataclass
class IdentificatieGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/identificatieGegevens

    Args:
        identificatieKenmerk (str): Een kenmerk waarmee een object geïdentificeerd kan worden
        identificatieBron (str): Herkomst van het kenmerk
    """

    identificatieKenmerk: str
    identificatieBron: str


@dataclass
class VerwijzingGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/verwijzingsGegevens

    Args:
        verwijzingNaam (str): Naam van het object waarnaar verwezen wordt
        verwijzingIdentificatie (Optional[IdentificatieGegevens]): Identificatie van object waarnaar verwezen wordt
    """

    verwijzingNaam: str
    verwijzingIdentificatie: IdentificatieGegevens = None


@dataclass
class BegripGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/begripGegevens

    Args:
        begripLabel (str): De tekstweergave van het begrip dat is toegekend in de begrippenlijst
        begripBegrippenlijst (VerwijzingGegevens): Verwijzing naar een beschrijving van de begrippen
        begripCode (Optional[str]): De code die aan het begrip is toegekend in de begrippenlijst
    """

    begripLabel: str
    begripBegrippenlijst: VerwijzingGegevens
    begripCode: str = None

    def _mdto_ordered_fields(self) -> List:
        """Sort dataclass fields by their order in the MDTO XSD."""
        fields = super()._mdto_ordered_fields()
        # swap order of begripBegrippenlijst and begripCode
        return fields[:-2] + (fields[2], fields[1])


@dataclass
class TermijnGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/termijnGegevens

    Args:
        termijnTriggerStartLooptijd (Optional[BegripGegevens]): Gebeurtenis waarna de looptijd van de termijn start
        termijnStartdatumLooptijd (Optional[str]): Datum waarop de looptijd is gestart
        termijnLooptijd (Optional[str]): Hoeveelheid tijd waarin de termijnEindDatum bereikt wordt
        termijnEinddatum (Optional[str]): Datum waarop de termijn eindigt
    """

    termijnTriggerStartLooptijd: BegripGegevens = None
    termijnStartdatumLooptijd: str = None
    termijnLooptijd: str = None
    termijnEinddatum: str = None


@dataclass
class ChecksumGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/checksum

    Note:
        When building Bestand objects, it's recommended to call the convience function `bestand_from_file()`.
        And if you just need to update a Bestand object's checksum, you should use `create_checksum()`.
    """

    checksumAlgoritme: BegripGegevens
    checksumWaarde: str
    checksumDatum: str

    def to_xml(self, root: str = "checksum") -> ET.Element:
        """Transform ChecksumGegevens into XML tree.

        Returns:
             ET.Element: XML representation of object
        """
        return super().to_xml(root)


@dataclass
class BeperkingGebruikGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/beperkingGebruik

    Args:
        beperkingGebruikType (BegripGegevens): Typering van de beperking
        beperkingGebruikNadereBeschrijving (Optional[str]): Beschrijving van de beperking
        beperkingGebruikDocumentatie (Optional[VerwijzingGegevens]): Verwijzing naar een tekstdocument met
            daarin een beschrijving van de beperking
        beperkingGebruikTermijn (Optional[TermijnGegevens]): Termijn waarbinnen de beperking van toepassing is
    """

    beperkingGebruikType: BegripGegevens
    beperkingGebruikNadereBeschrijving: str = None
    beperkingGebruikDocumentatie: VerwijzingGegevens | list[VerwijzingGegevens] = None
    beperkingGebruikTermijn: TermijnGegevens = None

    def to_xml(self, root: str = "beperkingGebruik") -> ET.Element:
        """Transform BeperkingGebruikGegevens into XML tree.

        Returns:
            ET.Element: XML representation of BeperkingGebruikGegevens
        """
        return super().to_xml(root)


@dataclass
class DekkingInTijdGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/dekkingInTijd

    Args:
        dekkingInTijdType (BegripGegevens): Typering van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdBegindatum (str): Begindatum van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdEinddatum (Optional[str]): Einddatum van de periode waar het informatieobject betrekking op heeft
    """

    dekkingInTijdType: BegripGegevens
    dekkingInTijdBegindatum: str
    dekkingInTijdEinddatum: str = None

    def to_xml(self, root: str = "dekkingInTijd") -> ET.Element:
        return super().to_xml(root)


@dataclass
class EventGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/event

    Args:
        eventType (BegripGegevens): Aanduiding van het type event
        eventTijd (Optional[str]): Tijdstip waarop het event heeft plaatsgevonden
        eventVerantwoordelijkeActor (Optional[VerwijzingGegevens]): Actor die verantwoordelijk was voor het event
        eventResultaat (Optional[str]): Beschrijving van het resultaat van het event
    """

    eventType: BegripGegevens
    eventTijd: str = None
    eventVerantwoordelijkeActor: VerwijzingGegevens = None
    eventResultaat: str = None

    def to_xml(self, root: str = "event") -> ET.Element:
        return super().to_xml(root)


@dataclass
class RaadpleeglocatieGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatie

    Args:
        raadpleeglocatieFysiek (Optional[VerwijzingGegevens])): Fysieke raadpleeglocatie van het informatieobject
        raadpleeglocatieOnline (Optional[str]): Online raadpleeglocatie van het informatieobject; moet een valide URL zijn
    """

    raadpleeglocatieFysiek: VerwijzingGegevens | List[VerwijzingGegevens] = None
    raadpleeglocatieOnline: str | List[VerwijzingGegevens] = None

    def to_xml(self, root: str = "raadpleeglocatie"):
        return super().to_xml(root)

    @property
    def raadpleeglocatieOnline(self):
        return self._raadpleeglocatieOnline

    @raadpleeglocatieOnline.setter
    def raadpleeglocatieOnline(self, url: str | List[str]):
        """https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatieOnline

        Args:
            url (str): any RFC 3986 compliant URI
        """
        # if url is not set, (e.g. when calling RaadpleegLocatieGegevens() without arguments)
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None:  # check if empty
            self._raadpleeglocatieOnline = None
        elif isinstance(url, list) and all(validators.url(u) for u in url):
            self._raadpleeglocatieOnline = url
        elif isinstance(url, str) and validators.url(url):
            self._raadpleeglocatieOnline = url
        else:
            raise ValueError(f"URL '{url}' is malformed")


@dataclass
class GerelateerdInformatieobjectGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/gerelateerdInformatieobjectGegevens

    Args:
        gerelateerdInformatieobjectVerwijzing (VerwijzingGegevens): Verwijzing naar het gerelateerde informatieobject
        gerelateerdInformatieobjectTypeRelatie (BegripGegevens): Typering van de relatie
    """

    gerelateerdInformatieobjectVerwijzing: VerwijzingGegevens
    gerelateerdInformatieobjectTypeRelatie: BegripGegevens

    def to_xml(self, root: str = "gerelateerdInformatieobject") -> ET.Element:
        return super().to_xml(root)


@dataclass
class BetrokkeneGegevens(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/betrokkeneGegevens

    Args:
        betrokkeneTypeRelatie (BegripGegevens): Typering van de betrokkenheid van de actor bij het informatieobject
        betrokkeneActor (VerwijzingGegevens): Persoon of organisatie die betrokken is bij het informatieobject
    """

    betrokkeneTypeRelatie: BegripGegevens
    betrokkeneActor: VerwijzingGegevens

    def to_xml(self, root: str = "betrokkene") -> ET.Element:
        return super().to_xml(root)


@dataclass
class Object(XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/object

    This class serves as the parent class to Informatieobject and Bestand.
    There is no reason to use it directly.

    MDTO objects that derive from this class inherit a save() method, which can be used
    to write an Informatieobject/Bestand to a XML file.
    """

    identificatie: IdentificatieGegevens | List[IdentificatieGegevens]
    naam: str

    def __post_init__(self):
        # check if name is of the right length
        if len(self.naam) > MDTO_MAX_NAAM_LENGTH:
            logging.warning(
                f"value '{self.naam}' of property naam "
                f"exceeds maximum length of {MDTO_MAX_NAAM_LENGTH}"
            )

    def to_xml(self, root: str) -> ET.ElementTree:
        """Transform Object into an XML tree with the following structure:

        ```xml
        <MDTO xmlns=…>
            <root> <!-- e.g. bestand -->
                …
            </root>
        </MDTO>
        ```
        Returns:
            ET.ElementTree: XML tree representing the Object
        """

        # construct attributes of <MDTO>
        xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {
            None: "https://www.nationaalarchief.nl/mdto",  # default namespace (i.e. xmlns=https...)
            "xsi": xsi_ns,
        }

        # create <MDTO>
        mdto = ET.Element("MDTO", nsmap=nsmap)

        # set schemaLocation attribute of <MDTO>
        mdto.set(
            f"{{{xsi_ns}}}schemaLocation",
            "https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd",
        )

        # convert all dataclass fields to their XML representation
        children = super().to_xml(root)
        mdto.append(children)

        tree = ET.ElementTree(mdto)
        # use tabs as indentation (this matches what MDTO does)
        ET.indent(tree, space="\t")
        return tree

    def save(
        self,
        file_or_filename: str | TextIO,
        lxml_args: dict = {
            "xml_declaration": True,
            "pretty_print": True,
            "encoding": "UTF-8",
        },
    ) -> None:
        """Save object to an XML file.

        Args:
            file_or_filename (str | TextIO): Path or file-object to write the object's XML representation to.
              If passing a file-like object, the file must be opened
              in writeable binary mode (i.e. `wb`).
            lxml_args (Optional[dict]): Extra keyword arguments to pass to lxml's write() method.
              Defaults to `xml_declaration=True, pretty_print=True, encoding="UTF-8"`.

        Note:
            For a complete list of options for lxml's write method, see
            https://lxml.de/apidoc/lxml.etree.html#lxml.etree._ElementTree.write
        """

        xml = self.to_xml()
        xml.write(file_or_filename, **lxml_args)


# TODO: place more restrictions on taal?
@dataclass
class Informatieobject(Object, XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/informatieobject

    Example:

    ```python
    informatieobject = Informatieobject(IdentificatieGegevens(…), naam="Kapvergunning", …)

    # write object to file
    informatieobject.save("Informatieobject-368-Kapvergunning.xml")
    ```

    Args:
        identificatie (IdentificatieGegevens | List[IdentificatieGegevens]): Identificatiekenmerk
        naam (str): Aanduiding waaronder het object bekend is
        archiefvormer (VerwijzingGegevens | List[VerwijzingGegevens]): Maker/ontvanger
        beperkingGebruik (BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]): Beperking op het gebruik
        waardering (BegripGegevens): Waardering volgens een selectielijst
        aggregatieniveau (Optional[BegripGegevens]): Aggregatieniveau
        classificatie (Optional[BegripGegevens | List[BegripGegevens]]): Classificatie volgens een classificatieschema
        trefwoord (Optional[str | List[str]]): Trefwoord
        omschrijving (Optional[str | List[str]]): Inhoudelijke omschrijving
        raadpleeglocatie(Optional[RaadpleeglocatieGegevens | List[RaadpleeglocatieGegevens]]): Raadpleeglocatie
        dekkingInTijd (Optional[DekkingInTijdGegevens | List[DekkingInTijdGegevens]]): Betreffende periode/tijdstip
        dekkingInRuimte (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Betreffende plaats/locatie
        taal (Optional[str]): Taal van het object
        event (Optional[EventGegevens | List[EventGegevens]]): Gerelateerde gebeurtenis
        bewaartermijn (Optional[TermijnGegevens]): Termijn waarin het object bewaard dient te worden
        informatiecategorie (Optional[BegripGegevens]): Informatiecategorie waar de bewaartermijn op gebaseerd is
        isOnderdeelVan (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Bovenliggende aggregatie
        bevatOnderdeel (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Direct onderliggend object
        heeftRepresentatie (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Bijbehorend Bestand object
        aanvullendeMetagegevens (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Aanvullende metagegevens
        gerelateerdInformatieobject (Optional[GerelateerdInformatieobjectGegevens | List[GerelateerdInformatieobjectGegevens]]): Gerelateerd object
        betrokkene (Optional[BetrokkeneGegevens | List[BetrokkeneGegevens]]): Persoon/organisatie betrokken bij
          ontstaan en gebruik van dit object
        activiteit (Optional[VerwijzingGegevens | List[VerwijzingGegevens]]): Activiteit waarbij dit object
          is gemaakt/ontvangen
    """

    archiefvormer: VerwijzingGegevens | List[VerwijzingGegevens]
    beperkingGebruik: BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]
    waardering: BegripGegevens
    aggregatieniveau: BegripGegevens = None
    classificatie: BegripGegevens | List[BegripGegevens] = None
    trefwoord: str | List[str] = None
    omschrijving: str = None
    raadpleeglocatie: RaadpleeglocatieGegevens | List[RaadpleeglocatieGegevens] = None
    dekkingInTijd: DekkingInTijdGegevens | List[DekkingInTijdGegevens] = None
    dekkingInRuimte: VerwijzingGegevens | List[VerwijzingGegevens] = None
    taal: str = None
    event: EventGegevens | List[EventGegevens] = None
    bewaartermijn: TermijnGegevens = None
    informatiecategorie: BegripGegevens = None
    isOnderdeelVan: VerwijzingGegevens | List[VerwijzingGegevens] = None
    bevatOnderdeel: VerwijzingGegevens | List[VerwijzingGegevens] = None
    heeftRepresentatie: VerwijzingGegevens | List[VerwijzingGegevens] = None
    aanvullendeMetagegevens: VerwijzingGegevens | List[VerwijzingGegevens] = None
    gerelateerdInformatieobject: (
        GerelateerdInformatieobjectGegevens | List[GerelateerdInformatieobjectGegevens]
    ) = None
    betrokkene: BetrokkeneGegevens | List[BetrokkeneGegevens] = None
    activiteit: VerwijzingGegevens | List[VerwijzingGegevens] = None

    def _mdto_ordered_fields(self) -> List:
        """Sort dataclass fields by their order in the MDTO XSD."""
        sorting_mapping = {
            "identificatie": 0,
            "naam": 1,
            "aggregatieniveau": 2,
            "classificatie": 3,
            "trefwoord": 4,
            "omschrijving": 5,
            "raadpleeglocatie": 6,
            "dekkingInTijd": 7,
            "dekkingInRuimte": 8,
            "taal": 9,
            "event": 10,
            "waardering": 11,
            "bewaartermijn": 12,
            "informatiecategorie": 13,
            "isOnderdeelVan": 14,
            "bevatOnderdeel": 15,
            "heeftRepresentatie": 16,
            "aanvullendeMetagegevens": 17,
            "gerelateerdInformatieobject": 18,
            "archiefvormer": 19,
            "betrokkene": 20,
            "activiteit": 21,
            "beperkingGebruik": 22,
        }

        return [
            field
            for field in sorted(
                dataclasses.fields(self), key=lambda f: sorting_mapping[f.name]
            )
        ]

    def to_xml(self) -> ET.ElementTree:
        """Transform Informatieobject into an XML tree with the following structure:

        ```xml
        <MDTO xmlns=…>
            <informatieobject>
                …
            </informatieobject>
        </MDTO>
        ```

        Note:
           When trying to save a Informatieobject to a file, use `my_informatieobject.save('file.xml')` instead.

        Returns:
            ET.ElementTree: XML tree representing the Informatieobject object
        """
        return super().to_xml("informatieobject")


@dataclass
class Bestand(Object, XMLSerializable):
    """https://www.nationaalarchief.nl/archiveren/mdto/bestand

    Note:
        When creating Bestand objects, it's easier to use the
        `bestand_from_file()` convenience function instead.

    Args:
        identificatie (IdentificatieGegevens | List[IdentificatieGegevens]): Identificatiekenmerk
        naam (str): Aanduiding waaronder dit object bekend is (meestal bestandsnaam)
        omvang (int): Aantal bytes in het bestand
        bestandsformaat (BegripGegevens): Bestandsformaat, bijv. PRONOM of MIME-type informatie
        checksum (ChecksumGegevens): Checksum gegevens van het bestand
        isRepresentatieVan (VerwijzingGegevens): Object waarvan dit bestand een representatie is
        URLBestand (Optional[str]): Actuele verwijzing naar dit bestand als RFC 3986 conforme URI
    """

    omvang: int
    bestandsformaat: BegripGegevens
    checksum: ChecksumGegevens | List[ChecksumGegevens]
    isRepresentatieVan: VerwijzingGegevens
    URLBestand: str = None

    def _mdto_ordered_fields(self) -> List:
        """Sort dataclass fields by their order in the MDTO XSD."""
        fields = super()._mdto_ordered_fields()
        # swap order of isRepresentatieVan and URLbestand
        return fields[:-2] + (fields[-1], fields[-2])

    def to_xml(self) -> ET.ElementTree:
        """
        Transform Bestand into an XML tree with the following structure:

        ```xml
        <MDTO xmlns=…>
            <bestand>
                …
            </bestand>
        </MDTO>
        ```

        Note:
           When trying to save a Bestand object to a file, use `my_bestand.save('file.xml')` instead.

        Returns:
            ET.ElementTree: XML tree representing Bestand object
        """
        return super().to_xml("bestand")

    @property
    def URLBestand(self):
        return self._URLBestand

    @URLBestand.setter
    def URLBestand(self, url: str):
        """https://www.nationaalarchief.nl/archiveren/mdto/URLBestand

        Args:
            url (str): any RFC 3986 compliant URI
        """
        # if url is not set (e.g. when calling Bestand() without the URLBestand argument),
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None:  # check if empty
            self._URLBestand = None
        elif validators.url(url):
            self._URLBestand = url
        else:
            raise ValueError(f"URL '{url} is malformed")


def pronominfo(path: str) -> BegripGegevens:
    # FIXME: format more properly
    """Use fido library to generate PRONOM information about a file.
    This information can be used in the <bestandsformaat> tag.

    Args:
        path (str): path to the file to inspect

    Returns:
        ``BegripGegevens`` object with the following properties::
            {
                `begripLabel`: file's PRONOM signature name
                `begripCode`: file's PRONOM ID
                `begripBegrippenLijst`: reference to PRONOM registry
            }
    """

    # Note: fido currently lacks a public API
    # Hence, the most robust solution is to invoke fido as a cli program
    # Upstream issue: https://github.com/openpreserve/fido/issues/94
    # downside is that this is slow, maybe siegfried speeds things up?

    # check if fido program exists
    if not shutil.which("fido"):
        raise RuntimeError(
            "Program 'fido' not found. For installation instructions, "
            "see https://github.com/openpreserve/fido#installation"
        )

    cmd = [
        "fido",
        "-q",
        "-matchprintf",
        "OK,%(info.formatname)s,%(info.puid)s,\n",
        "-nomatchprintf",
        "FAIL",
        path,
    ]

    cmd_result = subprocess.run(
        cmd, capture_output=True, shell=False, text=True, check=True
    )
    stdout = cmd_result.stdout
    stderr = cmd_result.stderr
    returncode = cmd_result.returncode

    # fido prints warnings about empty files to stderr
    if "(empty)" in stderr.lower():
        logging.warning(f"file {path} appears to be an empty file")

    # check for errors
    if returncode != 0:
        raise RuntimeError(
            f"fido PRONOM detection failed on file {path} with error:\n {stderr}"
        )
    elif stdout.startswith("OK"):
        results = stdout.split("\n")
        if len(results) > 2:  # .split('\n') returns a list of two items
            logging.warning(
                "fido returned more than one PRONOM match "
                f"for file {path}. Selecting the first one."
            )

        # strip "OK" from the output
        results = results[0].split(",")[1:]
        verwijzing = VerwijzingGegevens(verwijzingNaam="PRONOM-register")
        return BegripGegevens(
            begripLabel=results[0],
            begripCode=results[1],
            begripBegrippenlijst=verwijzing,
        )
    else:
        raise RuntimeError(f"fido PRONOM detection failed on file {path}")


def _detect_verwijzing(informatieobject: TextIO | str) -> VerwijzingGegevens:
    """A Bestand object must contain a reference to a corresponding informatieobject.
    Specifically, it expects an <isRepresentatieVan> tag with the following children:

    1. <verwijzingNaam>: name of the informatieobject
    2. <verwijzingIdentificatie> (optional): reference to the
    informatieobject's ID and source thereof

    This function infers these so-called 'VerwijzingGegevens' by
    parsing the XML of the file `informatieobject`.

    Args:
        informatieobject (TextIO | str): XML file to infer VerwijzingGegevens from

    Returns:
        `VerwijzingGegevens`, refering to the informatieobject specified by `informatieobject`
    """

    id_gegevens = None
    namespaces = {"mdto": "https://www.nationaalarchief.nl/mdto"}
    tree = ET.parse(informatieobject)
    root = tree.getroot()

    id_xpath = ".//mdto:informatieobject/mdto:identificatie/"

    kenmerk = root.find(f"{id_xpath}mdto:identificatieKenmerk", namespaces=namespaces)
    bron = root.find(f"{id_xpath}mdto:identificatieBron", namespaces=namespaces)
    naam = root.find(".//mdto:informatieobject/mdto:naam", namespaces=namespaces)

    if None in [kenmerk, bron]:
        raise ValueError(f"Failed to detect <identificatie> in {informatieobject}")

    identificatie = IdentificatieGegevens(kenmerk.text, bron.text)

    if naam is None:
        raise ValueError(f"Failed to detect <naam> in {informatieobject}")

    return VerwijzingGegevens(naam.text, identificatie)


def bestand_from_file(
    file: TextIO | str,
    identificatie: IdentificatieGegevens | List[IdentificatieGegevens],
    isrepresentatievan: VerwijzingGegevens | TextIO | str,
    url: str = None,
) -> Bestand:
    """Convenience function for creating a Bestand object from a file. The difference
    between this function and calling Bestand() directly is that this function infers
    most Bestand-related information for you (checksum, name, and so on), based on
    the characteristics of `file`. The value of <naam>, for example, is always set to the
    name of `file`.


    Args:
      file (TextIO | str): the file the Bestand object represents
      identificatie (IdentificatieGegevens | List[IdentificatieGegevens]): identificatiekenmerk of
        Bestand object
      isrepresentatievan (TextIO | str | VerwijzingGegevens): a XML file that contains an
        an informatieobject, or a VerwijzingGegevens object referencing an informatieobject.
        Used to construct the values for <isRepresentatieVan>.
      url (Optional[str]): value of <URLBestand>

    Example:
      ```python

      with open('informatieobject_001.xml') as f:
          bestand = mdto.bestand_from_file("vergunning.pdf",
                                   IdentificatieGegevens('34c5-4379-9f1a-5c378', 'Proza (DMS)'),
                                   informatieobject=f)
     bestand.save("vergunning.bestand.mdto.xml")
      ```

    Returns:
        Bestand: new Bestand object
    """
    file = helpers.process_file(file)

    # set <naam> to basename
    naam = os.path.basename(file.name)

    omvang = os.path.getsize(file.name)
    bestandsformaat = pronominfo(file.name)
    checksum = create_checksum(file)

    # file or file path?
    if isinstance(isrepresentatievan, (str, Path)) or hasattr(
        isrepresentatievan, "read"
    ):
        informatieobject = helpers.process_file(isrepresentatievan)
        informatieobject.close()
        verwijzing_obj = _detect_verwijzing(informatieobject_file)
    elif isinstance(isrepresentatievan, VerwijzingGegevens):
        verwijzing_informatieobject = isrepresentatievan
    else:
        raise TypeError(
            "isrepresentatievan must either be a path/file, or a VerwijzingGegevens object."
        )

    file.close()

    return Bestand(
        identificatie,
        naam,
        omvang,
        bestandsformaat,
        checksum,
        verwijzing_informatieobject,
        url,
    )


def create_checksum(
    file_or_filename: TextIO | str, algorithm: str = "sha256"
) -> ChecksumGegevens:
    """Convience function for creating ChecksumGegegevens objects.

    Takes a file-like object or path to file, and then generates the requisite
    checksum metadata (i.e.  `checksumAlgoritme`, `checksumWaarde`, and
    `checksumDatum`) from that file.

    Example:

        ```python
        pdf_checksum = create_checksum('document.pdf')
        # create ChecksumGegevens with a 512 bits instead of a 256 bits checksum
        jpg_checksum = create_checksum('scan-003.jpg', algorithm="sha512")
        ```

    Args:
        infile (TextIO | str): file-like object to generate checksum data for
        algorithm (Optional[str]): checksum algorithm to use; defaults to sha256.
         For valid values, see https://docs.python.org/3/library/hashlib.html

    Returns:
        ChecksumGegevens: checksum metadata from `file_or_filename`
    """
    infile = helpers.process_file(file_or_filename)
    verwijzing = VerwijzingGegevens(
        verwijzingNaam="Begrippenlijst ChecksumAlgoritme MDTO"
    )

    checksumAlgoritme = BegripGegevens(
        begripLabel=algorithm.upper().replace("SHA", "SHA-"),
        begripBegrippenlijst=verwijzing,
    )

    # file_digest() expects a file in binary mode, hence `infile.buffer.raw`
    # FIXME: this value is not the same on each call?
    checksumWaarde = hashlib.file_digest(infile.buffer.raw, algorithm).hexdigest()

    checksumDatum = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return ChecksumGegevens(checksumAlgoritme, checksumWaarde, checksumDatum)


def from_xml(mdto_xml: TextIO | str) -> Object:
    """Construct a Informatieobject/Bestand object from a MDTO XML file.

    Note:
        When `xmlfile` is invalid MDTO, this function will probably throw an error.

    Example:

    ```python
    import mdto

    informatieobject = mdto.from_xml("Voorbeeld Archiefstuk Informatieobject.xml")

    # edit the informatie object
    informatieobject.naam = "Verlenen kapvergunning Flipje's Erf 15 Tiel"

    # save it to a new file (or override the original, if desired)
    informatieobject.save("path/to/new/file.xml")
    ```

    Args:
        mdto_xml (TextIO | str): The MDTO XML file to construct an Informatieobject/Bestand from

    Returns:
        Object: A new MDTO object (Bestand or Informatieobject)
    """

    # Parsers:
    def parse_text(node) -> str:
        return node.text

    def parse_int(node) -> int:
        return int(node.text)

    def parse_identificatie(node) -> IdentificatieGegevens:
        return IdentificatieGegevens(
            node[0].text,
            node[1].text,
        )

    # this is measurably faster than the elem_to_mdto variant
    def parse_verwijzing(node) -> VerwijzingGegevens:
        if len(node) == 1:
            return VerwijzingGegevens(node[0].text)
        else:
            return VerwijzingGegevens(
                node[0].text,
                parse_identificatie(node[1]),
            )

    def elem_to_mdto(elem: ET.Element, mdto_class: classmethod, mdto_xml_parsers: dict):
        """Construct MDTO class from given XML element, using parsers specified in
        mdto_xml_parsers.

        Returns:
            MDTO instance: a initialized MDTO instance of type `mdto_class`
        """
        # initialize dictionary of keyword arguments (to be passed to MDTO class constructor)
        constructor_args = {mdto_field: [] for mdto_field in mdto_xml_parsers}

        for child in elem:
            mdto_field = child.tag.removeprefix(
                "{https://www.nationaalarchief.nl/mdto}"
            )
            # retrieve parser
            xml_parser = mdto_xml_parsers[mdto_field]
            # add value of parsed child element to class constructor args
            constructor_args[mdto_field].append(xml_parser(child))

        # cleanup constructor args
        for argname, value in constructor_args.items():
            # Convert empty argument lists into None values
            if len(value) == 0:
                constructor_args[argname] = None
            # Convert one-itemed argument lists to non-lists
            elif len(value) == 1:
                constructor_args[argname] = value[0]

        return mdto_class(**constructor_args)

    begrip_parsers = {
        "begripLabel": parse_text,
        "begripCode": parse_text,
        "begripBegrippenlijst": parse_verwijzing,
    }
    parse_begrip = lambda e: elem_to_mdto(e, BegripGegevens, begrip_parsers)

    termijn_parsers = {
        "termijnTriggerStartLooptijd": parse_begrip,
        "termijnStartdatumLooptijd": parse_text,
        "termijnLooptijd": parse_text,
        "termijnEinddatum": parse_text,
    }
    parse_termijn = lambda e: elem_to_mdto(e, TermijnGegevens, termijn_parsers)

    beperking_parsers = {
        "beperkingGebruikType": parse_begrip,
        "beperkingGebruikNadereBeschrijving": parse_text,
        "beperkingGebruikDocumentatie": parse_verwijzing,
        "beperkingGebruikTermijn": parse_termijn,
    }
    parse_beperking = lambda e: elem_to_mdto(
        e, BeperkingGebruikGegevens, beperking_parsers
    )

    raadpleeglocatie_parsers = {
        "raadpleeglocatieFysiek": parse_verwijzing,
        "raadpleeglocatieOnline": parse_text,
    }
    parse_raadpleeglocatie = lambda e: elem_to_mdto(
        e, RaadpleeglocatieGegevens, raadpleeglocatie_parsers
    )

    dekking_in_tijd_parsers = {
        "dekkingInTijdType": parse_begrip,
        "dekkingInTijdBegindatum": parse_text,
        "dekkingInTijdEinddatum": parse_text,
    }
    parse_dekking_in_tijd = lambda e: elem_to_mdto(
        e, DekkingInTijdGegevens, dekking_in_tijd_parsers
    )

    event_parsers = {
        "eventType": parse_begrip,
        "eventTijd": parse_text,
        "eventVerantwoordelijkeActor": parse_verwijzing,
        "eventResultaat": parse_text,
    }
    parse_event = lambda e: elem_to_mdto(e, EventGegevens, event_parsers)

    gerelateerd_informatieobject_parsers = {
        "gerelateerdInformatieobjectVerwijzing": parse_verwijzing,
        "gerelateerdInformatieobjectTypeRelatie": parse_begrip,
    }
    parse_gerelateerd_informatieobject = lambda e: elem_to_mdto(
        e, GerelateerdInformatieobjectGegevens, gerelateerd_informatieobject_parsers
    )

    betrokkene_parsers = {
        "betrokkeneTypeRelatie": parse_begrip,
        "betrokkeneActor": parse_verwijzing,
    }
    parse_betrokkene = lambda e: elem_to_mdto(e, BetrokkeneGegevens, betrokkene_parsers)

    checksum_parsers = {
        "checksumAlgoritme": parse_begrip,
        "checksumWaarde": parse_text,
        "checksumDatum": parse_text,
    }
    parse_checksum = lambda e: elem_to_mdto(e, ChecksumGegevens, checksum_parsers)

    informatieobject_parsers = {
        "naam": parse_text,
        "identificatie": parse_identificatie,
        "aggregatieniveau": parse_begrip,
        "classificatie": parse_begrip,
        "trefwoord": parse_text,
        "omschrijving": parse_text,
        "raadpleeglocatie": parse_raadpleeglocatie,
        "dekkingInTijd": parse_dekking_in_tijd,
        "dekkingInRuimte": parse_verwijzing,
        "taal": parse_text,
        "event": parse_event,
        "waardering": parse_begrip,
        "bewaartermijn": parse_termijn,
        "informatiecategorie": parse_begrip,
        "isOnderdeelVan": parse_verwijzing,
        "bevatOnderdeel": parse_verwijzing,
        "heeftRepresentatie": parse_verwijzing,
        "aanvullendeMetagegevens": parse_verwijzing,
        "gerelateerdInformatieobject": parse_gerelateerd_informatieobject,
        "archiefvormer": parse_verwijzing,
        "betrokkene": parse_betrokkene,
        "activiteit": parse_verwijzing,
        "beperkingGebruik": parse_beperking,
    }
    parse_informatieobject = lambda e: elem_to_mdto(
        e, Informatieobject, informatieobject_parsers
    )

    bestand_parsers = {
        "naam": parse_text,
        "identificatie": parse_identificatie,
        "omvang": parse_int,
        "checksum": parse_checksum,
        "bestandsformaat": parse_begrip,
        "URLBestand": parse_text,
        "isRepresentatieVan": parse_verwijzing,
    }
    parse_bestand = lambda e: elem_to_mdto(e, Bestand, bestand_parsers)

    # read xmlfile
    tree = ET.parse(mdto_xml)
    root = tree.getroot()
    children = list(root[0])

    # check if object type is Bestand or Informatieobject
    object_type = root[0].tag.removeprefix("{https://www.nationaalarchief.nl/mdto}")

    if object_type == "informatieobject":
        return parse_informatieobject(children)
    elif object_type == "bestand":
        return parse_bestand(children)
    else:
        raise ValueError(
            f"Unexpected first child <{object_type}> in {mdto_xml}: "
            "expected <informatieobject> or <bestand>."
        )
