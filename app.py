"""Punto de entrada: solo arranque y cableado (como server.js en el ejemplo).

Aquí se crean los repositorios y se inyectan en los servicios.
"""
import os

from flask import Flask

from src.aplicacion.habitacion_service import HabitacionService
from src.aplicacion.reserva_service import ReservaService
from src.aplicacion.usuario_service import UsuarioService
from src.infraestructura.hasher import BcryptHasher
from src.persistencia.habitacion_repository import HabitacionRepository
from src.persistencia.reserva_repository import ReservaRepository
from src.persistencia.usuario_repository import UsuarioRepository
from src.presentacion.hotel_routes import crear_rutas


def crear_app():
    usuario_repo = UsuarioRepository()
    habitacion_repo = HabitacionRepository()
    reserva_repo = ReservaRepository()

    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.register_blueprint(crear_rutas(
        UsuarioService(usuario_repo, BcryptHasher()),
        HabitacionService(habitacion_repo),
        ReservaService(reserva_repo, habitacion_repo, usuario_repo),
    ))
    return app


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "3000"))
    crear_app().run(port=puerto, debug=True)
