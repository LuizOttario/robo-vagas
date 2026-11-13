"""Estruturas de dados usadas no projeto inteiro."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

# Status possíveis de uma vaga no painel
STATUS = ["nova", "interessante", "candidatei", "entrevista", "descartada"]


@dataclass
class Vaga:
    fonte: str              # gupy, vagas_com, programathor
    id_externo: str         # id da vaga no site de origem
    titulo: str
    empresa: str
    url: str
    local: str = ""         # cidade/estado ou "Remoto"
    modalidade: str = ""    # remoto, hibrido, presencial
    nivel: str = ""         # estagio, junior, pleno, senior...
    salario: str = ""       # do jeito que o site mostra, ex.: "Até R$ 5.000"
    descricao: str = ""
    tags: list[str] = field(default_factory=list)
    publicada_em: datetime | None = None

    # Preenchidos depois, pela pontuação
    nota: int = 0
    motivos: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Id único no banco: a mesma vaga nunca é salva duas vezes."""
        return f"{self.fonte}:{self.id_externo}"

    def texto_completo(self) -> str:
        """Tudo que dá pra usar na hora de procurar palavras-chave."""
        return normalizar(" ".join([self.titulo, self.nivel, self.descricao, " ".join(self.tags)]))


def normalizar(texto: str) -> str:
    """Minúsculas e sem acento: 'Júnior' vira 'junior'."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def detectar_modalidade(*textos: str) -> str:
    texto = normalizar(" ".join(textos))
    if "hibrid" in texto:
        return "hibrido"
    if "remot" in texto or "home office" in texto or "home-office" in texto:
        return "remoto"
    if "presencial" in texto:
        return "presencial"
    return ""


NIVEIS = [
    ("estagio", ["estagio", "estagiario", "intern"]),
    ("trainee", ["trainee"]),
    ("junior", ["junior", "jr", "entry level", "entry-level"]),
    ("pleno", ["pleno", "pl", "mid", "mid-level"]),
    ("senior", ["senior", "sr", "sênior"]),
    ("especialista", ["especialista", "specialist", "staff", "principal", "lead", "lider", "tech lead"]),
]


def detectar_nivel(*textos: str) -> str:
    """Procura o nível no texto. Usa palavra inteira pra 'jr' não casar com 'jrs'."""
    # "PL/SQL" é uma linguagem, não o nível "Pleno"
    texto = normalizar(" ".join(textos)).replace("pl/sql", "plsql")
    for nivel, palavras in NIVEIS:
        for p in palavras:
            if re.search(rf"(?<![a-z]){re.escape(normalizar(p))}(?![a-z])", texto):
                return nivel
    return ""
