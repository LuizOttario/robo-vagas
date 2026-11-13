from vagas.modelos import Vaga
from vagas.pontuacao import contem, pontuar


def test_contem_usa_palavra_inteira():
    assert contem("experiencia com sql server", "SQL")
    assert not contem("mysqlx", "sql")
    assert contem("c# e .net", "C#")


def test_vaga_ideal_tira_nota_maxima(vaga_boa, config):
    pontuar(vaga_boa, config)
    assert vaga_boa.nota == 100
    assert any("habilidades" in m for m in vaga_boa.motivos)


def test_vaga_ruim_tira_zero(vaga_ruim, config):
    pontuar(vaga_ruim, config)
    assert vaga_ruim.nota == 0
    assert any("inglês fluente" in m for m in vaga_ruim.motivos)


def test_cidade_do_perfil_conta_pontos(config):
    vaga = Vaga(fonte="x", id_externo="1", titulo="Analista", empresa="", url="",
                local="São Paulo / SP", modalidade="presencial")
    pontuar(vaga, config)
    assert any("na sua cidade" in m for m in vaga.motivos)


def test_hibrido_fora_da_preferencia_nao_conta(config):
    config.aceita_hibrido = False
    vaga = Vaga(fonte="x", id_externo="1", titulo="Analista", empresa="", url="",
                local="São Paulo", modalidade="hibrido")
    pontuar(vaga, config)
    assert any("fora da sua região" in m for m in vaga.motivos)


def test_nota_fica_entre_0_e_100(config):
    config.palavras_evitar = ["java", "spring", "senior"]
    vaga = Vaga(fonte="x", id_externo="1", titulo="Java Spring Senior", empresa="", url="",
                nivel="senior", modalidade="presencial", local="Longe")
    assert pontuar(vaga, config).nota == 0
