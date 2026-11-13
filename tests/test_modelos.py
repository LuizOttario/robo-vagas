import pytest

from vagas.modelos import detectar_modalidade, detectar_nivel, normalizar


def test_normalizar_tira_acento_e_maiuscula():
    assert normalizar("  Automação   JÚNIOR ") == "automacao junior"


@pytest.mark.parametrize("texto, esperado", [
    ("Desenvolvedor Python Jr.", "junior"),
    ("Analista de Dados Júnior", "junior"),
    ("Estagiário(a) de Automação", "estagio"),
    ("Engenheiro de Dados Sênior", "senior"),
    ("Analista Pl", "pleno"),
    ("Junior/Pleno", "junior"),
    ("Tech Lead Python", "especialista"),
    ("Analista PL/SQL", ""),         # PL/SQL é linguagem, não nível
    ("Analista de Sistemas", ""),
])
def test_detectar_nivel(texto, esperado):
    assert detectar_nivel(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("São Paulo (Híbrido)", "hibrido"),
    ("100% Remoto", "remoto"),
    ("Trabalho em home office", "remoto"),
    ("Recife (Presencial)", "presencial"),
    ("Curitiba / PR", ""),
])
def test_detectar_modalidade(texto, esperado):
    assert detectar_modalidade(texto) == esperado
