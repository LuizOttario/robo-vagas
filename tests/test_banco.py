import pytest

from vagas.banco import Banco
from vagas.pontuacao import pontuar


def test_salvar_devolve_so_as_novas(config, vaga_boa, vaga_ruim):
    with Banco(config.banco) as banco:
        assert len(banco.salvar([vaga_boa, vaga_ruim])) == 2
        assert banco.salvar([vaga_boa]) == []  # já existia
        assert len(banco.tabela()) == 2


def test_atualizar_mantem_status(config, vaga_boa):
    with Banco(config.banco) as banco:
        banco.salvar([vaga_boa])
        banco.mudar_status(vaga_boa.id, "candidatei")
        vaga_boa.titulo = "Título novo"
        banco.salvar([vaga_boa])
        linha = banco.tabela().iloc[0]
        assert linha["status"] == "candidatei"
        assert linha["titulo"] == "Título novo"


def test_notificacao_so_uma_vez(config, vaga_boa, vaga_ruim):
    pontuar(vaga_boa, config)
    pontuar(vaga_ruim, config)
    with Banco(config.banco) as banco:
        banco.salvar([vaga_boa, vaga_ruim])
        pendentes = banco.para_notificar(60)
        assert [v["id"] for v in pendentes] == [vaga_boa.id]
        banco.marcar_notificadas([vaga_boa.id])
        assert banco.para_notificar(60) == []


def test_status_invalido(config, vaga_boa):
    with Banco(config.banco) as banco:
        banco.salvar([vaga_boa])
        with pytest.raises(ValueError):
            banco.mudar_status(vaga_boa.id, "contratado")


def test_execucoes(config):
    with Banco(config.banco) as banco:
        id_exec = banco.iniciar_execucao()
        banco.finalizar_execucao(id_exec, 10, 3, ["gupy: erro"])
        linha = banco.execucoes().iloc[0]
        assert (linha["encontradas"], linha["novas"], linha["erros"]) == (10, 3, "gupy: erro")


def test_mudar_status_de_vaga_que_nao_existe(tmp_path):
    with Banco(tmp_path / "v.db") as banco:
        assert banco.mudar_status("gupy:000", "candidatei") is False
