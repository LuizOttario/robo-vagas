import tomllib

from vagas.config import carregar
from vagas.curriculo import extrair_perfil, salvar_perfil

CURRICULO = """
MARIA SOUZA
Belo Horizonte - MG | (31) 99999-0000
Objetivo: Assistente Administrativo
Experiência: Auxiliar Administrativo na Empresa X (2021 - 2024)
Rotinas de contas a pagar, emissão de notas fiscais e controle de estoque.
Conhecimentos: Excel avançado, Word, sistema TOTVS. Domínio do pacote Office.
"""


def test_extrai_cargos_habilidades_e_cidade():
    p = extrair_perfil(CURRICULO)
    assert p["termos"] == ["assistente administrativo", "auxiliar administrativo"]
    for h in ["excel", "excel avançado", "word", "pacote office", "contas a pagar",
              "controle de estoque", "totvs"]:
        assert h in p["habilidades"]
    assert p["cidades"] == ["Belo Horizonte"]
    assert p["estado"] == "MG"


def test_departamento_pessoal_nao_repete_dentro_do_cargo():
    p = extrair_perfil("Assistente de Departamento Pessoal")
    assert p["termos"] == ["assistente de departamento pessoal"]


def test_curriculo_sem_nada_conhecido():
    assert extrair_perfil("texto qualquer") == {"termos": [], "habilidades": [], "cidades": [], "estado": ""}


def test_salvar_perfil_gera_config_que_o_robo_le(tmp_path):
    destino = tmp_path / "config.toml"
    salvar_perfil({"termos": ["assistente administrativo"], "habilidades": ["excel", "contas a pagar"],
                   "cidades": ["Contagem"], "estado": "MG", "niveis_desejados": ["junior", "pleno"]}, destino)
    tomllib.loads(destino.read_text(encoding="utf-8"))  # TOML válido
    c = carregar(destino)
    assert c.termos == ["assistente administrativo"]
    assert c.fontes == ["gupy", "solides", "programathor"]
    assert c.habilidades == ["excel", "contas a pagar"]
    assert (c.cidades, c.estado, c.niveis_desejados) == (["Contagem"], "MG", ["junior", "pleno"])
