"""Caso de uso RF-02: buscar habitaciones disponibles."""
from src.dominio import reglas_reserva as reglas


class HabitacionService:

    def __init__(self, habitacion_repo):
        self.habitacion_repo = habitacion_repo

    def buscar_disponibles(self, fecha_inicio, fecha_fin, tipo=None):
        inicio = reglas.convertir_fecha(fecha_inicio, "fecha de inicio")
        fin = reglas.convertir_fecha(fecha_fin, "fecha de fin")
        reglas.validar_rango_fechas(inicio, fin)

        habitaciones = self.habitacion_repo.listar_disponibles(inicio, fin, tipo)
        return [{**h, "precio": float(h["precio"])} for h in habitaciones]
