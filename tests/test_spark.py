# tests/test_spark.py
"""Testes de transformação PySpark com dados sintéticos (sem rede).

Regressões cobertas:
1. process_ideb com coluna misturando int/float/null — antes falhava com
   CANNOT_MERGE_TYPE (inferência de schema); hoje usa schema explícito.
2. DoubleType não aceita Python int no Spark 4 — normalizamos para float.
3. IDEB não divulgado ("-") vira null e gera id_estado a partir do código.
"""
import json

import pytest

from src.transformation.spark_processor import SparkProcessor

ESTADOS = [
    {"id": 35, "sigla": "SP", "nome": "Sao Paulo",
     "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"}},
    {"id": 42, "sigla": "SC", "nome": "Santa Catarina",
     "regiao": {"id": 4, "sigla": "S", "nome": "Sul"}},
    {"id": 23, "sigla": "CE", "nome": "Ceara",
     "regiao": {"id": 2, "sigla": "NE", "nome": "Nordeste"}},
]

IDEB_MISTO = [
    {"uf": "SP", "codigo_municipio": "3550308", "nome_municipio": "Sao Paulo",
     "rede": "Municipal", "ideb": 4, "ano": 2025},
    {"uf": "SP", "codigo_municipio": "3550308", "nome_municipio": "Sao Paulo",
     "rede": "Estadual", "ideb": 4.5, "ano": 2025},
    {"uf": "SP", "codigo_municipio": "3500001", "nome_municipio": "Teste",
     "rede": "Municipal", "ideb": None, "ano": 2025},
]


@pytest.fixture(scope="module")
def processor():
    """Um único SparkSession para todos os testes do módulo."""

    spark = SparkProcessor()
    yield spark
    spark.stop()


def _write_json(tmp_path, name, data):
    fp = tmp_path / name
    fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(fp)


def test_spark_processa_estados(processor, tmp_path):
    df = processor.process_estados(_write_json(tmp_path, "estados.json", ESTADOS))
    rows = {r["sigla"]: r for r in df.collect()}
    assert len(rows) == 3
    assert rows["SP"]["id_estado"] == 35
    assert rows["SP"]["nome_regiao"] == "Sudeste"
    assert rows["SC"]["nome_regiao"] == "Sul"


def test_spark_ideb_aceita_int_float_e_null(processor, tmp_path):
    """Regressão: mistura int/float/null na coluna ideb não pode falhar."""
    df = processor.process_ideb(_write_json(tmp_path, "ideb.json", IDEB_MISTO))
    rows = {(r["rede"], r["codigo_municipio"]): r for r in df.collect()}
    assert len(rows) == 3

    assert rows[("Municipal", "3550308")]["ideb_val"] == 4.0   # int 4 vira float
    assert rows[("Estadual", "3550308")]["ideb_val"] == 4.5    # float preservado
    assert rows[("Municipal", "3500001")]["ideb_val"] is None  # null preservado


def test_spark_ideb_gera_id_estado(processor, tmp_path):
    df = processor.process_ideb(_write_json(tmp_path, "ideb.json", IDEB_MISTO))
    id_estados = {r["id_estado"] for r in df.select("id_estado").distinct().collect()}
    assert id_estados == {35}  # 35 = SP (primeiros 2 dígitos do código 3550308)


def test_spark_ideb_schema_fixo(processor, tmp_path):
    df = processor.process_ideb(_write_json(tmp_path, "ideb.json", IDEB_MISTO))
    cols = [c.name for c in df.schema.fields]
    assert cols == ["codigo_municipio", "nome_municipio", "uf", "rede",
                    "ano_int", "ideb_val", "id_estado"]