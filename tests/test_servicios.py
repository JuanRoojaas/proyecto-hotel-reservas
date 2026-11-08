"""RNF-04 (adelanto de semana 2): servicios probados con repositorios simulados,
SIN conexión a MySQL. Funciona porque los repositorios se inyectan por constructor.
"""
from datetime import date, timedelta

import pytest

from src.aplicacion.reserva_service import ReservaService
from src.aplicacion.usuario_service import UsuarioService
from src.dominio.reglas_reserva import ErrorDeNegocio

INICIO = (date.today() + timedelta(days=30)).isoformat()
FIN = (date.today() + timedelta(days=32)).isoformat()


class UsuarioRepoFalso:
    def __init__(self):
        self.usuarios = {1: {"id_usuario": 1, "correo": "ana@correo.com"}}

    def buscar_por_correo(self, correo):
        return next((u for u in self.usuarios.values() if u["correo"] == correo), None)

    def buscar_por_id(self, id_usuario):
        return self.usuarios.get(id_usuario)

    def guardar(self, nombre, apellido, fecha_nacimiento, correo, password_hash):
        nuevo_id = len(self.usuarios) + 1
        self.usuarios[nuevo_id] = {"id_usuario": nuevo_id, "correo": correo, "password": password_hash}
        return nuevo_id


class HasherFalso:
    def generar(self, password):
        return "hash-" + password[::-1]


class HabitacionRepoFalso:
    def __init__(self, ocupada=False, estado="disponible"):
        self.ocupada = ocupada
        self.estado = estado

    def buscar_por_id(self, id_habitacion):
        if id_habitacion != 1:
            return None
        return {"id_habitacion": 1, "numero": "1", "precio": 120000, "estado": self.estado}

    def esta_ocupada(self, id_habitacion, inicio, fin):
        return self.ocupada


class ReservaRepoFalso:
    def __init__(self):
        self.guardadas = []

    def guardar(self, reserva, noches):
        self.guardadas.append((reserva, noches))
        return 100


# ------------------------------------------------ RF-01
def test_registrar_usuario_valido_no_expone_password():
    servicio = UsuarioService(UsuarioRepoFalso(), HasherFalso())
    r = servicio.registrar({"nombre": "Luis", "apellido": "Pérez", "correo": "luis@correo.com",
                            "password": "Hotel2026!"})
    assert r["id_usuario"] == 2
    assert "password" not in r


def test_registrar_correo_repetido_se_rechaza():
    servicio = UsuarioService(UsuarioRepoFalso(), HasherFalso())
    with pytest.raises(ErrorDeNegocio) as e:
        servicio.registrar({"nombre": "Ana", "apellido": "G", "correo": "ana@correo.com",
                            "password": "Hotel2026!"})
    assert e.value.codigo == "CORREO_REGISTRADO"


# ------------------------------------------------ RF-03
def _datos(**cambios):
    return {"id_usuario": 1, "id_habitacion": 1, "fecha_inicio": INICIO, "fecha_fin": FIN, **cambios}


def test_crear_reserva_valida_calcula_total():
    repo = ReservaRepoFalso()
    r = ReservaService(repo, HabitacionRepoFalso(), UsuarioRepoFalso()).crear(_datos())
    assert r["id_reserva"] == 100 and r["total"] == 240000.00 and r["noches"] == 2
    assert len(repo.guardadas[0][1]) == 2


def test_crear_reserva_habitacion_ocupada_se_rechaza():
    repo = ReservaRepoFalso()
    with pytest.raises(ErrorDeNegocio) as e:
        ReservaService(repo, HabitacionRepoFalso(ocupada=True), UsuarioRepoFalso()).crear(_datos())
    assert e.value.codigo == "HABITACION_OCUPADA"
    assert repo.guardadas == []


def test_crear_reserva_habitacion_en_mantenimiento_se_rechaza():
    with pytest.raises(ErrorDeNegocio) as e:
        ReservaService(ReservaRepoFalso(), HabitacionRepoFalso(estado="mantenimiento"),
                       UsuarioRepoFalso()).crear(_datos())
    assert e.value.codigo == "HABITACION_NO_OPERATIVA"


def test_crear_reserva_habitacion_inexistente():
    with pytest.raises(ErrorDeNegocio) as e:
        ReservaService(ReservaRepoFalso(), HabitacionRepoFalso(), UsuarioRepoFalso()).crear(_datos(id_habitacion=999))
    assert e.value.codigo == "HABITACION_NO_ENCONTRADA"
