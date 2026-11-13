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
