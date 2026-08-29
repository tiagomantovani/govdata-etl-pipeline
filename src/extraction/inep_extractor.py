# src/extraction/inep_extractor.py
import json
import os
import requests
import urllib3
import zipfile
from datetime import datetime

import pandas as pd

from src.utils.config import DOWNLOADS_DIR, RAW_DATA_DIR

# O servidor download.inep.gov.br entrega uma cadeia de certificados
# incompleta, que falha na validação via OpenSSL (certifi). Como é um
# download de dado público, usamos verify=False.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL oficial dos arquivos de divulgação do IDEB (download.inep.gov.br)
IDEB_BASE_URL = "https://download.inep.gov.br/ideb/resultados"

# Cabeçalho dos arquivos de municípios: a linha técnica (ex.: CO_MUNICIPIO)
# começa no índice 9 (as linhas 0-8 são título/contexto)
IDEB_MUNICIPIOS_HEADER_ROW = 9

# Edições do IDEB disponíveis nos arquivos por município
IDEB_ANOS = [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025]


class INEPExtractor:
    def __init__(self):
        self.base_url = IDEB_BASE_URL

    def _download_ideb(self, etapa, ano):
        """Baixa e extrai o arquivo xlsx de IDEB por município."""
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

        xlsx_path = os.path.join(DOWNLOADS_DIR, f"ideb_{etapa}_municipios_{ano}.xlsx")
        if os.path.exists(xlsx_path):
            print(f"♻️  Arquivo já existe: {xlsx_path}")
            return xlsx_path

        # Arquivos a partir de 2025 vêm em .zip (xlsx + ods + md5)
        for ext in (".zip", ".xlsx"):
            url = f"{self.base_url}/divulgacao_{etapa}_municipios_{ano}{ext}"
            archive_path = os.path.join(DOWNLOADS_DIR, os.path.basename(url))
            try:
                print(f"⬇️  Baixando {url}")
                response = requests.get(url, timeout=120, verify=False)
                response.raise_for_status()
                with open(archive_path, "wb") as f:
                    f.write(response.content)

                if url.endswith(".zip"):
                    with zipfile.ZipFile(archive_path) as zf:
                        names = [n for n in zf.namelist() if n.endswith(".xlsx")]
                        if not names:
                            raise RuntimeError("Nenhum xlsx dentro do zip")
                        zf.extract(names[0], DOWNLOADS_DIR)
                        extracted = os.path.join(DOWNLOADS_DIR, names[0])
                    os.rename(extracted, xlsx_path)
                    os.remove(archive_path)
                else:
                    os.rename(archive_path, xlsx_path)

                print(f"✅ Arquivo salvo em: {xlsx_path}")
                return xlsx_path
            except requests.exceptions.RequestException:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                continue

        raise RuntimeError(f"Não foi possível baixar IDEB {etapa}/{ano}")

    def get_ideb_municipios(self, etapa="anos_iniciais", ano=2025):
        """Extrai IDEB por município e salva em formato longo (JSON).

        Formato longo: (codigo_municipio, nome_municipio, uf, rede, ano, ideb)
        """
        xlsx_path = self._download_ideb(etapa, ano)

        df = pd.read_excel(xlsx_path, header=IDEB_MUNICIPIOS_HEADER_ROW)
        df = df[df["CO_MUNICIPIO"].notna()].copy()

        df["CO_MUNICIPIO"] = (
            df["CO_MUNICIPIO"].astype(str).str.replace(r"\.0$", "", regex=True)
        )

        cols_ideb = [f"VL_OBSERVADO_{y}" for y in IDEB_ANOS if f"VL_OBSERVADO_{y}" in df.columns]

        long = pd.melt(
            df[["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"] + cols_ideb],
            id_vars=["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"],
            var_name="col",
            value_name="ideb",
        )
        long["ano"] = long["col"].str.extract(r"(\d{4})").astype(int)
        long.drop(columns="col", inplace=True)

        # Sentinela "-"/"..." = IDEB não divulgado; força coluna numérica
        # (pandas preserva int/float do Excel; JSON deve ter só floats ou null)
        long["ideb"] = pd.to_numeric(long["ideb"], errors="coerce")
        # Substitui NaN por None (pandas .where mantém NaN em colunas numéricas)
        series = long["ideb"].astype(object)
        series[series.isna()] = None
        long["ideb"] = series

        records = long.rename(columns={
            "SG_UF": "uf",
            "CO_MUNICIPIO": "codigo_municipio",
            "NO_MUNICIPIO": "nome_municipio",
            "REDE": "rede",
        }).to_dict(orient="records")

        filename = (f"inep_ideb_municipios_{etapa}_{ano}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        filepath = os.path.join(RAW_DATA_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"✅ IDEB {etapa} {ano} salvo em: {filepath} ({len(records)} registros)")
        return records


if __name__ == "__main__":
    extractor = INEPExtractor()
    extractor.get_ideb_municipios("anos_iniciais", 2025)