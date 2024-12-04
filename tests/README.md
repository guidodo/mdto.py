Deze tests valideren de werking van deze library door naar drie dingen te kijken:

1. Is de geproduceerde XML output valide volgens de MDTO XSD?
2. Kunnen alle MDTO voorbeeldbestanden correct worden ingelezen?
2. Kunnen de MDTO voorbeeldbestanden zonder informatieverlies weer worden teruggeschreven?

# Test afhankelijkheden

[`pytest`](https://pypi.org/project/pytest/) en de afhankelijkheden van `mdto.py` zijn genoeg om alle tests uit te voeren. Aangezien de tests de MDTO voorbeeldbestanden en XSD moeten kunnen downloaden, heb je een werkende internetverbinding om de tests te kunnen uitvoeren.

# Het uitvoeren van de tests

``` shellsession
$ cd projecten/mdto # move into project dir
$ paru -S pytest # adapt to your operating system/preferences
$ pip install .
$ pytest
```
