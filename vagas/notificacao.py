"""Avisos de vagas boas por e-mail e Telegram."""

from __future__ import annotations

import html
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from vagas.config import Config

log = logging.getLogger(__name__)

TELEGRAM_LIMITE = 4000  # o Telegram aceita até 4096 caracteres por mensagem


def montar_texto(vagas: list) -> str:
    linhas = [f"{len(vagas)} vaga(s) nova(s) com boa nota:", ""]
    for v in vagas:
        local = " / ".join(p for p in [v["modalidade"], v["local"]] if p)
        linhas += [f"[{v['nota']}] {v['titulo']}",
                   f"     {v['empresa']} | {v['nivel'] or 'nível não informado'} | {local}",
                   f"     {v['url']}", ""]
    return "\n".join(linhas)


def enviar_email(vagas: list, config: Config, anexo: Path | None = None) -> bool:
    cfg = config.email
    if not cfg.get("ativo"):
        return False

    msg = EmailMessage()
    msg["From"] = cfg["usuario"]
    msg["To"] = cfg["destinatario"]
    msg["Subject"] = f"Robô de Vagas: {len(vagas)} vaga(s) nova(s) pra você"
    msg.set_content(montar_texto(vagas) + "\n-- Robô de Vagas")

    if anexo and anexo.exists():
        msg.add_attachment(anexo.read_bytes(), maintype="application",
                           subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           filename=anexo.name)
    try:
        with smtplib.SMTP(cfg["servidor"], int(cfg.get("porta", 587)), timeout=30) as smtp:
            if cfg.get("tls", True):
                smtp.starttls()
            if cfg.get("senha"):
                smtp.login(cfg["usuario"], cfg["senha"])
            smtp.send_message(msg)
        log.info("E-mail enviado para %s", cfg["destinatario"])
        return True
    except Exception as erro:
        log.error("Não consegui mandar o e-mail: %s", erro)
        return False


def enviar_telegram(vagas: list, config: Config) -> bool:
    cfg = config.telegram
    if not cfg.get("ativo"):
        return False

    # Monta as mensagens em HTML e divide se passar do limite do Telegram
    blocos, atual = [], f"<b>{len(vagas)} vaga(s) nova(s) pra você</b>\n\n"
    for v in vagas:
        item = (f"<b>[{v['nota']}] {html.escape(v['titulo'])}</b>\n"
                f"{html.escape(v['empresa'] or '')} | {html.escape(v['modalidade'] or v['local'] or '')}\n"
                f"<a href=\"{html.escape(v['url'])}\">Abrir vaga</a>\n\n")
        if len(atual) + len(item) > TELEGRAM_LIMITE:
            blocos.append(atual)
            atual = ""
        atual += item
    blocos.append(atual)

    url = f"https://api.telegram.org/bot{cfg['token']}/sendMessage"
    try:
        for bloco in blocos:
            resposta = requests.post(url, timeout=30, data={
                "chat_id": cfg["chat_id"], "text": bloco,
                "parse_mode": "HTML", "disable_web_page_preview": "true"})
            resposta.raise_for_status()
        log.info("Telegram enviado (%d mensagem(ns))", len(blocos))
        return True
    except Exception as erro:
        log.error("Não consegui mandar no Telegram: %s", erro)
        return False


def notificar(vagas: list, config: Config, anexo: Path | None = None) -> bool:
    """Manda pelos canais ligados no config. Devolve True se algum funcionou."""
    if not vagas:
        return False
    resultados = [enviar_email(vagas, config, anexo), enviar_telegram(vagas, config)]
    return any(resultados)
