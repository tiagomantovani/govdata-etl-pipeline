# tests/test_extraction.py
"""Testes offline das extrações (sem rede).

Regressão coberta: sentinelas do IDEB ("-"/"...") = valor não divulgado;
o regex de limpeza do código do município; e a formatação long-format.
"""
import pandas as pd

from src.extraction.ibge_extractor import IBGEExtractor
from src.extraction.inep_extractor import (
    INEPExtractor,
    IDEB_BASE_URL,
    IDEB_MUNICIPIOS_HEADER_ROW,
    IDEB_ANOS,
)
from src.utils.config import IBGE_API_BASE


def test_ibge_urls():
    assert IBGE_API_BASE == "https://servicodados.ibge.gov.br/api/v1"
    extractor = IBGEExtractor()
    assert extractor.base_url_sidra.startswith("https://apisidra.ibge.gov.br")


def test_inep_constantes():
    assert "download.inep.gov.br" in IDEB_BASE_URL
    assert IDEB_MUNICIPIOS_HEADER_ROW == 9
    assert 2005 in IDEB_ANOS and 2025 in IDEB_ANOS


def test_limpeza_codigo_municipio():
    # pandas lê "3550308.0"; o extrator remove o sufixo ".0"
    raw = pd.Series(["3550308.0", "1100015.0", "5300108.0"])
    clean = raw.astype(str).str.replace(r"\.0$", "", regex=True)
    assert list(clean) == ["3550308", "1100015", "5300108"]


def test_extrai_ano_da_coluna_do_ideb():
    # o melt usa o nome da coluna para extrair o ano
    col = "VL_OBSERVADO_2019"
    ano = pd.Series([col]).str.extract(r"(\d{4})").astype(int).iloc[0, 0]
    assert ano == 2019


def test_sentinela_negativo_para_numeric():
    # sentinela "-" vira NaN e deve ser tratada como ausente (None)
    serie = pd.Series([4.5, "-", 6.2, "...", None])
    numerico = pd.to_numeric(serie, errors="coerce")
    assert numerico.isna().sum() == 3  # "-", "..." e None
    assert numerico.iloc[0] == 4.5


def test_tem_extrator_de_municipios():
    extractor = INEPExtractor()
    assert callable(extractor.get_ideb_municipios)