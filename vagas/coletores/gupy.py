"""
Coletor do Gupy (portal.gupy.io).

Técnica: API JSON. O próprio site do Gupy busca as vagas nesse endereço,
então em vez de abrir o navegador o robô pede os dados direto, o que é
bem mais rápido.
"""

from __future__ import annotations

import time
from datetime import datetime

from vagas.coletores.base import Coletor
from vagas.modelos import Vaga, detectar_nivel

API = "https://portal.gupy.io/api/job-search/jobs"
POR_PAGINA = 20

MODALIDADES = {"remote": "remoto", "hybrid": "hibrido", "on-site": "presencial"}
TIPOS = {
    "vacancy_type_internship": "estagio",
    "vacancy_type_trainee": "trainee",
    "vacancy_type_apprentice": "estagio",
    "vacancy_type_junior": "junior",
}


class ColetorGupy(Coletor):
    nome = "gupy"

    def coletar_termo(self, termo: str, limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        offset = 0
        while len(vagas) < limite:
            dados = self.get(API, params={"jobName": termo, "limit": POR_PAGINA, "offset": offset}).json()
            itens = dados.get("data", [])
            vagas += [converter(item) for item in itens]
            offset += POR_PAGINA
            total = dados.get("pagination", {}).get("total", 0)
            if not itens or offset >= total:
                break
            time.sleep(self.pausa_entre_paginas)
        return vagas[:limite]


def converter(item: dict) -> Vaga:
    """Transforma um item da API do Gupy numa Vaga."""
    cidade = ", ".join(p for p in [item.get("city"), item.get("state")] if p)
    modalidade = MODALIDADES.get(item.get("workplaceType") or "", "")
    titulo = (item.get("name") or "").strip()

    publicada = None
    if item.get("publishedDate"):
        try:
            publicada = datetime.fromisoformat(item["publishedDate"].replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass

    return Vaga(
        fonte="gupy",
        id_externo=str(item.get("id")),
        titulo=titulo,
        empresa=(item.get("careerPageName") or "").strip(),
        url=item.get("jobUrl") or "",
        local=cidade or ("Remoto" if modalidade == "remoto" else ""),
        modalidade=modalidade,
        nivel=TIPOS.get(item.get("type") or "") or detectar_nivel(titulo),
        descricao=(item.get("description") or "")[:4000],
        publicada_em=publicada,
    )
