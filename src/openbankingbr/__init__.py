# -*- coding: utf-8 -*-

"""
OpenBankingBR 
~~~~~~~~~~~~~

Biblioteca para o consumo dos dados publicos do Open Banking Brasil.

Exemplo de uso:
```python
import openbankingbr as obr

```

:copyright: (c) 2021 by Gustavo J Knuppe.

:license: MIT.
"""

from .errors import (
    OpenBankingException,
    InvalidDataException,
)

from .__version__ import (
    __author__,
    __copyright__,
    __description__,
    __title__,
    __license__,
    __url__,
    __version__,
)

from .models import Participante
from .utils import fetchUrl

from typing import List

class OpenBankingBR():
    """
    Classe primária que possibilita listar todos os participantes cadastrados
    no diretório do OpenBanking Brasil.

    Exemplo:
    ```python
    ob = OpenBankingBR(cacheDir = './cache')
    for participante in ob.participantes:
        print(participante.nome)

    ```    
    """
    def __init__(self, cacheDir: str = None):
        self.cacheDir = cacheDir

    @property
    def participantes(self):
        """
        Gera uma lista com os participantes cadastrados no diretório do Open Banking Brasil.

        https://openbanking-brasil.github.io/areadesenvolvedor/#participantes-open-banking-brasil
        """
        
        data = fetchUrl('https://data.directory.openbankingbrasil.org.br/participants', self.cacheDir)
        if data == None:
            raise OpenBankingException("Não possível obter a lista de participantes do diretório oficial") from None
        elif not type(data) == list:
            raise InvalidDataException("Os dados retornados da lista de participantes não são válidos") from None

        for p in data:
            yield Participante(self, p)
    
    def busca_participante(
        self,
        cnpj: int = None,
        dominio: str = None,
        identificador: str = None,
        ):
        """
        Busca um participante utilizando apenas UM critério de pesquisa definido nos argumentos.

        > `cnpj` é o campo numérico tratado, originado do `RegistrationNumber`.

        > `dominio` é o dominio web, ex: `bcb.gov.br`

        > `identificador` é o identificador do participante `OrganisationId`.

        """
        for participante in self.participantes:
            if cnpj != None and participante.cnpj == cnpj:
                return participante
            elif identificador != None and participante.identificador:
                return participante
            elif dominio != None:
                for ep in participante.apiEndPoints:
                    if dominio in ep:
                        return participante
        
        return None

__all__ = [
    "batch",
    "errors",
    "models",
    "OpenBankingBR",
]