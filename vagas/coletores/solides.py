"""
Coletor da Sólides Vagas (vagas.solides.com.br).

Técnica: API JSON. A página de busca do próprio site carrega as vagas de
/api/vacancies, então o robô pede os dados direto nesse endereço.

O filtro de cidade da API usa o formato "Cidade - UF". Ela não tem filtro de
trabalho remoto, então pra achar vagas remotas o robô faz uma busca geral
e fica só com as que são remotas.
"""

from __future__ import annotations

import time
from datetime import datetime

from bs4 import BeautifulSoup

from vagas.coletores.base import Coletor
from vagas.modelos import Vaga, detectar_nivel, normalizar

API = "https://vagas.solides.com.br/api/vacancies"
URL_VAGA = "https://vagas.solides.com.br/vaga/{id}"
POR_PAGINA = 20          # a API não aceita mais que 20 por página
PAGINAS_REMOTO = 3       # quantas páginas da busca geral olhar atrás de vagas remotas

MODALIDADES = {"remoto": "remoto", "hibrido": "hibrido", "presencial": "presencial"}
NIVEIS = {
    "estagiario": "estagio", "estagio": "estagio", "trainee": "trainee",
    "junior": "junior", "pleno": "pleno", "senior": "senior", "especialista": "especialista",
}


class ColetorSolides(Coletor):
    nome = "solides"
    pausa_entre_paginas = 1.5

    def __init__(self, cidades: list[str] | None = None, estado: str = "") -> None:
        super().__init__()
        # Sem a UF não dá pra filtrar por cidade, aí só entram as vagas remotas
        self.locais = [f"{c} - {estado}" for c in (cidades or [])] if estado else []

    def coletar_termo(self, termo: str, limite: int) -> list[Vaga]:
        """Busca em cada cidade (até `limite` por cidade) e depois as vagas remotas."""
        vagas: list[Vaga] = []
        for local in self.locais:
            vagas += self._buscar(termo, local, limite)
        vagas += [v for v in self._buscar(termo, "", POR_PAGINA * PAGINAS_REMOTO)
                  if v.modalidade == "remoto"]
        return vagas

    def _buscar(self, termo: str, local: str, limite: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        pagina = 1
        while len(vagas) < limite:
            dados = self.get(API, params={"page": pagina, "take": POR_PAGINA,
                                          "title": termo, "locations": local}).json()
            itens = dados.get("data") or []
            vagas += [converter(i) for i in itens if not i.get("isHiddenJob") and not i.get("isDisabled")]
            if not itens or pagina >= (dados.get("totalPages") or 0):
                break
            pagina += 1
            time.sleep(self.pausa_entre_paginas)
        return vagas[:limite]


def converter(item: dict) -> Vaga:
    """Transforma um item da API da Sólides numa Vaga."""
    titulo = (item.get("title") or "").strip()
    modalidade = MODALIDADES.get(item.get("jobType") or "", "")
    if item.get("homeOffice"):
        modalidade = "remoto"

    cidade = (item.get("city") or {}).get("name") or ""
    uf = (item.get("state") or {}).get("code") or ""
    local = ", ".join(p for p in [cidade, uf] if p) or ("Remoto" if modalidade == "remoto" else "")

    nivel = ""
    for s in item.get("seniority") or []:
        nivel = NIVEIS.get(normalizar(s.get("name") or ""), "")
        if nivel:
            break

    publicada = None
    if item.get("createdAt"):
        try:
            publicada = datetime.fromisoformat(item["createdAt"][:10])
        except ValueError:
            pass

    descricao = BeautifulSoup(item.get("description") or "", "html.parser").get_text(" ", strip=True)

    return Vaga(
        fonte="solides",
        id_externo=str(item.get("id")),
        titulo=titulo,
        empresa=(item.get("companyName") or "").strip(),
        url=URL_VAGA.format(id=item.get("id")),
        local=local,
        modalidade=modalidade,
        nivel=nivel or detectar_nivel(titulo),
        salario=salario(item.get("salary") or {}),
        descricao=descricao[:4000],
        tags=[h["name"].strip() for h in item.get("hardSkills") or [] if (h.get("name") or "").strip()],
        publicada_em=publicada,
    )


def salario(dados: dict) -> str:
    """Monta o texto do salário só quando a empresa mostra a faixa."""
    if not dados.get("showRangeToApplicant"):
        return ""
    de, ate = dados.get("initialRange") or 0, dados.get("finalRange") or 0

    def reais(valor: float) -> str:
        return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if de and ate and de != ate:
        return f"{reais(de)} a {reais(ate)}"
    if ate:
        return f"Até {reais(ate)}"
    if de:
        return f"A partir de {reais(de)}"
    return ""
