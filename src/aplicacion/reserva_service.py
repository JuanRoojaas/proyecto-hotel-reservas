"""Casos de uso de reservas.

RF-03 Crear la reserva. Receta: validar datos -> validar IDs y fechas
-> verificar huésped y habitación -> verificar que la habitación esté operativa
-> verificar disponibilidad -> guardar (el repositorio confirma la transacción)
-> devolver la reserva tal como quedó guardada.

Consultar la reserva por id sirve para comprobar por API lo que RF-03 guardó.
"""
from src.dominio import reglas_reserva as reglas


class ReservaService:

    def __init__(self, reserva_repo, habitacion_repo, usuario_repo):
        self.reserva_repo = reserva_repo
        self.habitacion_repo = habitacion_repo
        self.usuario_repo = usuario_repo

    def crear(self, datos):
        reglas.validar_datos_reserva(datos)
        id_usuario = reglas.validar_id(datos["id_usuario"], "id_usuario")
        id_habitacion = reglas.validar_id(datos["id_habitacion"], "id_habitacion")
        inicio = reglas.convertir_fecha(datos["fecha_inicio"], "fecha de inicio")
        fin = reglas.convertir_fecha(datos["fecha_fin"], "fecha de fin")
        reglas.validar_rango_fechas(inicio, fin)

        usuario = self.usuario_repo.buscar_por_id(id_usuario)
        reglas.validar_existe(usuario, "USUARIO_NO_ENCONTRADO", "El huésped no existe")

        habitacion = self.habitacion_repo.buscar_por_id(id_habitacion)
        reglas.validar_existe(habitacion, "HABITACION_NO_ENCONTRADA", "La habitación no existe")
        reglas.validar_habitacion_operativa(habitacion)

        ocupada = self.habitacion_repo.esta_ocupada(id_habitacion, inicio, fin)
        reglas.validar_habitacion_libre(ocupada)

        reserva = {"id_usuario": id_usuario, "id_habitacion": id_habitacion,
                   "fecha_inicio": inicio, "fecha_fin": fin}
        # Si otra solicitud ganó la carrera entre la verificación y el guardado,
        # la restricción UNIQUE de la base lo detecta y el repositorio lanza
        # ErrorDeNegocio('HABITACION_OCUPADA'), que la API traduce a 409.
        id_reserva = self.reserva_repo.guardar(reserva, reglas.noches_de_estancia(inicio, fin))

        # La escritura ya está confirmada: se responde con lo que quedó guardado.
        return self.consultar(id_reserva)

    def consultar(self, id_reserva):
        id_reserva = reglas.validar_id(id_reserva, "id_reserva")
        reserva = self.reserva_repo.buscar_por_id(id_reserva)
        reglas.validar_existe(reserva, "RESERVA_NO_ENCONTRADA", "La reserva no existe")
        inicio, fin = reserva["fecha_inicio"], reserva["fecha_fin"]
        return {
            "id_reserva": reserva["id_reserva"],
            "id_usuario": reserva["id_usuario"],
            "id_habitacion": reserva["id_habitacion"],
            "numero_habitacion": reserva["numero"],
            "tipo": reserva["tipo"],
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "noches": (fin - inicio).days,
            "precio_noche": float(reserva["precio"]),
            "total": reglas.calcular_total(reserva["precio"], inicio, fin),
            "estado": reserva["estado"],
        }
