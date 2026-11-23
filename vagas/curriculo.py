"""
Lê um currículo em PDF e monta o perfil de busca (cargos, habilidades e cidade).

O perfil vira o config.toml, que é o que o robô usa pra buscar e dar nota.
Nada sai do computador: o PDF só é lido aqui.
"""

from __future__ import annotations

import io
import json
import re
import tomllib
from pathlib import Path

from pypdf import PdfReader

from vagas.config import ARQUIVO_EXEMPLO
from vagas.modelos import normalizar
from vagas.pontuacao import contem

# Cargos que viram termos de busca quando aparecem no currículo
CARGOS = [
    # administrativo
    "assistente administrativo", "auxiliar administrativo", "analista administrativo",
    "assistente financeiro", "auxiliar financeiro", "analista financeiro",
    "assistente de departamento pessoal", "auxiliar de departamento pessoal", "departamento pessoal",
    "assistente de rh", "auxiliar de rh", "analista de rh", "recursos humanos",
    "recepcionista", "secretária", "secretário", "auxiliar de escritório", "assistente de escritório",
    "faturista", "assistente de faturamento", "auxiliar de faturamento",
    "assistente de compras", "comprador", "assistente comercial", "auxiliar comercial",
    "assistente de logística", "auxiliar de logística", "almoxarife",
    "auxiliar contábil", "assistente contábil", "assistente fiscal",
    "atendente", "operador de caixa",
    # TI
    "analista de suporte", "técnico de suporte", "suporte de ti", "help desk",
    "analista de infraestrutura", "analista de redes", "desenvolvedor python", "rpa",
]

# Habilidades que contam ponto na nota quando aparecem no currículo e na vaga
HABILIDADES = [
    # escritório
    "excel", "word", "powerpoint", "pacote office", "google planilhas", "outlook",
    "excel avançado", "tabela dinâmica", "procv",
    # rotinas administrativas
    "contas a pagar", "contas a receber", "faturamento", "fluxo de caixa", "conciliação bancária",
    "emissão de notas fiscais", "nota fiscal", "notas fiscais", "boletos", "cobrança",
    "folha de pagamento", "admissão", "demissão", "ponto eletrônico", "benefícios", "esocial",
    "gestão de documentos", "controle de documentos", "atendimento ao cliente",
    "atendimento telefônico", "recepção", "compras", "cotação", "orçamentos", "estoque",
    "controle de estoque", "inventário", "logística", "rotinas administrativas",
    "digitação", "pagamentos", "fornecedores", "licitações", "contratos", "crm",
    # sistemas ("senior" e "domínio" ficam de fora: confundem com nível e com "domínio do Excel")
    "sap", "totvs", "protheus", "sankhya", "omie", "erp",
    # TI
    "python", "selenium", "rpa", "sql", "power bi", "active directory", "microsoft 365",
    "redes", "suporte técnico", "help desk", "windows server", "linux", "zabbix",
]

UFS = ("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO").split()
CIDADE_UF = re.compile(
    r"([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ú][a-zà-ú]+)*)\s*[-/,–]\s*(" + "|".join(UFS) + r")\b")


def ler_pdf(conteudo: bytes) -> str:
    """Devolve o texto do PDF. PDF escaneado (só imagem) volta vazio."""
    leitor = PdfReader(io.BytesIO(conteudo))
    return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)


def extrair_perfil(texto: str) -> dict:
    """Acha cargos, habilidades e cidade no texto do currículo."""
    normal = normalizar(texto)
    cargos = [c for c in CARGOS if contem(normal, c)]
    # "departamento pessoal" sozinho é redundante se já achou um cargo de DP
    cargos = [c for c in cargos if not any(c != o and normalizar(c) in normalizar(o) for o in cargos)]
    habilidades = [h for h in HABILIDADES if contem(normal, h)]

    cidades, estado = [], ""
    achado = CIDADE_UF.search(texto)
    if achado:
        cidades, estado = [achado.group(1).strip()], achado.group(2)
    return {"termos": cargos, "habilidades": habilidades, "cidades": cidades, "estado": estado}


def salvar_perfil(perfil: dict, destino: Path) -> None:
    """Grava o perfil no config.toml, mantendo o resto do arquivo (e-mail, alertas...)."""
    origem = destino if destino.exists() else ARQUIVO_EXEMPLO
    with open(origem, "rb") as arquivo:
        dados = tomllib.load(arquivo)

    busca = dados.setdefault("busca", {})
    busca["termos"] = perfil["termos"]
    # O Vagas.com precisa do Chrome instalado; no .exe ficam só os sites que não precisam
    busca["fontes"] = perfil.get("fontes", ["gupy", "solides", "programathor"])
    p = dados.setdefault("perfil", {})
    for chave in ("habilidades", "cidades", "estado", "niveis_desejados"):
        if chave in perfil:
            p[chave] = perfil[chave]

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(para_toml(dados), encoding="utf-8")


def para_toml(dados: dict) -> str:
    """TOML simples: seções com texto, número, verdadeiro/falso e listas de texto."""
    linhas = []
    for secao, valores in dados.items():
        linhas.append(f"[{secao}]")
        for chave, valor in valores.items():
            # json.dumps escreve string, número, bool e lista num formato que o TOML também aceita
            texto = json.dumps(valor, ensure_ascii=False)
            linhas.append(f"{chave} = {texto}")
        linhas.append("")
    return "\n".join(linhas)
