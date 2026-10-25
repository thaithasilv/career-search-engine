"""
Conexao com o banco de dados (MySQL), sem nenhuma senha escrita no codigo.

As credenciais vem, nesta ordem:
  1) do arquivo .env na mesma pasta (uso local; o .env esta no .gitignore)
  2) de variaveis de ambiente do sistema
  3) do st.secrets do Streamlit (.streamlit/secrets.toml ou Streamlit Cloud)

Instalar:  pip install python-dotenv mysql-connector-python
"""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OBRIGATORIAS = ("DB_USER", "DB_PASSWORD")
PADROES = {"DB_HOST": "localhost", "DB_NAME": "onetdatabase"}


class ConfigBancoAusente(RuntimeError):
    """Credenciais do banco nao configuradas."""


def _ler(nome):
    valor = os.getenv(nome)
    if valor:
        return valor.strip()
    try:  # so funciona quando roda via "streamlit run"
        import streamlit as st
        if nome in st.secrets:
            return str(st.secrets[nome]).strip()
    except Exception:
        pass
    return PADROES.get(nome)


def _config():
    cfg = {nome: _ler(nome) for nome in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")}
    faltando = [n for n in OBRIGATORIAS if not cfg[n]]
    if faltando:
        raise ConfigBancoAusente(
            f"Faltam as variaveis {', '.join(faltando)}. "
            "Copie o arquivo .env.example para .env e preencha seus dados."
        )
    return {
        "host": cfg["DB_HOST"],
        "user": cfg["DB_USER"],
        "password": cfg["DB_PASSWORD"],
        "database": cfg["DB_NAME"],
    }


def conectar():
    """Abre uma conexao nova com o MySQL. Lembre de fechar com conn.close()."""
    return mysql.connector.connect(**_config())
