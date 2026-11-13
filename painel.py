"""
Painel web do Robô de Vagas (Streamlit).

Rodar:  python -m vagas painel
   ou:  streamlit run painel.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from vagas import relatorio
from vagas.banco import Banco
from vagas.config import PASTA_PROJETO, carregar
from vagas.modelos import STATUS, normalizar

st.set_page_config(page_title="Robô de Vagas", page_icon=None, layout="wide")

COR = "#2F5597"
config = carregar()


@st.cache_data(ttl=60)
def carregar_vagas() -> pd.DataFrame:
    with Banco(config.banco) as banco:
        return banco.tabela()


def carregar_execucoes() -> pd.DataFrame:
    with Banco(config.banco) as banco:
        return banco.execucoes()


def salvar_mudancas(originais: pd.DataFrame, editadas: pd.DataFrame) -> int:
    """Grava no banco o status e as anotações que você mudou na tabela."""
    mudou = 0
    with Banco(config.banco) as banco:
        for id_vaga, linha in editadas.iterrows():
            antes = originais.loc[id_vaga]
            if linha["status"] != antes["status"]:
                banco.mudar_status(id_vaga, linha["status"])
                mudou += 1
            if (linha["anotacao"] or "") != (antes["anotacao"] or ""):
                banco.anotar(id_vaga, linha["anotacao"] or "")
                mudou += 1
    return mudou


# ------------------------------------------------------------------- cabeçalho

st.title("Robô de Vagas")
st.caption("Vagas coletadas automaticamente do Gupy, Vagas.com e ProgramaThor, com nota de acordo com o seu perfil.")

df = carregar_vagas()

# ---------------------------------------------------------------- barra lateral

with st.sidebar:
    st.header("Filtros")
    busca = st.text_input("Buscar no título ou empresa", placeholder="ex.: python, banco, júnior")
    nota_min = st.slider("Nota mínima", 0, 100, 40, step=5)
    fontes = st.multiselect("Sites", placeholder="Todos", options=sorted(df["fonte"].unique()) if len(df) else [])
    modalidades = st.multiselect("Modalidade", placeholder="Todos", options=["remoto", "hibrido", "presencial", ""],
                                 format_func=lambda m: m or "não informado")
    niveis = st.multiselect("Nível", placeholder="Todos", options=["estagio", "trainee", "junior", "pleno", "senior", "especialista", ""],
                            format_func=lambda n: n or "não informado")
    status_sel = st.multiselect("Status", STATUS, default=[s for s in STATUS if s != "descartada"])
    so_recentes = st.checkbox("Só vagas coletadas nos últimos 7 dias")

    st.divider()
    st.header("Robô")
    if st.button("Buscar vagas agora", type="primary", width="stretch"):
        with st.spinner("O robô está buscando vagas. Isso leva uns 2 minutos..."):
            resultado = subprocess.run([sys.executable, "-m", "vagas", "coletar"],
                                       cwd=PASTA_PROJETO, capture_output=True, text=True)
        carregar_vagas.clear()
        if resultado.returncode == 0:
            st.success("Busca concluída.")
        else:
            st.error("A busca teve problemas. Veja o log abaixo.")
        with st.expander("Log da busca"):
            st.code(resultado.stdout[-4000:] + resultado.stderr[-2000:])

if df.empty:
    st.info("Ainda não há vagas. Clique em **Buscar vagas agora** na barra lateral "
            "ou rode `python -m vagas coletar` no terminal.")
    st.stop()

# ---------------------------------------------------------------- filtragem

filtro = df["nota"] >= nota_min
if busca:
    termo = normalizar(busca)
    filtro &= (df["titulo"].map(normalizar).str.contains(termo, regex=False)
               | df["empresa"].fillna("").map(normalizar).str.contains(termo, regex=False))
if fontes:
    filtro &= df["fonte"].isin(fontes)
if modalidades:
    filtro &= df["modalidade"].fillna("").isin(modalidades)
if niveis:
    filtro &= df["nivel"].fillna("").isin(niveis)
if status_sel:
    filtro &= df["status"].isin(status_sel)
if so_recentes:
    filtro &= df["coletada_em"] >= datetime.now() - timedelta(days=7)
filtradas = df[filtro]

# ------------------------------------------------------------------- números

hoje = pd.Timestamp(datetime.now().date())
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Vagas no banco", len(df))
c2.metric("Mostrando agora", len(filtradas))
c3.metric("Nota 60 ou mais", int((df["nota"] >= 60).sum()))
c4.metric("Novas hoje", int((df["coletada_em"] >= hoje).sum()))
c5.metric("Candidaturas", int(df["status"].isin(["candidatei", "entrevista"]).sum()))

aba_vagas, aba_graficos, aba_candidaturas, aba_robo = st.tabs(
    ["Vagas", "Gráficos", "Minhas candidaturas", "Execuções do robô"])

# --------------------------------------------------------------------- vagas

with aba_vagas:
    st.caption("Mude o **status** ou escreva uma **anotação** direto na tabela e clique em Salvar.")
    tabela = filtradas.set_index("id")[
        ["nota", "titulo", "empresa", "nivel", "modalidade", "local", "salario",
         "fonte", "publicada_em", "status", "anotacao", "url"]].copy()

    editada = st.data_editor(
        tabela,
        width="stretch",
        height=520,
        hide_index=True,
        disabled=[c for c in tabela.columns if c not in ("status", "anotacao")],
        column_config={
            "nota": st.column_config.ProgressColumn("Nota", min_value=0, max_value=100, format="%d"),
            "titulo": st.column_config.TextColumn("Título", width="large"),
            "empresa": "Empresa",
            "nivel": "Nível",
            "modalidade": "Modalidade",
            "local": "Local",
            "salario": "Salário",
            "fonte": "Site",
            "publicada_em": st.column_config.DateColumn("Publicada", format="DD/MM/YYYY"),
            "status": st.column_config.SelectboxColumn("Status", options=STATUS, required=True),
            "anotacao": st.column_config.TextColumn("Anotação"),
            "url": st.column_config.LinkColumn("Link", display_text="Abrir"),
        },
        key="tabela_vagas",
    )

    col_salvar, col_excel, _ = st.columns([1, 1, 3])
    if col_salvar.button("Salvar mudanças", width="stretch"):
        n = salvar_mudancas(tabela, editada)
        carregar_vagas.clear()
        st.success(f"{n} mudança(s) salva(s).") if n else st.info("Nada mudou.")
        st.rerun() if n else None

    with tempfile.TemporaryDirectory() as pasta:
        arquivo = relatorio.gerar(filtradas, Path(pasta), "vagas.xlsx")
        col_excel.download_button("Baixar Excel", arquivo.read_bytes(),
                                  file_name=f"vagas_{datetime.now():%Y-%m-%d}.xlsx",
                                  width="stretch")

    st.subheader("Detalhes da vaga")
    if len(filtradas):
        escolhida = st.selectbox("Escolha uma vaga", filtradas["id"],
                                 format_func=lambda i: f"[{df.set_index('id').loc[i, 'nota']}] "
                                                       f"{df.set_index('id').loc[i, 'titulo']}")
        v = df.set_index("id").loc[escolhida]
        st.markdown(f"**{v['titulo']}** em **{v['empresa']}**  \n"
                    f"{v['nivel'] or 'nível não informado'} | {v['modalidade'] or 'modalidade não informada'}"
                    f" | {v['local'] or ''}  \n[Abrir a vaga no site]({v['url']})")
        st.markdown("**Por que essa nota:**")
        for motivo in v["motivos"]:
            st.markdown(f"- {motivo}")
        if v["tags"]:
            st.markdown("**Tecnologias:** " + ", ".join(v["tags"]))
        if v["descricao"]:
            with st.expander("Descrição"):
                st.write(v["descricao"])

# ------------------------------------------------------------------ gráficos

with aba_graficos:
    if filtradas.empty:
        st.info("Nenhuma vaga com esses filtros.")
    else:
        g1, g2 = st.columns(2)

        por_site = filtradas["fonte"].value_counts().reset_index()
        por_site.columns = ["Site", "Vagas"]
        g1.plotly_chart(px.bar(por_site, x="Vagas", y="Site", orientation="h", title="Vagas por site",
                               color_discrete_sequence=[COR]), width="stretch")

        por_mod = filtradas["modalidade"].replace("", "não informado").fillna("não informado").value_counts().reset_index()
        por_mod.columns = ["Modalidade", "Vagas"]
        g2.plotly_chart(px.pie(por_mod, names="Modalidade", values="Vagas", hole=0.5,
                               title="Modalidade"), width="stretch")

        g3, g4 = st.columns(2)
        tecs = relatorio.contar_tecnologias(filtradas).most_common(15)
        if tecs:
            df_tec = pd.DataFrame(tecs, columns=["Tecnologia", "Vagas"]).sort_values("Vagas")
            g3.plotly_chart(px.bar(df_tec, x="Vagas", y="Tecnologia", orientation="h",
                                   title="Tecnologias mais pedidas", color_discrete_sequence=[COR]),
                            width="stretch")

        g4.plotly_chart(px.histogram(filtradas, x="nota", nbins=20, title="Distribuição das notas",
                                     color_discrete_sequence=[COR]).update_layout(bargap=0.05),
                        width="stretch")

        por_dia = filtradas.assign(dia=filtradas["coletada_em"].dt.date).groupby("dia").size().reset_index(name="Vagas")
        st.plotly_chart(px.line(por_dia, x="dia", y="Vagas", markers=True, title="Vagas novas por dia",
                                color_discrete_sequence=[COR]), width="stretch")

# -------------------------------------------------------------- candidaturas

with aba_candidaturas:
    funil = df["status"].value_counts().reindex(STATUS, fill_value=0)
    cols = st.columns(len(STATUS))
    for col, (status, qtd) in zip(cols, funil.items()):
        col.metric(status.capitalize(), int(qtd))

    minhas = df[df["status"].isin(["interessante", "candidatei", "entrevista"])]
    if minhas.empty:
        st.info("Marque vagas como **interessante**, **candidatei** ou **entrevista** na aba Vagas "
                "pra acompanhar aqui.")
    else:
        for status in ["entrevista", "candidatei", "interessante"]:
            grupo = minhas[minhas["status"] == status]
            if grupo.empty:
                continue
            st.subheader(f"{status.capitalize()} ({len(grupo)})")
            for _, v in grupo.iterrows():
                nota_extra = f" | _{v['anotacao']}_" if v["anotacao"] else ""
                st.markdown(f"- **[{v['titulo']}]({v['url']})** em {v['empresa']} "
                            f"(nota {v['nota']}){nota_extra}")

# ------------------------------------------------------------------ execuções

with aba_robo:
    execs = carregar_execucoes()
    if execs.empty:
        st.info("O robô ainda não rodou.")
    else:
        execs = execs.rename(columns={"inicio": "Início", "fim": "Fim", "encontradas": "Encontradas",
                                      "novas": "Novas", "erros": "Erros"})
        st.dataframe(execs[["Início", "Fim", "Encontradas", "Novas", "Erros"]],
                     width="stretch", hide_index=True)
