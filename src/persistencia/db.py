"""Conexión a MySQL. Único lugar que conoce las credenciales (vienen del .env)."""
import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hotel_corte_vertical"),
}


@contextmanager
def obtener_conexion():
    """Abre una conexión nueva y la cierra SIEMPRE al salir del bloque `with`.

    Quién confirma o revierte: el método del repositorio que escribe
    (commit si todo salió bien, rollback ante cualquier error).
    """
    conexion = mysql.connector.connect(**CONFIG)
    try:
        yield conexion
    finally:
        conexion.close()
