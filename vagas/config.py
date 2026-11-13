"""Leitura do arquivo de configuração (config.toml)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_PADRAO = PASTA_PROJETO / "config.toml"
ARQUIVO_EXEMPLO = PASTA_PROJETO / "config.exemplo.toml"


@dataclass
class Config:
    # [busca]
    termos: list[str] = field(default_factory=lambda: ["python"])
    fontes: list[str] = field(default_factory=lambda: ["gupy", "vagas_com", "programathor", "solides"])
    max_por_termo: int = 50
    mostrar_navegador: bool = False

    # [perfil]
    habilidades: list[str] = field(default_factory=list)
    niveis_desejados: list[str] = field(default_factory=lambda: ["junior"])
    niveis_evitar: list[str] = field(default_factory=lambda: ["senior", "especialista"])
    aceita_remoto: bool = True
    aceita_hibrido: bool = True
    cidades: list[str] = field(default_factory=list)
    estado: str = ""  # UF das cidades, ex.: "MG" (a Sólides precisa disso pra filtrar)
    palavras_evitar: list[str] = field(default_factory=list)

    # [alertas]
    nota_minima_alerta: int = 60

    # [email] e [telegram]
    email: dict = field(default_factory=dict)
    telegram: dict = field(default_factory=dict)

    # [geral]
    banco: Path = PASTA_PROJETO / "dados" / "vagas.db"
    pasta_relatorios: Path = PASTA_PROJETO / "relatorios"


def carregar(caminho: Path | None = None) -> Config:
    """Lê o config.toml. Se não existir, usa o config.exemplo.toml."""
    caminho = caminho or (ARQUIVO_PADRAO if ARQUIVO_PADRAO.exists() else ARQUIVO_EXEMPLO)
    with open(caminho, "rb") as arquivo:
        dados = tomllib.load(arquivo)

    busca = dados.get("busca", {})
    perfil = dados.get("perfil", {})
    alertas = dados.get("alertas", {})
    geral = dados.get("geral", {})
    padrao = Config()

    def caminho_do_projeto(valor, padrao_):
        if not valor:
            return padrao_
        p = Path(valor)
        return p if p.is_absolute() else PASTA_PROJETO / p

    return Config(
        termos=busca.get("termos", padrao.termos),
        fontes=busca.get("fontes", padrao.fontes),
        max_por_termo=busca.get("max_por_termo", padrao.max_por_termo),
        mostrar_navegador=busca.get("mostrar_navegador", padrao.mostrar_navegador),
        habilidades=perfil.get("habilidades", padrao.habilidades),
        niveis_desejados=perfil.get("niveis_desejados", padrao.niveis_desejados),
        niveis_evitar=perfil.get("niveis_evitar", padrao.niveis_evitar),
        aceita_remoto=perfil.get("aceita_remoto", padrao.aceita_remoto),
        aceita_hibrido=perfil.get("aceita_hibrido", padrao.aceita_hibrido),
        cidades=perfil.get("cidades", padrao.cidades),
        estado=perfil.get("estado", padrao.estado),
        palavras_evitar=perfil.get("palavras_evitar", padrao.palavras_evitar),
        nota_minima_alerta=alertas.get("nota_minima", padrao.nota_minima_alerta),
        email=dados.get("email", {}),
        telegram=dados.get("telegram", {}),
        banco=caminho_do_projeto(geral.get("banco"), padrao.banco),
        pasta_relatorios=caminho_do_projeto(geral.get("pasta_relatorios"), padrao.pasta_relatorios),
    )
