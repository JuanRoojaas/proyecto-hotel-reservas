"""Acceso a datos de habitaciones. Todo el SQL de `habitaciones` vive aquí."""
from src.persistencia.db import obtener_conexion

COLUMNAS = "h.id_habitacion, h.numero, h.tipo, h.precio, h.estado, h.descripcion"

# Habitaciones con alguna noche ocupada dentro de [inicio, fin): la noche de salida no cuenta.
SUBCONSULTA_OCUPADAS = (
    "SELECT rn.id_habitacion FROM reservas_noches rn "
    "WHERE rn.fecha >= %s AND rn.fecha < %s"
)


class HabitacionRepository:

    def buscar_por_id(self, id_habitacion):
        """Retorna la habitación (dict) o None si no existe."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(f"SELECT {COLUMNAS} FROM habitaciones h WHERE h.id_habitacion = %s", (id_habitacion,))
            fila = cursor.fetchone()
            cursor.close()
            return fila

    def listar_disponibles(self, inicio, fin, tipo=None):
        """RF-02: habitaciones operativas sin noches ocupadas en el rango (filtro opcional por tipo)."""
        sql = (
            f"SELECT {COLUMNAS} FROM habitaciones h "
            f"WHERE h.estado = 'disponible' AND h.id_habitacion NOT IN ({SUBCONSULTA_OCUPADAS})"
        )
        parametros = [inicio, fin]
        if tipo:
            sql += " AND h.tipo = %s"
            parametros.append(tipo)
        sql += " ORDER BY CAST(h.numero AS UNSIGNED)"
        with obtener_conexion() as cnx:
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(sql, parametros)
            filas = cursor.fetchall()
            cursor.close()
            return filas

    def esta_ocupada(self, id_habitacion, inicio, fin):
        """RF-03: el hecho con el que el negocio decide la disponibilidad."""
        with obtener_conexion() as cnx:
            cursor = cnx.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM reservas_noches "
                "WHERE id_habitacion = %s AND fecha >= %s AND fecha < %s",
                (id_habitacion, inicio, fin),
            )
            (cantidad,) = cursor.fetchone()
            cursor.close()
            return cantidad > 0
