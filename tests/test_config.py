# tests/test_config.py
"""Valida a configuração central do projeto (caminhos e defaults)."""
import os

from src.utils.config import (
    BASE_DIR, DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, DOWNLOADS_DIR,
    POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER,
)


def test_dirs_exist():
    assert os.path.isdir(DATA_DIR)
    assert os.path.isdir(RAW_DATA_DIR)
    assert os.path.isdir(PROCESSED_DATA_DIR)
    assert os.path.isdir(DOWNLOADS_DIR)


def test_base_dir_is_project_root():
    assert os.path.basename(DATA_DIR) == "data"
    assert os.path.dirname(DATA_DIR) == BASE_DIR


def test_postgres_defaults():
    # Valores padrão quando .env não existe (ex.: CI)
    assert POSTGRES_DB == "govdata"
    assert POSTGRES_USER == "postgres"
    assert isinstance(POSTGRES_HOST, str)