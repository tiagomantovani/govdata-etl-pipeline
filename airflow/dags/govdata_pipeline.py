# airflow/dags/govdata_pipeline.py
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator  # pyright: ignore[reportMissingImports]
import glob
import os
import sys

# Força o Python do Docker a enxergar a raiz do projeto (src está em /opt/airflow/src)
sys.path.insert(0, '/opt/airflow')

from src.extraction.ibge_extractor import IBGEExtractor
from src.extraction.inep_extractor import INEPExtractor
from src.transformation.spark_processor import SparkProcessor
from src.loading.postgres_loader import PostgresLoader

# Argumentos padrão
default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def latest(pattern):
    """Retorna o caminho do arquivo JSON mais recente do raw (ou None)."""
    files = sorted(glob.glob(os.path.join('/opt/airflow/data/raw', pattern)))
    return files[-1] if files else None


def extract_ibge():
    """Extrai estados, população e PIB das APIs do IBGE/SIDRA."""
    extractor = IBGEExtractor()
    extractor.get_estados()
    extractor.get_populacao()
    extractor.get_pib()


def extract_inep():
    """Extrai IDEB por município (arquivo oficial do INEP)."""
    extractor = INEPExtractor()
    extractor.get_ideb_municipios(etapa="anos_iniciais", ano=2025)


def transform_data():
    """Transforma os 4 datasets mais recentes com PySpark e salva Parquet."""
    processor = SparkProcessor()
    processor.run_all({
        "estados": latest("ibge_estados_*.json"),
        "populacao": latest("ibge_populacao_*.json"),
        "pib": latest("ibge_pib_*.json"),
        "ideb": latest("inep_ideb_*.json"),
    })
    processor.stop()


def load_to_postgres():
    """Carrega os Parquet processados no PostgreSQL (star schema)."""
    loader = PostgresLoader()
    if loader.connect():
        loader.create_tables()
        loader.load_dim_estado()
        loader.load_fato_populacao()
        loader.load_fato_pib()
        loader.load_fato_ideb()
        loader.close()


with DAG(
    'govdata_pipeline',
    default_args=default_args,
    description='Pipeline completo de dados do governo brasileiro',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['govdata', 'etl', 'pipeline'],
) as dag:

    task_extract_ibge = PythonOperator(
        task_id='extract_ibge',
        python_callable=extract_ibge,
    )

    task_extract_inep = PythonOperator(
        task_id='extract_inep',
        python_callable=extract_inep,
    )

    task_transform = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
    )

    task_load = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres,
    )

    # Extract (paralelo) >> Transform >> Load
    [task_extract_ibge, task_extract_inep] >> task_transform >> task_load