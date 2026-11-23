"""
Painel web do Robô de Vagas (Streamlit).

Rodar:  python -m vagas painel
   ou:  streamlit run painel.py
"""

from __future__ import annotations

import argparse
import contextlib
import io
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from vagas import relatorio
from vagas.__main__ import cmd_coletar, cmd_repontuar
from vagas.banco import Banco
from vagas.config import ARQUIVO_PADRAO, carregar
from vagas.curriculo import extrair_perfil, ler_pdf, salvar_perfil
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


def rodar(comando, args=None) -> tuple[int, str]:
    """Roda um comando do robô aqui dentro (no .exe não dá pra chamar outro Python) e devolve o log."""
    saida = io.StringIO()
    handler = logging.StreamHandler(saida)
    log = logging.getLogger("vagas")
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    try:
        with contextlib.redirect_stdout(saida):
            codigo = comando(args, carregar())
    except Exception as erro:  # mostra o erro na tela em vez de derrubar o painel
        codigo = 1
        saida.write(f"\nErro: {erro}")
    finally:
        log.removeHandler(handler)
    return codigo, saida.getvalue()


# ------------------------------------------------------------------- cabeçalho

st.title("Robô de Vagas")
st.caption("Vagas coletadas automaticamente dos sites de emprego (" + ", ".join(config.fontes)
           + "), com nota de acordo com o seu perfil.")

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
            codigo, saida = rodar(cmd_coletar, argparse.Namespace(
                fontes=None, termos=None, ver=False, sem_alerta=True))
        carregar_vagas.clear()
        if codigo == 0:
            st.success("Busca concluída.")
        else:
            st.error("A busca teve problemas. Veja o log abaixo.")
        with st.expander("Log da busca"):
            st.code(saida[-5000:])

# ------------------------------------------------------------- meu currículo

with st.expander("Meu currículo", expanded=not ARQUIVO_PADRAO.exists()):
    st.caption("Envie seu currículo em PDF: o robô descobre os cargos, as habilidades e a sua cidade. "
               "Confira, ajuste e salve. O arquivo não sai do seu computador.")
    pdf = st.file_uploader("Currículo em PDF", type="pdf")
    perfil = {"termos": config.termos, "habilidades": config.habilidades,
              "cidades": config.cidades, "estado": config.estado}
    if pdf:
        texto = ler_pdf(pdf.getvalue())
        if texto.strip():
            perfil = extrair_perfil(texto)
        else:
            st.warning("Não consegui ler o texto desse PDF (parece ser uma foto ou digitalização). "
                       "Preencha os campos abaixo à mão.")

    with st.form("perfil"):
        termos = st.text_area("Cargos que você procura (um por linha)", "\n".join(perfil["termos"]))
        habilidades = st.text_area("Suas habilidades (uma por linha)", "\n".join(perfil["habilidades"]), height=180)
        c_cid, c_uf = st.columns([3, 1])
        cidades = c_cid.text_input("Cidades onde aceita trabalhar (separe por vírgula)", ", ".join(perfil["cidades"]))
        estado = c_uf.text_input("Estado (sigla)", perfil["estado"], max_chars=2)
        niveis = st.multiselect("Níveis que te interessam", ["estagio", "trainee", "junior", "pleno", "senior"],
                                default=[n for n in config.niveis_desejados
                                         if n in ("estagio", "trainee", "junior", "pleno", "senior")])
        if st.form_submit_button("Salvar perfil", type="primary"):
            linhas = lambda t: [x.strip() for x in t.splitlines() if x.strip()]  # noqa: E731
            if not linhas(termos):
                st.error("Coloque pelo menos um cargo pra o robô saber o que procurar.")
            else:
                salvar_perfil({"termos": linhas(termos), "habilidades": linhas(habilidades),
                               "cidades": [c.strip() for c in cidades.split(",") if c.strip()],
                               "estado": estado.strip().upper(), "niveis_desejados": niveis}, ARQUIVO_PADRAO)
                rodar(cmd_repontuar)  # notas das vagas que já estão no banco seguem o perfil novo
                carregar_vagas.clear()
                st.success("Perfil salvo. Agora clique em **Buscar vagas agora** na barra lateral.")

if df.empty:
    st.info("Ainda não há vagas. Salve seu perfil acima e clique em **Buscar vagas agora** na barra lateral.")
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
