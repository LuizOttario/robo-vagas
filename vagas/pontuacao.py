"""
Dá uma nota de 0 a 100 pra cada vaga, de acordo com o seu perfil.

A nota é dividida assim:
  - Habilidades: até 45 pontos (cada habilidade sua que aparece na vaga soma)
  - Nível:       até 30 pontos (perde pontos se for um nível que você quer evitar)
  - Local:       até 25 pontos (remoto, híbrido ou na sua cidade)
  - Penalidade:  -15 por palavra que você quer evitar

Cada vaga também guarda os "motivos" da nota, pra você entender por que ela
ficou alta ou baixa.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from vagas.config import Config
from vagas.modelos import Vaga, normalizar

PESO_HABILIDADES = 45
PESO_NIVEL = 30
PESO_LOCAL = 25
PENALIDADE_PALAVRA = 15


def contem(texto: str, termo: str) -> bool:
    """Procura palavra inteira: 'sql' acha 'SQL Server' mas não 'mysqlx'."""
    termo = normalizar(termo)
    return re.search(rf"(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])", texto) is not None


def pontuar(vaga: Vaga, config: Config) -> Vaga:
    texto = vaga.texto_completo()
    nota = 0
    motivos: list[str] = []

    # 1) Habilidades
    if config.habilidades:
        achadas = [h for h in config.habilidades if contem(texto, h)]
        # 3 habilidades já dão a pontuação máxima: vaga nenhuma pede todas
        pontos = round(PESO_HABILIDADES * min(len(achadas), 3) / 3)
        nota += pontos
        if achadas:
            motivos.append(f"+{pontos} habilidades: {', '.join(achadas)}")
        else:
            motivos.append("+0 nenhuma das suas habilidades aparece")

    # 2) Nível
    desejados = [normalizar(n) for n in config.niveis_desejados]
    evitar = [normalizar(n) for n in config.niveis_evitar]
    if vaga.nivel in desejados:
        nota += PESO_NIVEL
        motivos.append(f"+{PESO_NIVEL} nível {vaga.nivel}")
    elif vaga.nivel in evitar:
        nota -= PESO_NIVEL
        motivos.append(f"-{PESO_NIVEL} nível {vaga.nivel}")
    elif not vaga.nivel:
        nota += PESO_NIVEL // 2  # sem nível informado: pode ser que sirva
        motivos.append(f"+{PESO_NIVEL // 2} nível não informado")
    else:
        motivos.append(f"+0 nível {vaga.nivel}")

    # 3) Local
    local = normalizar(vaga.local)
    na_cidade = any(normalizar(c) in local for c in config.cidades if c)
    if vaga.modalidade == "remoto" and config.aceita_remoto:
        nota += PESO_LOCAL
        motivos.append(f"+{PESO_LOCAL} remoto")
    elif na_cidade and (vaga.modalidade != "hibrido" or config.aceita_hibrido):
        nota += PESO_LOCAL
        motivos.append(f"+{PESO_LOCAL} na sua cidade")
    elif not vaga.local and not vaga.modalidade:
        nota += PESO_LOCAL // 2
        motivos.append(f"+{PESO_LOCAL // 2} local não informado")
    else:
        motivos.append("+0 fora da sua região")

    # 4) Palavras que você quer evitar
    for palavra in config.palavras_evitar:
        if contem(texto, palavra):
            nota -= PENALIDADE_PALAVRA
            motivos.append(f"-{PENALIDADE_PALAVRA} contém '{palavra}'")

    # 5) Bônus pequeno para vaga recente (até 7 dias)
    if vaga.publicada_em and datetime.now() - vaga.publicada_em < timedelta(days=7):
        nota += 5
        motivos.append("+5 publicada nos últimos 7 dias")

    vaga.nota = max(0, min(100, nota))
    vaga.motivos = motivos
    return vaga
