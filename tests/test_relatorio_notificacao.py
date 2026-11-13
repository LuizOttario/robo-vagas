from openpyxl import load_workbook

from vagas import notificacao, relatorio
from vagas.banco import Banco
from vagas.pontuacao import pontuar


def test_relatorio_excel(config, vaga_boa, vaga_ruim):
    with Banco(config.banco) as banco:
        banco.salvar([pontuar(vaga_boa, config), pontuar(vaga_ruim, config)])
        df = banco.tabela()
    arquivo = relatorio.gerar(df, config.pasta_relatorios, "teste.xlsx")

    wb = load_workbook(arquivo)
    assert wb.sheetnames == ["Vagas", "Resumo", "Gráficos"]
    aba = wb["Vagas"]
    assert aba.max_row == 3                       # cabeçalho + 2 vagas
    assert aba["A2"].value == 100                 # ordenado pela nota
    assert aba["L2"].hyperlink.target == vaga_boa.url
    assert len(wb["Gráficos"]._charts) == 3


def test_relatorio_vazio_nao_quebra(config):
    with Banco(config.banco) as banco:
        df = banco.tabela()
    assert relatorio.gerar(df, config.pasta_relatorios, "vazio.xlsx").exists()


def test_contar_tecnologias(config, vaga_boa):
    with Banco(config.banco) as banco:
        banco.salvar([vaga_boa])
        df = banco.tabela()
    contagem = relatorio.contar_tecnologias(df)
    assert contagem["Python"] == 1 and contagem["Selenium"] == 1 and contagem["Java"] == 0


def test_telegram_envia_mensagem(config, vaga_boa, monkeypatch):
    enviados = []

    class RespostaFalsa:
        def raise_for_status(self):
            pass

    def post_falso(url, data, timeout):
        enviados.append((url, data))
        return RespostaFalsa()

    monkeypatch.setattr(notificacao.requests, "post", post_falso)
    config.telegram = {"ativo": True, "token": "ABC", "chat_id": "42"}
    with Banco(config.banco) as banco:
        banco.salvar([pontuar(vaga_boa, config)])
        vagas = banco.para_notificar(0)

    assert notificacao.notificar(vagas, config)
    url, dados = enviados[0]
    assert url.endswith("/botABC/sendMessage")
    assert dados["chat_id"] == "42"
    assert "Desenvolvedor Python Júnior" in dados["text"]


def test_sem_canal_ligado_nao_envia(config, vaga_boa):
    with Banco(config.banco) as banco:
        banco.salvar([vaga_boa])
        assert notificacao.notificar(banco.para_notificar(0), config) is False
