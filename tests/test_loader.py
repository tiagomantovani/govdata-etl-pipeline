# tests/test_loader.py
"""Testes do PostgresLoader que não dependem de banco/Docker.

Regressão: pandas .where(cond, None) mantém NaN em colunas numéricas —
foi a causa de 24.355 IDEBs virarem NaN no PostgreSQL.
"""
import math

import pandas as pd

from src.loading.postgres_loader import PostgresLoader


def test_to_nullable_converte_nan_para_none():
    series = pd.Series([4.5, math.nan, 6.0, None, 3.2], dtype=float)
    out = PostgresLoader._to_nullable(series)
    assert out.dtype == object
    assert out.iloc[0] == 4.5
    assert out.iloc[1] is None
    assert out.iloc[2] == 6.0
    assert out.iloc[3] is None
    assert out.iloc[4] == 3.2
    # não pode sobrar nenhum NaN (NaN != None em comparação)
    assert out.isna().sum() == 2  # exatamente os dois valores ausentes


def test_to_nullable_preserva_int_como_valor():
    # coluna mista (int + float) no Parquet lido via pandas
    series = pd.Series([1, 2, None], dtype="object")
    out = PostgresLoader._to_nullable(series)
    assert out.iloc[0] == 1
    assert out.iloc[2] is None


def test_resolve_host_sempre_retorna_string():
    from src.loading.postgres_loader import HOST
    assert isinstance(HOST, str)
    assert HOST in ("postgres", "localhost")