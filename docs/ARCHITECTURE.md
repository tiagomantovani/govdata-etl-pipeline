# Arquitetura — GovData ETL

## Visão geral

Pipeline em 4 camadas, orquestrado por Airflow e executável tanto no host (Windows) quanto no container (Linux).

```
IBGE APIs (SIDRA 4714/5938 + localidades) ─┐
                                           ├─► data/raw/*.json ─► PySpark ─► data/processed/*.parquet ─► PostgreSQL (star)
INEP download.inep.gov.br (IDEB xlsx/zip) ─┘                                          ▲
                                                                                      │ Airflow DAG govdata_pipeline
                                                                              extract ┤ transform ┤ load
                                                                                      │ (retries=1, diário)
```

## Decisões técnicas

| Tema | Escolha | Motivo |
|---|---|---|
| Extração IBGE | SIDRA `apisidra.ibge.gov.br` | API `servicodados` instável para agregados |
| Extração INEP | `download.inep.gov.br` (xlsx/zip) | `api.dadosabertosinep.org` fora do ar; `dadosabertosbrasil` idem |
| Transformação | PySpark 4.2.0 (host) / 3.5.0 (container) | Parquet particionado, schema explícito, funciona no Windows com fix nativo |
| Carga | PostgreSQL 13, `psycopg2`, `TRUNCATE + executemany` | Star schema simples, `NUMERIC` com `NULL` (não `NaN`) |
| Orquestração | Airflow 2.8 (LocalExecutor) + Docker | Reuso de código `src/` via volume, `data/` compartilhado host↔container |

## Portabilidade Windows ↔ Linux

`src/transformation/spark_processor.py` só ativa `HADOOP_HOME`, `PYSPARK_PYTHON` e `System.load(hadoop.dll)` quando `os.name == "nt"`. No Linux o Spark encontra o Python/JVM sozinho. O loader resolve o host do Postgres por tentativa de conexão (`postgres` dentro do Docker, `localhost` fora).

## Fluxo de dados por camada

1. **Raw** (`data/raw/*.json`, `data/downloads/*.xlsx`) — sempre preservado, com timestamp no nome.
2. **Processed** (`data/processed/*_processado/*.parquet`) — colunas tipadas, `NULL` para ausentes.
3. **Warehouse** (PostgreSQL) — `dim_estado` + 3 fatos + 5 views em `sql/views.sql`.

## Pastas

- `src/` importável tanto no host (`venv`) quanto no container (`/opt/airflow/src`).
- `airflow/dags/` montado em `/opt/airflow/dags`.
- `data/` montado em `/opt/airflow/data` (único ponto de verdade).
