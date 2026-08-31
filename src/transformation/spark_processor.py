# src/transformation/spark_processor.py
import json
import os
import sys

# Windows: aponta p/ env vars nativas (SPARK 4 + JDK 25). Linux/container
# não precisa de nada disso — pyspark encontra o Python e o Hadoop nativo.
if os.name == "nt":
    os.environ["HADOOP_HOME"] = "D:\\hadoop"
    venv_python = os.path.join(os.path.dirname(sys.executable), "python.exe")
    os.environ["PYSPARK_PYTHON"] = venv_python
    os.environ["PYSPARK_DRIVER_PYTHON"] = venv_python
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
from src.utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR


class SparkProcessor:
    def __init__(self):
        builder = SparkSession.builder \
            .appName("GovDataPipeline") \
            .master("local[*]") \
            .config("spark.sql.warehouse.dir", PROCESSED_DATA_DIR)

        if os.name == "nt":
            builder = builder \
                .config("spark.driver.extraJavaOptions", "-Djava.library.path=D:\\hadoop\\bin") \
                .config("spark.executor.extraJavaOptions", "-Djava.library.path=D:\\hadoop\\bin")

        self.spark = builder.getOrCreate()

        # Windows: carrega hadoop.dll explicitamente antes do commit Parquet
        # (evita UnsatisfiedLinkError no NativeIO$Windows.access0 com JDK 25)
        if os.name == "nt":
            hadoop_native = os.path.join(os.environ.get("HADOOP_HOME", "D:\\hadoop"), "bin", "hadoop.dll")
            try:
                self.spark._jvm.java.lang.System.load(hadoop_native)
            except Exception:
                pass

        print(f"🚀 Spark Session iniciada: {self.spark.version}")

    # ---- Métodos auxiliares ----

    def _read_json_list(self, filepath):
        """Lê um arquivo JSON e retorna a lista de registros."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _sidra_to_dataframe(self, filepath):
        """
        Converte dados bruto da API SIDRA para DataFrame.

        A API SIDRA retorna uma LISTA onde:
        - O primeiro item é o CABEÇALHO (nomes das colunas)
        - Os demais itens são os DADOS
        """
        records = self._read_json_list(filepath)

        header = records[0]          # ex: {"NC": "...", "V": "Valor", "D1N": "Brasil", ...}
        rows = records[1:]           # dados propriamente ditos

        # Monta lista de dicionários usando o cabeçalho como nomes de coluna
        data = []
        for row in rows:
            item = {col: row.get(col) for col in header}
            data.append(item)

        return self.spark.createDataFrame(data)

    def _save_parquet(self, df, name):
        """Salva DataFrame como Parquet e mostra resultado."""
        output_path = os.path.join(PROCESSED_DATA_DIR, name)
        df.write.mode("overwrite").parquet(output_path)
        print(f"✅ Processado e salvo em: {output_path}")
        print(f"📈 Registros: {df.count()}")
        df.show(truncate=False)
        return df

    # ---- Processamento de cada dataset ----

    def process_estados(self, input_file):
        """Processa lista de estados (formato localidades API IBGE)."""
        records = self._read_json_list(input_file)
        df = self.spark.createDataFrame(records)

        df_clean = df \
            .withColumn("id_estado", F.col("id").cast(IntegerType())) \
            .withColumn("id_regiao", F.col("regiao.id").cast(IntegerType())) \
            .withColumn("sigla_regiao", F.col("regiao.sigla")) \
            .withColumn("nome_regiao", F.col("regiao.nome")) \
            .select("id_estado", "sigla", "nome", "sigla_regiao", "nome_regiao", "id_regiao")

        return self._save_parquet(df_clean, "estados_processados")

    def process_populacao(self, input_file):
        """Processa população por UF (SIDRA tabela 4714)."""
        df = self._sidra_to_dataframe(input_file)

        df_clean = df \
            .withColumnRenamed("D1C", "codigo_uf") \
            .withColumnRenamed("D1N", "nome_uf") \
            .withColumnRenamed("D3N", "ano") \
            .withColumn("populacao",
                        F.when(F.col("V").rlike(r"^\d+$"),
                               F.col("V").cast(DoubleType()))
                         .otherwise(F.lit(None))) \
            .select("codigo_uf", "nome_uf", "ano", "populacao")

        return self._save_parquet(df_clean, "populacao_processada")

    def process_pib(self, input_file):
        """Processa PIB por UF (SIDRA tabela 5938)."""
        df = self._sidra_to_dataframe(input_file)

        df_clean = df \
            .withColumnRenamed("D1C", "codigo_uf") \
            .withColumnRenamed("D1N", "nome_uf") \
            .withColumnRenamed("D2N", "variavel") \
            .withColumnRenamed("D3N", "ano") \
            .withColumn("valor",
                        F.when(F.col("V").rlike(r"^\d+$"),
                               F.col("V").cast(DoubleType()))
                         .otherwise(F.lit(None))) \
            .withColumn("unidade", F.col("MN")) \
            .select("codigo_uf", "nome_uf", "variavel", "ano", "valor", "unidade")

        return self._save_parquet(df_clean, "pib_processado")

    def process_ideb(self, input_file):
        """Processa IDEB por município (formato longo do extrator INEP).

        Usa schema explícito: a inferência do createDataFrame falha
        quando a coluna mistura int/float/null (dados reais do INEP).
        """
        records = self._read_json_list(input_file)
        # Spark 4 é estrito: DoubleType aceita float, mas não int.
        # Normaliza para float/None antes do createDataFrame (robustez).
        records = [{"ideb": None if r["ideb"] is None else float(r["ideb"]),
                    **{k: v for k, v in r.items() if k != "ideb"}}
                   for r in records]

        schema = StructType([
            StructField("uf", StringType()),
            StructField("codigo_municipio", StringType()),
            StructField("nome_municipio", StringType()),
            StructField("rede", StringType()),
            StructField("ideb", DoubleType()),
            StructField("ano", IntegerType()),
        ])
        df = self.spark.createDataFrame(records, schema=schema)

        df_clean = df \
            .withColumn("ano_int", F.col("ano").cast(IntegerType())) \
            .withColumn("ideb_val", F.col("ideb").cast(DoubleType())) \
            .withColumn("id_estado",
                        F.substring(F.col("codigo_municipio"), 1, 2).cast(IntegerType())) \
            .select("codigo_municipio", "nome_municipio", "uf", "rede",
                    "ano_int", "ideb_val", "id_estado")

        return self._save_parquet(df_clean, "ideb_processado")

    # ---- Execução completa ----

    def run_all(self, raw_files: dict):
        """
        Executa todas as transformações.
        raw_files: {'estados': path, 'populacao': path, 'pib': path, 'ideb': path}
        """
        if raw_files.get("estados"):
            self.process_estados(raw_files["estados"])
        if raw_files.get("populacao"):
            self.process_populacao(raw_files["populacao"])
        if raw_files.get("pib"):
            self.process_pib(raw_files["pib"])
        if raw_files.get("ideb"):
            self.process_ideb(raw_files["ideb"])

    def stop(self):
        self.spark.stop()
        print("🛑 Spark Session finalizada")


if __name__ == "__main__":
    import glob

    # Pegar os arquivos mais recentes de cada tipo
    def latest(pattern):
        files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, pattern)))
        return files[-1] if files else None

    processor = SparkProcessor()
    processor.run_all({
        "estados": latest("ibge_estados_*.json"),
        "populacao": latest("ibge_populacao_*.json"),
        "pib": latest("ibge_pib_*.json"),
        "ideb": latest("inep_ideb_*.json"),
    })
    processor.stop()