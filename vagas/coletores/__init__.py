"""Coletores de vagas. Cada site usa uma técnica diferente:

- gupy:          API JSON (requests)
- vagas_com:     navegador automatizado (Selenium / RPA)
- programathor:  leitura de HTML (requests + BeautifulSoup)
"""

from vagas.coletores.base import Coletor
from vagas.coletores.gupy import ColetorGupy
from vagas.coletores.programathor import ColetorProgramaThor
from vagas.coletores.vagas_com import ColetorVagasCom

DISPONIVEIS = {
    "gupy": ColetorGupy,
    "vagas_com": ColetorVagasCom,
    "programathor": ColetorProgramaThor,
}


def criar(nome: str, mostrar_navegador: bool = False) -> Coletor:
    if nome not in DISPONIVEIS:
        raise ValueError(f"Fonte desconhecida: {nome}. Opções: {', '.join(DISPONIVEIS)}")
    if nome == "vagas_com":
        return ColetorVagasCom(mostrar_navegador=mostrar_navegador)
    return DISPONIVEIS[nome]()
