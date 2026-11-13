"""
Banco de dados SQLite: guarda todas as vagas já vistas.

SQLite é um banco que fica num arquivo só (dados/vagas.db), sem precisar
instalar servidor nenhum.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from vagas.modelos import STATUS, Vaga

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id            TEXT PRIMARY KEY,
    fonte         TEXT NOT NULL,
    id_externo    TEXT NOT NULL,
    titulo        TEXT NOT NULL,
    empresa       TEXT,
    url           TEXT,
    local         TEXT,
    modalidade    TEXT,
    nivel         TEXT,
    salario       TEXT,
    descricao     TEXT,
    tags          TEXT,              -- lista em JSON
    publicada_em  TEXT,
    coletada_em   TEXT NOT NULL,     -- primeira vez que o robô viu a vaga
    vista_em      TEXT NOT NULL,     -- última vez que o robô viu a vaga
    nota          INTEGER DEFAULT 0,
    motivos       TEXT,              -- lista em JSON
    status        TEXT DEFAULT 'nova',
    notificada    INTEGER DEFAULT 0,
    anotacao      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_vagas_nota ON vagas(nota DESC);
CREATE INDEX IF NOT EXISTS idx_vagas_status ON vagas(status);

CREATE TABLE IF NOT EXISTS execucoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio      TEXT NOT NULL,
    fim         TEXT,
    encontradas INTEGER DEFAULT 0,
    novas       INTEGER DEFAULT 0,
    erros       TEXT DEFAULT ''
);
"""


class Banco:
    def __init__(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho
        self.con = sqlite3.connect(caminho)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def fechar(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()

    # ------------------------------------------------------------------ vagas

    def salvar(self, vagas: list[Vaga]) -> list[Vaga]:
        """
        Salva as vagas. Devolve só as que são NOVAS (nunca vistas antes).
        Vagas que já existem têm os dados e a nota atualizados, mas o status
        que você marcou no painel é mantido.
        """
        agora = datetime.now().isoformat(timespec="seconds")
        novas = []
        with self.con:
            for v in vagas:
                existe = self.con.execute("SELECT 1 FROM vagas WHERE id = ?", (v.id,)).fetchone()
                dados = {
                    "id": v.id, "fonte": v.fonte, "id_externo": v.id_externo,
                    "titulo": v.titulo, "empresa": v.empresa, "url": v.url,
                    "local": v.local, "modalidade": v.modalidade, "nivel": v.nivel,
                    "salario": v.salario, "descricao": v.descricao,
                    "tags": json.dumps(v.tags, ensure_ascii=False),
                    "publicada_em": v.publicada_em.isoformat(timespec="seconds") if v.publicada_em else None,
                    "nota": v.nota, "motivos": json.dumps(v.motivos, ensure_ascii=False),
                    "agora": agora,
                }
                if existe:
                    self.con.execute("""
                        UPDATE vagas SET titulo=:titulo, empresa=:empresa, url=:url, local=:local,
                            modalidade=:modalidade, nivel=:nivel, salario=:salario, descricao=:descricao,
                            tags=:tags, publicada_em=COALESCE(:publicada_em, publicada_em),
                            nota=:nota, motivos=:motivos, vista_em=:agora
                        WHERE id=:id""", dados)
                else:
                    self.con.execute("""
                        INSERT INTO vagas (id, fonte, id_externo, titulo, empresa, url, local, modalidade,
                            nivel, salario, descricao, tags, publicada_em, coletada_em, vista_em, nota, motivos)
                        VALUES (:id, :fonte, :id_externo, :titulo, :empresa, :url, :local, :modalidade,
                            :nivel, :salario, :descricao, :tags, :publicada_em, :agora, :agora, :nota, :motivos)
                    """, dados)
                    novas.append(v)
        return novas

    def para_notificar(self, nota_minima: int) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM vagas WHERE notificada = 0 AND nota >= ? AND status != 'descartada' "
            "ORDER BY nota DESC", (nota_minima,)).fetchall()

    def marcar_notificadas(self, ids: list[str]) -> None:
        with self.con:
            self.con.executemany("UPDATE vagas SET notificada = 1 WHERE id = ?", [(i,) for i in ids])

    def mudar_status(self, id_vaga: str, status: str) -> None:
        if status not in STATUS:
            raise ValueError(f"Status inválido: {status}. Opções: {', '.join(STATUS)}")
        with self.con:
            self.con.execute("UPDATE vagas SET status = ? WHERE id = ?", (status, id_vaga))

    def anotar(self, id_vaga: str, texto: str) -> None:
        with self.con:
            self.con.execute("UPDATE vagas SET anotacao = ? WHERE id = ?", (texto, id_vaga))

    def tabela(self) -> pd.DataFrame:
        """Todas as vagas numa tabela do pandas (usada no painel e no relatório)."""
        df = pd.read_sql_query("SELECT * FROM vagas ORDER BY nota DESC, coletada_em DESC", self.con)
        for coluna in ["publicada_em", "coletada_em", "vista_em"]:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
        df["tags"] = df["tags"].apply(lambda t: json.loads(t) if t else [])
        df["motivos"] = df["motivos"].apply(lambda t: json.loads(t) if t else [])
        return df

    # -------------------------------------------------------------- execuções

    def iniciar_execucao(self) -> int:
        with self.con:
            cur = self.con.execute("INSERT INTO execucoes (inicio) VALUES (?)",
                                   (datetime.now().isoformat(timespec="seconds"),))
        return cur.lastrowid

    def finalizar_execucao(self, id_exec: int, encontradas: int, novas: int, erros: list[str]) -> None:
        with self.con:
            self.con.execute(
                "UPDATE execucoes SET fim = ?, encontradas = ?, novas = ?, erros = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), encontradas, novas, "\n".join(erros), id_exec))

    def execucoes(self, limite: int = 20) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM execucoes ORDER BY id DESC LIMIT ?", self.con, params=(limite,))
