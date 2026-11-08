"""Caso de uso RF-03: crear la reserva (y consultarla por id).

Receta: validar datos -> validar fechas -> verificar huésped y habitación
-> verificar que la habitación esté operativa -> verificar disponibilidad
-> calcular total -> guardar.
"""
from src.dominio import reglas_reserva as reglas


class ReservaService:

    def __init__(self, reserva_repo, habitacion_repo, usuario_repo):
        self.reserva_repo = reserva_repo
        self.habitacion_repo = habitacion_repo
        self.usuario_repo = usuario_repo

    def crear(self, datos):
        reglas.validar_datos_reserva(datos)
        inicio = reglas.convertir_fecha(datos["fecha_inicio"], "fecha de inicio")
        fin = reglas.convertir_fecha(datos["fecha_fin"], "fecha de fin")
        reglas.validar_rango_fechas(inicio, fin)

        usuario = self.usuario_repo.buscar_por_id(datos["id_usuario"])
        reglas.validar_existe(usuario, "USUARIO_NO_ENCONTRADO", "El huésped no existe")

        habitacion = self.habitacion_repo.buscar_por_id(datos["id_habitacion"])
        reglas.validar_existe(habitacion, "HABITACION_NO_ENCONTRADA", "La habitación no existe")
        reglas.validar_habitacion_operativa(habitacion)

        ocupada = self.habitacion_repo.esta_ocupada(habitacion["id_habitacion"], inicio, fin)
        reglas.validar_habitacion_libre(ocupada)

        reserva = {"id_usuario": usuario["id_usuario"], "id_habitacion": habitacion["id_habitacion"],
                   "fecha_inicio": inicio, "fecha_fin": fin}
        # Si otra solicitud ganó la carrera entre la verificación y el guardado,
        # la restricción UNIQUE de la base lo detecta y el repositorio lanza
        # ErrorDeNegocio('HABITACION_OCUPADA').
        id_reserva = self.reserva_repo.guardar(reserva, reglas.noches_de_estancia(inicio, fin))
        return {"mensaje": "Reserva confirmada", "id_reserva": id_reserva, "estado": "confirmada",
                "habitacion": habitacion["numero"], "noches": (fin - inicio).days,
                "total": reglas.calcular_total(habitacion["precio"], inicio, fin)}

    def consultar(self, id_reserva):
        reserva = self.reserva_repo.buscar_por_id(id_reserva)
        reglas.validar_existe(reserva, "RESERVA_NO_ENCONTRADA", "No existe una reserva con ese id")
        total = reglas.calcular_total(reserva["precio"], reserva["fecha_inicio"], reserva["fecha_fin"])
        return {
            **reserva,
            "precio": float(reserva["precio"]),
            "fecha_inicio": reserva["fecha_inicio"].isoformat(),
            "fecha_fin": reserva["fecha_fin"].isoformat(),
            "total": total,
        }
