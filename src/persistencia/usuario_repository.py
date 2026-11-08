"""Acceso a datos de usuarios. Todo el SQL de la tabla `usuarios` vive aquí."""
from mysql.connector import errorcode
from mysql.connector.errors import IntegrityError

from src.dominio.reglas_reserva import ErrorDeNegocio
from src.persistencia.db import obtener_conexion

COLUMNAS_PUBLICAS = "id_usuario, nombre, apellido, fecha_nacimiento, correo, rol, verificado"


class UsuarioRepository:

    def guardar(self, nombre, apellido, fecha_nacimiento, correo, password_hash):
        """Inserta el usuario (rol 'huesped' por defecto) y retorna su id real."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor()
            try:
                cursor.execute(
                    "INSERT INTO usuarios (nombre, apellido, fecha_nacimiento, correo, password) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (nombre, apellido, fecha_nacimiento, correo, password_hash),
                )
                cnx.commit()
                return cursor.lastrowid
            except IntegrityError as e:
                cnx.rollback()
                if e.errno == errorcode.ER_DUP_ENTRY:
                    # La restricción UNIQUE(correo) de la base refuerza la regla del negocio.
                    raise ErrorDeNegocio("CORREO_REGISTRADO", "Ya existe una cuenta con ese correo") from e
                raise
            finally:
                cursor.close()

    def buscar_por_correo(self, correo):
        """Retorna el usuario (dict, incluye el hash para un futuro login) o None."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(
                f"SELECT {COLUMNAS_PUBLICAS}, password FROM usuarios WHERE correo = %s", (correo,)
            )
            fila = cursor.fetchone()
            cursor.close()
            return fila

    def buscar_por_id(self, id_usuario):
        """Retorna el usuario (dict, sin el hash) o None si no existe."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(f"SELECT {COLUMNAS_PUBLICAS} FROM usuarios WHERE id_usuario = %s", (id_usuario,))
            fila = cursor.fetchone()
            cursor.close()
            return fila
