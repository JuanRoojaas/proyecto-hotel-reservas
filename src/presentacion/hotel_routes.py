"""Capa HTTP: extrae los datos de la petición, delega en la aplicación y
traduce resultados o errores de negocio a códigos HTTP. Aquí no hay SQL
ni reglas de negocio.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from src.dominio.reglas_reserva import ErrorDeNegocio

CODIGO_HTTP = {
    "DATOS_FALTANTES": 400,
    "CORREO_INVALIDO": 400,
    "PASSWORD_DEBIL": 400,
    "FECHA_INVALIDA": 400,
    "FECHA_PASADA": 400,
    "RANGO_INVALIDO": 400,
    "USUARIO_NO_ENCONTRADO": 404,
    "HABITACION_NO_ENCONTRADA": 404,
    "RESERVA_NO_ENCONTRADA": 404,
    "CORREO_REGISTRADO": 409,
    "HABITACION_NO_OPERATIVA": 409,
    "HABITACION_OCUPADA": 409,
}


def crear_rutas(usuario_service, habitacion_service, reserva_service):
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.errorhandler(ErrorDeNegocio)
    def manejar_error_negocio(error):
        return jsonify({"error": error.mensaje, "codigo": error.codigo}), CODIGO_HTTP.get(error.codigo, 400)

    @api.errorhandler(Exception)
    def manejar_error_inesperado(error):
        print("Error inesperado:", error)
        return jsonify({"error": "Error interno del servidor"}), 500

    @api.get("/salud")
    def salud():
        return jsonify({"estado": "ok", "hora": datetime.now(timezone.utc).isoformat()})

    # RF-01
    @api.post("/usuarios")
    def registrar_usuario():
        return jsonify(usuario_service.registrar(request.get_json(silent=True) or {})), 201

    # RF-02  ej: /api/habitaciones/disponibles?inicio=2026-12-10&fin=2026-12-12&tipo=suite
    @api.get("/habitaciones/disponibles")
    def buscar_disponibles():
        return jsonify(habitacion_service.buscar_disponibles(
            request.args.get("inicio"), request.args.get("fin"), request.args.get("tipo")
        ))

    # RF-03
    @api.post("/reservas")
    def crear_reserva():
        return jsonify(reserva_service.crear(request.get_json(silent=True) or {})), 201

    @api.get("/reservas/<int:id_reserva>")
    def consultar_reserva(id_reserva):
        return jsonify(reserva_service.consultar(id_reserva))

    return api
