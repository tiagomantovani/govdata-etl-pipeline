FROM apache/airflow:2.8.0

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow
# pyspark 3.5.0 (Python 3.8): Linux não precisa dos binários nativos do Windows
# openpyxl: leitura do XLSX oficial do INEP | pyarrow: pandas.read_parquet no loader
RUN pip install pyspark==3.5.0 && \
    pip install openpyxl==3.1.5 "pyarrow==15.0.2"
