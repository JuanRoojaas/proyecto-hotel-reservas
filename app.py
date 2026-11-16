"""Punto de entrada: solo arranque y cableado (como server.js en el ejemplo).

Aquí se crean los repositorios y se inyectan en los servicios.
"""
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from src.aplicacion.habitacion_service import HabitacionService
from src.aplicacion.reserva_service import ReservaService
from src.aplicacion.usuario_service import UsuarioService
from src.infraestructura.hasher import BcryptHasher
from src.persistencia.habitacion_repository import HabitacionRepository
from src.persistencia.reserva_repository import ReservaRepository
from src.persistencia.usuario_repository import UsuarioRepository
from src.presentacion.hotel_routes import crear_rutas, registrar_manejadores_de_error

load_dotenv()

# Origen de la interfaz de la semana 3 (por defecto, Live Server de VS Code).
ORIGENES_CORS = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")


def crear_app():
    usuario_repo = UsuarioRepository()
    habitacion_repo = HabitacionRepository()
    reserva_repo = ReservaRepository()

    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    CORS(app, resources={r"/api/*": {"origins": ORIGENES_CORS}})
    registrar_manejadores_de_error(app)
    app.register_blueprint(crear_rutas(
        UsuarioService(usuario_repo, BcryptHasher()),
        HabitacionService(habitacion_repo),
        ReservaService(reserva_repo, habitacion_repo, usuario_repo),
    ))
    return app


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "3000"))
    crear_app().run(port=puerto, debug=True)
