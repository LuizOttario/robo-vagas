"""Coletores de vagas. Cada site usa uma técnica diferente:

- gupy:          API JSON (requests)
- vagas_com:     navegador automatizado (Selenium / RPA)
- programathor:  leitura de HTML (requests + BeautifulSoup)
- solides:       API JSON, filtrando por cidade
"""

from vagas.coletores.base import Coletor
from vagas.coletores.gupy import ColetorGupy
from vagas.coletores.programathor import ColetorProgramaThor
from vagas.coletores.solides import ColetorSolides
from vagas.coletores.vagas_com import ColetorVagasCom

DISPONIVEIS = {
    "gupy": ColetorGupy,
    "vagas_com": ColetorVagasCom,
    "programathor": ColetorProgramaThor,
    "solides": ColetorSolides,
}


def criar(nome: str, mostrar_navegador: bool = False,
          cidades: list[str] | None = None, estado: str = "") -> Coletor:
    if nome not in DISPONIVEIS:
        raise ValueError(f"Fonte desconhecida: {nome}. Opções: {', '.join(DISPONIVEIS)}")
    if nome == "vagas_com":
        return ColetorVagasCom(mostrar_navegador=mostrar_navegador)
    if nome == "solides":
        return ColetorSolides(cidades=cidades, estado=estado)
    return DISPONIVEIS[nome]()
