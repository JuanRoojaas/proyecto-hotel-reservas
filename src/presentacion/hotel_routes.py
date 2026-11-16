"""Capa HTTP: extrae los datos de la petición, delega en la aplicación y
traduce resultados o errores de negocio a códigos HTTP. Aquí no hay SQL
ni reglas de negocio.

Formato de error (igual para toda la API):
    {"detail": "<mensaje para el usuario>", "codigo": "<CODIGO_DE_NEGOCIO>"}
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from src.dominio.reglas_reserva import ErrorDeNegocio

CODIGO_HTTP = {
    # 400: la entrada no cumple el contrato
    "DATOS_FALTANTES": 400,
    "ID_INVALIDO": 400,
    "CORREO_INVALIDO": 400,
    "PASSWORD_DEBIL": 400,
    "FECHA_INVALIDA": 400,
    "FECHA_PASADA": 400,
    "RANGO_INVALIDO": 400,
    # 404: el recurso referenciado no existe
    "USUARIO_NO_ENCONTRADO": 404,
    "HABITACION_NO_ENCONTRADA": 404,
    "RESERVA_NO_ENCONTRADA": 404,
    # 409: choca con el estado actual de los datos
    "CORREO_REGISTRADO": 409,
    "HABITACION_OCUPADA": 409,
    "HABITACION_NO_OPERATIVA": 409,
}

MENSAJES_HTTP = {
    404: ("RUTA_NO_ENCONTRADA", "La ruta solicitada no existe"),
    405: ("METODO_NO_PERMITIDO", "Método HTTP no permitido en esta ruta"),
}


def _error(detail, codigo, estado):
    return jsonify({"detail": detail, "codigo": codigo}), estado


def registrar_manejadores_de_error(app):
    """Todas las respuestas de error salen en JSON, también las de Flask."""

    @app.errorhandler(ErrorDeNegocio)
    def error_de_negocio(error):
        return _error(error.mensaje, error.codigo, CODIGO_HTTP.get(error.codigo, 400))

    @app.errorhandler(HTTPException)
    def error_http(error):
        codigo, detail = MENSAJES_HTTP.get(error.code, ("ERROR_HTTP", error.description))
        return _error(detail, codigo, error.code)

    @app.errorhandler(Exception)
    def error_inesperado(error):
        # Fallo interno: se registra completo en el servidor y al cliente
        # solo se le dice que algo falló, sin detalles técnicos.
        app.logger.exception("Error interno no controlado")
        return _error("Error interno del servidor", "ERROR_INTERNO", 500)


def crear_rutas(usuario_service, habitacion_service, reserva_service):
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.get("/salud")
    def salud():
        return jsonify({"estado": "ok", "hora": datetime.now(timezone.utc).isoformat()})

    # RF-01 Registro de usuario
    @api.post("/usuarios")
    def registrar_usuario():
        return jsonify(usuario_service.registrar(request.get_json(silent=True) or {})), 201

    # RF-02 Búsqueda  ej: /api/habitaciones/disponibles?fecha_inicio=2026-12-10&fecha_fin=2026-12-12&tipo=suite
    @api.get("/habitaciones/disponibles")
    def buscar_disponibles():
        return jsonify(habitacion_service.buscar_disponibles(
            request.args.get("fecha_inicio"), request.args.get("fecha_fin"), request.args.get("tipo")
        ))

    # RF-03 Crear la reserva
    @api.post("/reservas")
    def crear_reserva():
        return jsonify(reserva_service.crear(request.get_json(silent=True) or {})), 201

    # RF-03 Consultar la reserva creada (el servicio valida que el id sea entero positivo)
    @api.get("/reservas/<id_reserva>")
    def consultar_reserva(id_reserva):
        return jsonify(reserva_service.consultar(id_reserva))

    return api
