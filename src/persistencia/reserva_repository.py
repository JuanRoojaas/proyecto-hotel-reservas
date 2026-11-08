"""Acceso a datos de reservas. Todo el SQL de `reservas` y `reservas_noches` vive aquí."""
from mysql.connector import errorcode
from mysql.connector.errors import IntegrityError

from src.dominio.reglas_reserva import ErrorDeNegocio
from src.persistencia.db import obtener_conexion


class ReservaRepository:

    def guardar(self, reserva, noches):
        """Guarda la reserva y sus noches en UNA transacción y retorna el id real.

        Si cualquier INSERT falla (por ejemplo, una noche ya ocupada que viola
        UNIQUE(id_habitacion, fecha)), se hace rollback y no queda nada a medias
        (RNF-02).
        """
        with obtener_conexion() as cnx:
            cursor = cnx.cursor()
            try:
                cnx.start_transaction()
                cursor.execute(
                    "INSERT INTO reservas (id_usuario, id_habitacion, fecha_inicio, fecha_fin) "
                    "VALUES (%s, %s, %s, %s)",
                    (reserva["id_usuario"], reserva["id_habitacion"],
                     reserva["fecha_inicio"], reserva["fecha_fin"]),
                )
                id_reserva = cursor.lastrowid
                cursor.executemany(
                    "INSERT INTO reservas_noches (id_reserva, id_habitacion, fecha) VALUES (%s, %s, %s)",
                    [(id_reserva, reserva["id_habitacion"], noche) for noche in noches],
                )
                cnx.commit()
                return id_reserva
            except IntegrityError as e:
                cnx.rollback()
                if e.errno == errorcode.ER_DUP_ENTRY:
                    raise ErrorDeNegocio(
                        "HABITACION_OCUPADA", "La habitación ya está reservada en esas fechas"
                    ) from e
                raise
            except Exception:
                cnx.rollback()
                raise
            finally:
                cursor.close()

    def buscar_por_id(self, id_reserva):
        """Retorna la reserva (dict, con número y precio de la habitación) o None si no existe."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(
                "SELECT r.id_reserva, r.id_usuario, r.id_habitacion, h.numero, h.tipo, h.precio, "
                "r.fecha_inicio, r.fecha_fin, r.estado "
                "FROM reservas r JOIN habitaciones h ON h.id_habitacion = r.id_habitacion "
                "WHERE r.id_reserva = %s",
                (id_reserva,),
            )
            fila = cursor.fetchone()
            cursor.close()
            return fila

    def contar(self):
        """Apoyo para las pruebas de integridad (RNF-02)."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor()
            cursor.execute("SELECT (SELECT COUNT(*) FROM reservas), (SELECT COUNT(*) FROM reservas_noches)")
            reservas, noches = cursor.fetchone()
            cursor.close()
            return {"reservas": reservas, "noches": noches}
