"""Testa a leitura dos dados de cada site sem acessar a internet."""

from vagas.coletores.gupy import converter
from vagas.coletores.programathor import ler_pagina
from vagas.coletores.vagas_com import slug

HTML_PROGRAMATHOR = """
<div class="cell-list ">
  <a href="/jobs/12345-desenvolvedor-python-junior">
    <h3>Desenvolvedor Python Júnior <span class="new-badge">NOVA</span></h3>
    <div class="cell-list-content-icon">
      <span><i class="fa fa-briefcase"></i>Empresa Exemplo</span>
      <span><i class="fas fa-map-marker-alt"></i>São Paulo  (Híbrido)</span>
      <span><i class="far fa-money-bill-alt"></i>Até R$5.000</span>
      <span><i class="far fa-chart-bar"></i>Júnior</span>
      <span><i class="far fa-file-alt"></i>CLT</span>
    </div>
    <div><span class="tag-list">Python</span><span class="tag-list">SQL</span></div>
  </a>
</div>
<div class="cell-list min-height-180"><div>Propaganda</div></div>
"""


def test_programathor_le_cartao_e_ignora_propaganda():
    vagas = ler_pagina(HTML_PROGRAMATHOR)
    assert len(vagas) == 1
    v = vagas[0]
    assert v.id == "programathor:12345"
    assert v.titulo == "Desenvolvedor Python Júnior"
    assert v.empresa == "Empresa Exemplo"
    assert v.local == "São Paulo"
    assert v.modalidade == "hibrido"
    assert v.nivel == "junior"
    assert v.salario == "Até R$5.000"
    assert v.tags == ["Python", "SQL"]
    assert v.url == "https://programathor.com.br/jobs/12345-desenvolvedor-python-junior"


def test_gupy_converte_item_da_api():
    v = converter({
        "id": 999, "name": "Estágio em Automação", "careerPageName": "Empresa",
        "city": "Campinas", "state": "São Paulo", "workplaceType": "hybrid",
        "type": "vacancy_type_internship", "jobUrl": "https://empresa.gupy.io/job/999",
        "publishedDate": "2026-11-10T12:00:00.000Z", "description": "Python e Excel",
    })
    assert v.id == "gupy:999"
    assert v.local == "Campinas, São Paulo"
    assert v.modalidade == "hibrido"
    assert v.nivel == "estagio"
    assert v.publicada_em.year == 2026


def test_gupy_remoto_sem_cidade():
    v = converter({"id": 1, "name": "Dev Python Jr", "workplaceType": "remote", "type": "vacancy_type_effective"})
    assert v.local == "Remoto"
    assert v.nivel == "junior"


def test_slug_da_url_do_vagas_com():
    assert slug("Automação Python") == "automacao-python"
    assert slug("  C# / .NET ") == "c-net"


ITEM_SOLIDES = {
    "id": 952820, "title": "Analista de Suporte Júnior", "companyName": "Empresa Exemplo",
    "description": "<p>Suporte <b>N1 e N2</b> com Active Directory.</p>",
    "city": {"name": "Belo Horizonte"}, "state": {"code": "MG"},
    "jobType": "hibrido", "homeOffice": False,
    "seniority": [{"name": "Júnior"}],
    "salary": {"showRangeToApplicant": True, "initialRange": 3000, "finalRange": 4300.5},
    "hardSkills": [{"name": " Active Directory "}, {"name": "Windows"}],
    "createdAt": "2026-11-13", "isHiddenJob": False, "isDisabled": False,
}


def test_solides_converte_item_da_api():
    from vagas.coletores.solides import converter
    v = converter(ITEM_SOLIDES)
    assert v.id == "solides:952820"
    assert v.url == "https://vagas.solides.com.br/vaga/952820"
    assert v.local == "Belo Horizonte, MG"
    assert v.modalidade == "hibrido"
    assert v.nivel == "junior"
    assert v.salario == "R$ 3.000,00 a R$ 4.300,50"
    assert v.tags == ["Active Directory", "Windows"]
    assert v.descricao == "Suporte N1 e N2 com Active Directory."
    assert v.publicada_em.day == 13


def test_solides_home_office_sem_cidade_vira_remoto():
    from vagas.coletores.solides import converter
    v = converter({"id": 1, "title": "Dev Python Pleno", "jobType": "presencial", "homeOffice": True,
                   "salary": {"showRangeToApplicant": False, "finalRange": 9000}})
    assert v.modalidade == "remoto"
    assert v.local == "Remoto"
    assert v.nivel == "pleno"      # veio do título
    assert v.salario == ""         # empresa escondeu a faixa


def test_solides_monta_filtro_de_cidade_com_uf():
    from vagas.coletores.solides import ColetorSolides
    assert ColetorSolides(["Contagem", "Betim"], "MG").locais == ["Contagem - MG", "Betim - MG"]
    assert ColetorSolides(["Contagem"], "").locais == []   # sem UF não filtra por cidade


def test_solides_busca_cidades_e_so_remotas_na_busca_geral(monkeypatch):
    from vagas.coletores import solides

    remota = dict(ITEM_SOLIDES, id=2, jobType="remoto", city=None, state=None)
    presencial_longe = dict(ITEM_SOLIDES, id=3, jobType="presencial", city={"name": "Manaus"})
    pedidos = []

    class Resposta:
        def __init__(self, dados): self.dados = dados
        def json(self): return self.dados

    def falso_get(self, url, params=None):
        pedidos.append(params["locations"])
        if params["locations"]:
            return Resposta({"totalPages": 1, "data": [ITEM_SOLIDES]})
        return Resposta({"totalPages": 1, "data": [remota, presencial_longe]})

    monkeypatch.setattr(solides.ColetorSolides, "get", falso_get)
    vagas = solides.ColetorSolides(["Belo Horizonte"], "MG").coletar_termo("suporte", 10)
    assert pedidos == ["Belo Horizonte - MG", ""]
    assert sorted(v.id_externo for v in vagas) == ["2", "952820"]
