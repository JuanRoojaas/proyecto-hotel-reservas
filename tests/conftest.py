"""Utilidades de prueba: recrea la base con estado inicial conocido."""
from pathlib import Path

import mysql.connector
import pytest

from src.persistencia.db import CONFIG

RAIZ = Path(__file__).resolve().parent.parent


def ejecutar_script(ruta):
    config_sin_bd = {k: v for k, v in CONFIG.items() if k != "database"}
    cnx = mysql.connector.connect(**config_sin_bd)
    cursor = cnx.cursor()
    lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    sql = "\n".join(l for l in lineas if not l.strip().startswith("--"))  # quita comentarios
    for sentencia in (s.strip() for s in sql.split(";")):
        if sentencia:
            cursor.execute(sentencia)
    cnx.commit()
    cursor.close()
    cnx.close()


@pytest.fixture(scope="module")
def bd_reiniciada():
    """Borra y recrea la base (01_schema.sql + 02_seed.sql) antes de cada módulo de pruebas."""
    try:
        ejecutar_script(RAIZ / "db" / "01_schema.sql")
        ejecutar_script(RAIZ / "db" / "02_seed.sql")
    except (mysql.connector.errors.InterfaceError, mysql.connector.errors.ProgrammingError) as e:
        if getattr(e, "errno", None) in (1064,):  # error de sintaxis en los scripts: que falle
            raise
        pytest.skip(f"No hay conexión a MySQL ({e}). Revise el archivo .env")
