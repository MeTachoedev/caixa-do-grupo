"""Regras de saída aplicadas pelo próprio Streamlit."""

import tomllib
from pathlib import Path


def test_m002_native_dataframe_export_is_disabled():
    """M-002: somente o CSV tratado pelo app pode ser exportado pela tela."""
    config = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    with config.open("rb") as handle:
        values = tomllib.load(handle)
    assert values["client"]["disableDataExport"] is True
