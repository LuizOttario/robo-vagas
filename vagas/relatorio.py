"""
Gera o relatório em Excel com três abas:
  - Vagas:   todas as vagas, ordenadas pela nota, com link clicável e cores
  - Resumo:  números gerais e contagens por site, modalidade e nível
  - Gráficos: barras com vagas por site e as tecnologias mais pedidas
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from vagas.modelos import normalizar

AZUL = "2F5597"
VERDE, AMARELO, VERMELHO = "C6EFCE", "FFEB9C", "FFC7CE"

# Tecnologias que o relatório conta pra montar o ranking
TECNOLOGIAS = [
    "Python", "SQL", "Excel", "Power BI", "Selenium", "Pandas", "Java", "JavaScript",
    "TypeScript", "C#", ".NET", "React", "Node.js", "AWS", "Azure", "GCP", "Docker",
    "Kubernetes", "Git", "API", "Django", "Flask", "FastAPI", "PostgreSQL", "MySQL",
    "MongoDB", "Spark", "Airflow", "Linux", "UiPath", "Automation Anywhere", "Blue Prism",
    "RPA", "Machine Learning", "PHP", "Go", "Angular", "Vue",
]


def contar_tecnologias(df: pd.DataFrame) -> Counter:
    """Conta em quantas vagas cada tecnologia aparece."""
    from vagas.pontuacao import contem

    contagem = Counter()
    for _, linha in df.iterrows():
        texto = normalizar(" ".join([linha["titulo"], linha["descricao"] or "", " ".join(linha["tags"])]))
        for tec in TECNOLOGIAS:
            if contem(texto, tec):
                contagem[tec] += 1
    return contagem


def _cabecalho(aba, colunas: list[str], larguras: list[int]) -> None:
    aba.append(colunas)
    for celula, largura in zip(aba[1], larguras):
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.alignment = Alignment(horizontal="center", vertical="center")
        aba.column_dimensions[celula.column_letter].width = largura
    aba.freeze_panes = "A2"


def gerar(df: pd.DataFrame, pasta: Path, nome: str | None = None) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / (nome or f"vagas_{datetime.now():%Y-%m-%d}.xlsx")
    wb = Workbook()

    # ---------------------------------------------------------------- Vagas
    aba = wb.active
    aba.title = "Vagas"
    colunas = ["Nota", "Título", "Empresa", "Nível", "Modalidade", "Local", "Salário",
               "Site", "Publicada", "Status", "Por que essa nota", "Link"]
    _cabecalho(aba, colunas, [7, 50, 28, 12, 13, 24, 18, 14, 12, 13, 60, 12])

    for _, v in df.iterrows():
        publicada = v["publicada_em"].to_pydatetime().date() if pd.notna(v["publicada_em"]) else None
        aba.append([v["nota"], v["titulo"], v["empresa"], v["nivel"], v["modalidade"], v["local"],
                    v["salario"], v["fonte"], publicada, v["status"], "; ".join(v["motivos"]), "Abrir"])
        linha = aba.max_row
        link = aba.cell(row=linha, column=len(colunas))
        link.hyperlink = v["url"]
        link.font = Font(color="0563C1", underline="single")
        aba.cell(row=linha, column=9).number_format = "DD/MM/YYYY"

    if len(df):
        ultima = aba.max_row
        faixa = f"A2:A{ultima}"
        aba.conditional_formatting.add(faixa, CellIsRule(operator="greaterThanOrEqual", formula=["60"],
                                       fill=PatternFill("solid", fgColor=VERDE)))
        aba.conditional_formatting.add(faixa, CellIsRule(operator="between", formula=["35", "59"],
                                       fill=PatternFill("solid", fgColor=AMARELO)))
        aba.conditional_formatting.add(faixa, CellIsRule(operator="lessThan", formula=["35"],
                                       fill=PatternFill("solid", fgColor=VERMELHO)))
        aba.auto_filter.ref = f"A1:{get_column_letter(len(colunas))}{ultima}"

    # --------------------------------------------------------------- Resumo
    resumo = wb.create_sheet("Resumo")
    resumo.column_dimensions["A"].width = 32
    resumo.column_dimensions["B"].width = 14
    titulo = resumo.cell(row=1, column=1, value=f"Relatório de vagas - {datetime.now():%d/%m/%Y %H:%M}")
    titulo.font = Font(bold=True, size=14, color=AZUL)

    linha = 3
    gerais = [
        ("Total de vagas", len(df)),
        ("Vagas com nota 60 ou mais", int((df["nota"] >= 60).sum()) if len(df) else 0),
        ("Nota média", round(float(df["nota"].mean()), 1) if len(df) else 0),
        ("Candidaturas feitas", int((df["status"] == "candidatei").sum()) if len(df) else 0),
    ]
    for rotulo, valor in gerais:
        resumo.cell(row=linha, column=1, value=rotulo).font = Font(bold=True)
        resumo.cell(row=linha, column=2, value=valor)
        linha += 1

    posicoes_graficos = {}
    for titulo_bloco, coluna in [("Vagas por site", "fonte"), ("Vagas por modalidade", "modalidade"),
                                 ("Vagas por nível", "nivel")]:
        linha += 1
        resumo.cell(row=linha, column=1, value=titulo_bloco).font = Font(bold=True, color=AZUL)
        linha += 1
        inicio = linha
        contagem = df[coluna].replace("", "não informado").value_counts() if len(df) else {}
        for valor, qtd in contagem.items():
            resumo.cell(row=linha, column=1, value=valor)
            resumo.cell(row=linha, column=2, value=int(qtd))
            linha += 1
        posicoes_graficos[coluna] = (inicio, linha - 1)

    linha += 1
    resumo.cell(row=linha, column=1, value="Tecnologias mais pedidas").font = Font(bold=True, color=AZUL)
    linha += 1
    inicio_tec = linha
    for tec, qtd in contar_tecnologias(df).most_common(15):
        resumo.cell(row=linha, column=1, value=tec)
        resumo.cell(row=linha, column=2, value=qtd)
        linha += 1
    posicoes_graficos["tecnologias"] = (inicio_tec, linha - 1)

    # ------------------------------------------------------------- Gráficos
    graficos = wb.create_sheet("Gráficos")
    lugar = 1
    for chave, titulo_graf in [("fonte", "Vagas por site"), ("tecnologias", "Tecnologias mais pedidas"),
                               ("modalidade", "Vagas por modalidade")]:
        inicio, fim = posicoes_graficos[chave]
        if fim < inicio:
            continue
        g = BarChart()
        g.type = "bar"  # barras deitadas: fica mais fácil de ler os nomes
        g.title = titulo_graf
        g.legend = None
        g.height = 8 if chave != "tecnologias" else 11
        g.width = 18
        g.add_data(Reference(resumo, min_col=2, min_row=inicio, max_row=fim))
        g.set_categories(Reference(resumo, min_col=1, min_row=inicio, max_row=fim))
        graficos.add_chart(g, f"A{lugar}")
        lugar += 17 if chave != "tecnologias" else 23

    wb.save(arquivo)
    return arquivo
