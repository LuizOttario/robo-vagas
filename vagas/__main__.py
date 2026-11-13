"""
Linha de comando do Robô de Vagas.

    python -m vagas coletar        busca vagas novas, dá nota, salva e avisa
    python -m vagas relatorio      gera o Excel com todas as vagas
    python -m vagas painel         abre o painel web no navegador
    python -m vagas repontuar      recalcula as notas (use depois de mudar seu perfil)
    python -m vagas status ID STATUS   muda o status de uma vaga

Use --help em qualquer comando pra ver as opções.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd

from vagas import coletores, notificacao, relatorio
from vagas.banco import Banco
from vagas.config import PASTA_PROJETO, Config, carregar
from vagas.modelos import STATUS, Vaga
from vagas.pontuacao import pontuar

log = logging.getLogger("vagas")


def configurar_log(config: Config, detalhado: bool) -> None:
    config.banco.parent.mkdir(parents=True, exist_ok=True)
    formato = "%(asctime)s %(levelname)-7s %(message)s"
    logging.basicConfig(
        level=logging.DEBUG if detalhado else logging.INFO,
        format=formato, datefmt="%d/%m %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(config.banco.parent / "robo.log", encoding="utf-8")],
    )
    # Bibliotecas externas falam demais; mostra só avisos delas
    for barulhenta in ["selenium", "urllib3", "WDM"]:
        logging.getLogger(barulhenta).setLevel(logging.WARNING)


# --------------------------------------------------------------------- coletar

def cmd_coletar(args, config: Config) -> int:
    fontes = args.fontes or config.fontes
    termos = args.termos or config.termos
    if args.ver:
        config.mostrar_navegador = True

    with Banco(config.banco) as banco:
        id_exec = banco.iniciar_execucao()
        todas: list[Vaga] = []
        erros: list[str] = []

        for nome in fontes:
            log.info("Buscando no %s: %s", nome, ", ".join(termos))
            try:
                coletor = coletores.criar(nome, config.mostrar_navegador)
            except ValueError as erro:
                erros.append(str(erro))
                log.error(erro)
                continue
            try:
                todas += coletor.coletar(termos, config.max_por_termo)
            except Exception as erro:
                erros.append(f"{nome}: {erro}")
                log.error("%s falhou: %s", nome, erro)
            finally:
                coletor.fechar()

        for vaga in todas:
            pontuar(vaga, config)
        novas = banco.salvar(todas)
        log.info("Total: %d vagas encontradas, %d novas", len(todas), len(novas))

        if novas:
            print("\nMelhores vagas novas:")
            for v in sorted(novas, key=lambda v: v.nota, reverse=True)[:10]:
                print(f"  [{v.nota:3d}] {v.titulo[:60]:60s} {v.empresa[:25]}")
            print()

        if not args.sem_alerta:
            alertar(banco, config)

        banco.finalizar_execucao(id_exec, len(todas), len(novas), erros)
    return 0 if todas or not erros else 1


def alertar(banco: Banco, config: Config) -> None:
    pendentes = banco.para_notificar(config.nota_minima_alerta)
    if not pendentes:
        log.info("Nenhuma vaga nova acima da nota %d", config.nota_minima_alerta)
        return
    if not (config.email.get("ativo") or config.telegram.get("ativo")):
        log.info("%d vaga(s) com nota >= %d. Ligue e-mail ou Telegram no config.toml pra receber aviso.",
                 len(pendentes), config.nota_minima_alerta)
        return

    anexo = relatorio.gerar(banco.tabela(), config.pasta_relatorios) if config.email.get("ativo") else None
    if notificacao.notificar(pendentes, config, anexo):
        banco.marcar_notificadas([v["id"] for v in pendentes])


# ------------------------------------------------------------- outros comandos

def cmd_relatorio(args, config: Config) -> int:
    with Banco(config.banco) as banco:
        df = banco.tabela()
    if args.nota_minima:
        df = df[df["nota"] >= args.nota_minima]
    arquivo = relatorio.gerar(df, config.pasta_relatorios)
    log.info("Relatório com %d vagas salvo em %s", len(df), arquivo)
    return 0


def cmd_repontuar(args, config: Config) -> int:
    with Banco(config.banco) as banco:
        df = banco.tabela()
        vagas = []
        for _, linha in df.iterrows():
            v = Vaga(fonte=linha["fonte"], id_externo=linha["id_externo"], titulo=linha["titulo"],
                     empresa=linha["empresa"], url=linha["url"], local=linha["local"] or "",
                     modalidade=linha["modalidade"] or "", nivel=linha["nivel"] or "",
                     salario=linha["salario"] or "", descricao=linha["descricao"] or "",
                     tags=linha["tags"],
                     publicada_em=linha["publicada_em"].to_pydatetime() if pd.notna(linha["publicada_em"]) else None)
            vagas.append(pontuar(v, config))
        banco.salvar(vagas)
    log.info("Notas recalculadas para %d vagas", len(vagas))
    return 0


def cmd_status(args, config: Config) -> int:
    with Banco(config.banco) as banco:
        banco.mudar_status(args.id, args.status)
    log.info("Vaga %s marcada como '%s'", args.id, args.status)
    return 0


def cmd_painel(args, config: Config) -> int:
    painel = PASTA_PROJETO / "painel.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(painel),
                            "--server.port", str(args.porta), "--browser.gatherUsageStats", "false"])


# ------------------------------------------------------------------------ main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m vagas", description="Robô de Vagas")
    parser.add_argument("--config", type=Path, help="caminho do config.toml")
    parser.add_argument("-v", "--detalhado", action="store_true", help="mostra mais mensagens")
    sub = parser.add_subparsers(dest="comando")

    p = sub.add_parser("coletar", help="busca vagas novas")
    p.add_argument("--fontes", nargs="+", choices=list(coletores.DISPONIVEIS), help="sites a usar")
    p.add_argument("--termos", nargs="+", help="palavras a pesquisar")
    p.add_argument("--ver", action="store_true", help="mostra o Chrome trabalhando")
    p.add_argument("--sem-alerta", action="store_true", help="não manda e-mail/Telegram")
    p.set_defaults(func=cmd_coletar)

    p = sub.add_parser("relatorio", help="gera o Excel")
    p.add_argument("--nota-minima", type=int, default=0)
    p.set_defaults(func=cmd_relatorio)

    p = sub.add_parser("painel", help="abre o painel web")
    p.add_argument("--porta", type=int, default=8501)
    p.set_defaults(func=cmd_painel)

    p = sub.add_parser("repontuar", help="recalcula as notas")
    p.set_defaults(func=cmd_repontuar)

    p = sub.add_parser("status", help="muda o status de uma vaga")
    p.add_argument("id", help="id da vaga, ex.: gupy:123456")
    p.add_argument("status", choices=STATUS)
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    if not args.comando:
        parser.print_help()
        return 0

    config = carregar(args.config)
    configurar_log(config, args.detalhado)
    return args.func(args, config)


if __name__ == "__main__":
    sys.exit(main())
