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


def reiniciar_base():
    """Borra y recrea la base: 01_schema.sql + 02_seed.sql (estado inicial conocido)."""
    try:
        ejecutar_script(RAIZ / "db" / "01_schema.sql")
        ejecutar_script(RAIZ / "db" / "02_seed.sql")
    except mysql.connector.Error as e:
        # 2003/2005: servidor apagado o host incorrecto · 1045: usuario o contraseña incorrectos
        if getattr(e, "errno", None) in (2003, 2005, 1045):
            pytest.skip(f"No hay conexión a MySQL ({e}). ¿Está encendido el servidor? Revise el archivo .env")
        raise  # cualquier otro error (p. ej. de sintaxis en los scripts) debe fallar


@pytest.fixture(scope="module")
def bd_reiniciada():
    """Una base limpia por archivo de pruebas (pruebas de persistencia)."""
    reiniciar_base()


@pytest.fixture
def bd_limpia():
    """Una base limpia por CADA prueba: los escenarios de API no dependen entre sí."""
    reiniciar_base()


@pytest.fixture
def cliente(bd_limpia):
    """Cliente HTTP de prueba de Flask: atraviesa API -> servicio -> repositorio -> MySQL."""
    from app import crear_app
    return crear_app().test_client()


def consultar_bd(sql, parametros=()):
    """Lee la base desde una conexión NUEVA, independiente de la API (para verificar)."""
    cnx = mysql.connector.connect(**CONFIG)
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(sql, parametros)
    filas = cursor.fetchall()
    cursor.close()
    cnx.close()
    return filas


def contar(tabla, where="1=1", parametros=()):
    return consultar_bd(f"SELECT COUNT(*) AS n FROM {tabla} WHERE {where}", parametros)[0]["n"]
