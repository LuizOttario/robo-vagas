"""Base comum para todos os coletores de vagas."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import requests

from vagas.modelos import Vaga

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class Coletor(ABC):
    """
    Cada site tem um coletor próprio que herda desta classe.
    Pra adicionar um site novo é só criar uma classe com `nome` e `coletar_termo`.
    """

    nome: str = ""
    pausa_entre_paginas = 1.0  # segundos; evita sobrecarregar o site

    def __init__(self) -> None:
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})

    @abstractmethod
    def coletar_termo(self, termo: str, limite: int) -> list[Vaga]:
        """Busca as vagas de um termo e devolve no máximo `limite` vagas."""

    def coletar(self, termos: list[str], limite: int) -> list[Vaga]:
        """Busca todos os termos. Se um termo falhar, os outros continuam."""
        encontradas: dict[str, Vaga] = {}
        for termo in termos:
            try:
                vagas = self.coletar_termo(termo, limite)
                for vaga in vagas:
                    encontradas.setdefault(vaga.id, vaga)  # sem repetir
                log.info("%s: %d vagas para '%s'", self.nome, len(vagas), termo)
            except Exception as erro:
                log.warning("%s: falhou ao buscar '%s' (%s: %s)",
                            self.nome, termo, type(erro).__name__, erro)
            time.sleep(self.pausa_entre_paginas)
        return list(encontradas.values())

    def fechar(self) -> None:
        self.sessao.close()

    def get(self, url: str, **kwargs) -> requests.Response:
        resposta = self.sessao.get(url, timeout=30, **kwargs)
        resposta.raise_for_status()
        return resposta
