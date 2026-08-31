# src/loading/postgres_loader.py
import os
import socket

import pandas as pd
import psycopg2

from src.utils.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,
    PROCESSED_DATA_DIR,
)


def _resolve_host():
    """Resolve o host do PostgreSQL para o ambiente atual.

    No docker-compose o serviço se chama 'postgres'; fora do Docker
    os dados do .env apontam para o mesmo nome, mas só acessível via
    localhost. Detecta por tentativa de conexão real (nada de chute).
    """
    if POSTGRES_HOST == "postgres":
        try:
            with socket.create_connection(("postgres", int(POSTGRES_PORT)), timeout=2):
                pass
            return "postgres"          # dentro do container Docker
        except OSError:
            return "localhost"         # rodando direto no host
    return POSTGRES_HOST


HOST = _resolve_host()


class PostgresLoader:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=10,
            )
            print("✅ Conectado ao PostgreSQL")
            return True
        except psycopg2.Error as e:
            print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
            return False

    def create_tables(self):
        if not self.connection:
            return

        cursor = self.connection.cursor()

        statements = [
            """
            CREATE TABLE IF NOT EXISTS dim_estado (
                id_estado INTEGER PRIMARY KEY,
                sigla VARCHAR(2) NOT NULL,
                nome VARCHAR(100) NOT NULL,
                sigla_regiao VARCHAR(2) NOT NULL,
                nome_regiao VARCHAR(50) NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fato_populacao (
                id SERIAL PRIMARY KEY,
                ano INTEGER NOT NULL,
                populacao NUMERIC NOT NULL,
                id_estado INTEGER REFERENCES dim_estado(id_estado)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fato_pib (
                id SERIAL PRIMARY KEY,
                ano INTEGER NOT NULL,
                variavel VARCHAR(200) NOT NULL,
                valor NUMERIC,
                unidade VARCHAR(50),
                id_estado INTEGER REFERENCES dim_estado(id_estado)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fato_ideb (
                id SERIAL PRIMARY KEY,
                codigo_municipio VARCHAR(7) NOT NULL,
                nome_municipio VARCHAR(120) NOT NULL,
                uf VARCHAR(2) NOT NULL,
                rede VARCHAR(20) NOT NULL,
                ano INTEGER NOT NULL,
                ideb NUMERIC(4,1),
                id_estado INTEGER REFERENCES dim_estado(id_estado)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_fato_ideb_ano ON fato_ideb (ano)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_fato_ideb_uf ON fato_ideb (uf)
            """,
        ]

        for sql in statements:
            cursor.execute(sql)

        self.connection.commit()
        print("✅ Tabelas criadas")

    def truncate(self, table):
        cursor = self.connection.cursor()
        cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        self.connection.commit()

    @staticmethod
    def _read_parquet(name):
        path = os.path.join(PROCESSED_DATA_DIR, name)
        return pd.read_parquet(path)

    @staticmethod
    def _to_nullable(series):
        """Converte NaN para None (pandas .where mantém NaN em numéricas)."""
        out = series.astype(object)
        out[out.isna()] = None
        return out

    def _bulk_insert(self, table, columns, rows, batch_size=5000):
        from psycopg2.extras import execute_batch

        cursor = self.connection.cursor()
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            execute_batch(cursor, sql, batch, page_size=1000)
            self.connection.commit()
            print(f"  ... {min(i + batch_size, len(rows))}/{len(rows)} em {table}")
        print(f"✅ {len(rows)} registros inseridos em {table}")

    # ---- Cargas ----

    def load_dim_estado(self):
        df = self._read_parquet("estados_processados")
        rows = list(df[["id_estado", "sigla", "nome", "sigla_regiao", "nome_regiao"]].itertuples(index=False, name=None))
        self.truncate("dim_estado")
        self._bulk_insert("dim_estado", ["id_estado", "sigla", "nome", "sigla_regiao", "nome_regiao"], rows)

    def load_fato_populacao(self):
        df = self._read_parquet("populacao_processada")
        df = df.rename(columns={"codigo_uf": "id_estado"})
        rows = list(df[["id_estado", "ano", "populacao"]].itertuples(index=False, name=None))
        self.truncate("fato_populacao")
        self._bulk_insert("fato_populacao", ["id_estado", "ano", "populacao"], rows)

    def load_fato_pib(self):
        df = self._read_parquet("pib_processado")
        df = df.rename(columns={"codigo_uf": "id_estado"})
        df["valor"] = self._to_nullable(df["valor"])
        rows = list(df[["id_estado", "ano", "variavel", "valor", "unidade"]].itertuples(index=False, name=None))
        self.truncate("fato_pib")
        self._bulk_insert("fato_pib", ["id_estado", "ano", "variavel", "valor", "unidade"], rows)

    def load_fato_ideb(self):
        df = self._read_parquet("ideb_processado")
        df = df.rename(columns={"ano_int": "ano", "ideb_val": "ideb"})
        df["ideb"] = self._to_nullable(df["ideb"])
        rows = list(df[["codigo_municipio", "nome_municipio", "uf", "rede", "ano", "ideb", "id_estado"]]
                    .itertuples(index=False, name=None))
        self.truncate("fato_ideb")
        self._bulk_insert("fato_ideb", ["codigo_municipio", "nome_municipio", "uf", "rede", "ano", "ideb", "id_estado"], rows)

    def close(self):
        if self.connection:
            self.connection.close()
            print("🔌 Conexão fechada")


if __name__ == "__main__":
    loader = PostgresLoader()
    if loader.connect():
        loader.create_tables()
        loader.load_dim_estado()
        loader.load_fato_populacao()
        loader.load_fato_pib()
        loader.load_fato_ideb()
        loader.close()