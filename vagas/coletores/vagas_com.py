"""
Coletor do Vagas.com (vagas.com.br).

Técnica: RPA com Selenium. O robô abre o Chrome, entra na busca, clica em
"mostrar mais vagas" até juntar o suficiente e lê os cartões da tela,
do mesmo jeito que uma pessoa faria.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from vagas.coletores.base import USER_AGENT, Coletor
from vagas.modelos import Vaga, detectar_modalidade, detectar_nivel, normalizar

SITE = "https://www.vagas.com.br"


def slug(termo: str) -> str:
    """'Automação Python' vira 'automacao-python', que é o formato da URL do site."""
    return re.sub(r"[^a-z0-9]+", "-", normalizar(termo)).strip("-")


class ColetorVagasCom(Coletor):
    nome = "vagas_com"

    def __init__(self, mostrar_navegador: bool = False) -> None:
        super().__init__()
        self.mostrar_navegador = mostrar_navegador
        self._navegador: webdriver.Chrome | None = None

    @property
    def navegador(self) -> webdriver.Chrome:
        """Só abre o Chrome quando for usar pela primeira vez."""
        if self._navegador is None:
            opcoes = webdriver.ChromeOptions()
            if not self.mostrar_navegador:
                opcoes.add_argument("--headless=new")
            for arg in ["--lang=pt-BR", "--window-size=1366,900", "--no-sandbox",
                        "--disable-dev-shm-usage", f"--user-agent={USER_AGENT}"]:
                opcoes.add_argument(arg)
            # No Docker o Chromium fica num caminho diferente; essas variáveis apontam pra ele
            if os.environ.get("CHROME_BIN"):
                opcoes.binary_location = os.environ["CHROME_BIN"]
            servico = Service(os.environ["CHROMEDRIVER"]) if os.environ.get("CHROMEDRIVER") else Service()
            self._navegador = webdriver.Chrome(options=opcoes, service=servico)
            self._navegador.set_page_load_timeout(45)
        return self._navegador

    def coletar_termo(self, termo: str, limite: int) -> list[Vaga]:
        nav = self.navegador
        nav.get(f"{SITE}/vagas-de-{slug(termo)}")

        try:
            WebDriverWait(nav, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.vaga")))
        except TimeoutException:
            return []  # nenhuma vaga pra esse termo

        # Clica em "Mostrar mais vagas" até ter o suficiente ou o botão sumir
        while len(nav.find_elements(By.CSS_SELECTOR, "li.vaga")) < limite:
            if not self._clicar_mostrar_mais():
                break

        cartoes = nav.find_elements(By.CSS_SELECTOR, "li.vaga")[:limite]
        vagas = []
        for cartao in cartoes:
            try:
                vagas.append(ler_cartao(cartao))
            except NoSuchElementException:
                continue  # cartão com formato diferente, pula
        return vagas

    def _clicar_mostrar_mais(self) -> bool:
        nav = self.navegador
        antes = len(nav.find_elements(By.CSS_SELECTOR, "li.vaga"))
        botoes = nav.find_elements(By.CSS_SELECTOR, "#maisVagas, a.btMaisVagas")
        if not botoes or not botoes[0].is_displayed():
            return False
        nav.execute_script("arguments[0].scrollIntoView({block: 'center'});", botoes[0])
        nav.execute_script("arguments[0].click();", botoes[0])
        try:
            WebDriverWait(nav, 10).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "li.vaga")) > antes)
        except TimeoutException:
            return False
        time.sleep(self.pausa_entre_paginas)
        return True

    def fechar(self) -> None:
        super().fechar()
        if self._navegador is not None:
            self._navegador.quit()
            self._navegador = None


def texto(cartao: WebElement, seletor: str) -> str:
    achados = cartao.find_elements(By.CSS_SELECTOR, seletor)
    return achados[0].get_attribute("textContent").strip() if achados else ""


def ler_cartao(cartao: WebElement) -> Vaga:
    link = cartao.find_element(By.CSS_SELECTOR, "a.link-detalhes-vaga")
    titulo = (link.get_attribute("title") or link.text).strip()
    nivel_site = texto(cartao, ".nivelVaga")
    descricao = re.sub(r"\s+", " ", texto(cartao, ".detalhes p"))

    # O local vem junto com um texto de ajuda escondido; pega só a primeira linha
    local = texto(cartao, ".vaga-local").split("\n")[0].strip()
    local = re.sub(r"\s+", " ", local)

    publicada = None
    data = texto(cartao, ".data-publicacao")
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", data):
        publicada = datetime.strptime(data, "%d/%m/%Y")
    elif "hoje" in data.lower():
        publicada = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return Vaga(
        fonte="vagas_com",
        id_externo=link.get_attribute("data-id-vaga") or link.get_attribute("id"),
        titulo=titulo,
        empresa=texto(cartao, ".emprVaga"),
        url=link.get_attribute("href"),
        local=local,
        modalidade=detectar_modalidade(local, titulo, descricao),
        nivel=detectar_nivel(nivel_site) or detectar_nivel(titulo),
        descricao=descricao,
        publicada_em=publicada,
    )
