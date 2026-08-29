from datetime import datetime, timedelta
from airflow import DAG

from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

# Funções que simulam os passos do seu processo de dados
def extrair_dados():
    print("Buscando dados da API do Governo...")

def transformar_dados():
    print("Limpando e normalizando os dados com Pandas...")

def carregar_dados():
    print("Salvando os dados limpos no PostgreSQL no disco D...")

# Configurações padrão da DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Definição do Pipeline
with DAG(
    'meu_primeiro_pipeline',
    default_args=default_args,
    description='Pipeline de teste para validação do ambiente no disco D',
    schedule_interval=None,  # Execução manual
    catchup=False,
) as dag:

    inicio = EmptyOperator(task_id='inicio')

    task_extracao = PythonOperator(
        task_id='extrair_dados_gov',
        python_callable=extrair_dados,
    )

    task_transformacao = PythonOperator(
        task_id='transformar_com_pandas',
        python_callable=transformar_dados,
    )

    task_carga = PythonOperator(
        task_id='carregar_no_postgres',
        python_callable=carregar_dados,
    )

    fim = EmptyOperator(task_id='fim')

    # Fluxo de execução (Orquestração)
    inicio >> task_extracao >> task_transformacao >> task_carga >> fim
