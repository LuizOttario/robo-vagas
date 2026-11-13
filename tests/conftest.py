import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vagas.config import Config  # noqa: E402
from vagas.modelos import Vaga  # noqa: E402


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(
        habilidades=["python", "sql", "selenium", "excel"],
        niveis_desejados=["junior", "estagio"],
        niveis_evitar=["senior", "especialista"],
        cidades=["São Paulo"],
        palavras_evitar=["inglês fluente"],
        banco=tmp_path / "vagas.db",
        pasta_relatorios=tmp_path / "relatorios",
    )


@pytest.fixture
def vaga_boa() -> Vaga:
    return Vaga(fonte="gupy", id_externo="1", titulo="Desenvolvedor Python Júnior",
                empresa="Empresa Boa", url="https://exemplo.com/1", modalidade="remoto",
                local="Remoto", nivel="junior",
                descricao="Automação com Python, Selenium e SQL.", publicada_em=datetime.now())


@pytest.fixture
def vaga_ruim() -> Vaga:
    return Vaga(fonte="vagas_com", id_externo="2", titulo="Engenheiro Java Sênior",
                empresa="Empresa X", url="https://exemplo.com/2", modalidade="presencial",
                local="Manaus / AM", nivel="senior", descricao="Java, Spring. Inglês fluente.")
