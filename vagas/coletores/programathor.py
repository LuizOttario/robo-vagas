"""
Coletor do ProgramaThor (programathor.com.br).

Técnica: baixa o HTML da página com `requests` e lê com BeautifulSoup.
Não precisa de navegador porque as vagas já vêm prontas no HTML.
"""

from __future__ import annotations

import re
import time

from bs4 import BeautifulSoup

from vagas.coletores.base import Coletor
from vagas.modelos import Vaga, detectar_modalidade, detectar_nivel

SITE = "https://programathor.com.br"
POR_PAGINA = 15  # quantas vagas o site mostra por página
MAX_PAGINAS = 10


class ColetorProgramaThor(Coletor):
    nome = "programathor"

    def coletar_termo(self, termo: str, limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        for pagina in range(1, MAX_PAGINAS + 1):
            html = self.get(f"{SITE}/jobs", params={"search": termo, "page": pagina}).text
            novas = ler_pagina(html)
            vagas += novas
            if len(novas) < POR_PAGINA or len(vagas) >= limite:
                break
            time.sleep(self.pausa_entre_paginas)
        return vagas[:limite]


# O site usa um ícone diferente pra cada informação da vaga
ICONES = {
    "fa-briefcase": "empresa",
    "fa-map-marker-alt": "local",
    "fa-chart-bar": "nivel",
    "fa-money-bill-alt": "salario",
    "fa-file-alt": "contrato",
}


def ler_pagina(html: str) -> list[Vaga]:
    sopa = BeautifulSoup(html, "html.parser")
    vagas = []
    for card in sopa.select("div.cell-list"):
        link = card.select_one('a[href^="/jobs/"]')
        titulo_tag = card.select_one("h3")
        if not link or not titulo_tag:
            continue  # cartão de propaganda, não é vaga

        # Tira os selos "NOVA" e "Vencida" do título
        for selo in titulo_tag.select("span"):
            selo.decompose()
        titulo = re.sub(r"\s+", " ", titulo_tag.get_text(" ", strip=True))
        titulo = re.sub(r"^\W*PRESENCIAL - SOMENTE PARA CANDIDATOS NO LOCAL\s*", "", titulo)

        info = {}
        for span in card.select(".cell-list-content-icon span"):
            icone = span.find("i")
            classes = icone.get("class", []) if icone else []
            for classe, campo in ICONES.items():
                if classe in classes:
                    info[campo] = span.get_text(" ", strip=True)

        local = re.sub(r"\s+", " ", info.get("local", ""))
        id_externo = link["href"].split("/")[2].split("-")[0]
        tags = [t.get_text(strip=True) for t in card.select(".tag-list")]

        vagas.append(Vaga(
            fonte="programathor",
            id_externo=id_externo,
            titulo=titulo,
            empresa=info.get("empresa", ""),
            url=SITE + link["href"],
            local=re.sub(r"\s*\((Presencial|Híbrido|Remoto)\)", "", local).strip(),
            modalidade=detectar_modalidade(local),
            nivel=detectar_nivel(info.get("nivel", "")) or detectar_nivel(titulo),
            salario=info.get("salario", ""),
            descricao=f"{titulo}. Contrato: {info.get('contrato', '')}",
            tags=tags,
        ))
    return vagas
