"""RNF-04 · Mantenibilidad / Capacidad para ser probado.

Los servicios de los tres RF se prueban con repositorios SIMULADOS (mocks), sin MySQL.
Funciona porque cada servicio recibe sus repositorios por el constructor
(inyección de dependencias): aquí se le pasa un mock en lugar del real.

- `create_autospec` copia los métodos y parámetros del repositorio REAL: si el
  servicio llamara un método que no existe o con argumentos distintos, la prueba falla.
- El mock devuelve hechos conocidos ("la habitación está ocupada") y permite
  verificar llamadas: en un rechazo NO debe invocarse `guardar`; en una consulta
  solo debe pedirse la lectura.
- La fixture `sin_base_de_datos` hace fallar cualquier intento de abrir una
  conexión real: si alguna prueba la abriera, fallaría.
"""
from datetime import date, timedelta
from unittest.mock import create_autospec

import mysql.connector
import pytest

from src.aplicacion.habitacion_service import HabitacionService
from src.aplicacion.reserva_service import ReservaService
from src.aplicacion.usuario_service import UsuarioService
from src.dominio.reglas_reserva import ErrorDeNegocio
from src.infraestructura.hasher import BcryptHasher
from src.persistencia.habitacion_repository import HabitacionRepository
from src.persistencia.reserva_repository import ReservaRepository
from src.persistencia.usuario_repository import UsuarioRepository

INICIO = date.today() + timedelta(days=30)
FIN = INICIO + timedelta(days=2)
HABITACION_1 = {"id_habitacion": 1, "numero": "1", "tipo": "estandar", "precio": 120000,
                "estado": "disponible", "descripcion": "Habitación estándar"}


@pytest.fixture(autouse=True)
def sin_base_de_datos(monkeypatch):
    """Cualquier intento de conectarse a MySQL hace fallar la prueba."""
    def prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión real a MySQL")
    monkeypatch.setattr(mysql.connector, "connect", prohibido)


@pytest.fixture
def repos():
    usuario = create_autospec(UsuarioRepository, instance=True)
    habitacion = create_autospec(HabitacionRepository, instance=True)
    reserva = create_autospec(ReservaRepository, instance=True)
    # Hechos por defecto: huésped 1 existe, habitación 1 existe, operativa y libre.
    usuario.buscar_por_id.return_value = {"id_usuario": 1, "correo": "ana@correo.com"}
    habitacion.buscar_por_id.return_value = dict(HABITACION_1)
    habitacion.esta_ocupada.return_value = False
    reserva.guardar.return_value = 100
    reserva.buscar_por_id.return_value = {
        "id_reserva": 100, "id_usuario": 1, "id_habitacion": 1, "numero": "1", "tipo": "estandar",
        "precio": 120000, "fecha_inicio": INICIO, "fecha_fin": FIN, "estado": "confirmada"}
    return usuario, habitacion, reserva


@pytest.fixture
def reserva_service(repos):
    usuario, habitacion, reserva = repos
    return ReservaService(reserva, habitacion, usuario)


def datos_reserva(**cambios):
    return {"id_usuario": 1, "id_habitacion": 1,
            "fecha_inicio": INICIO.isoformat(), "fecha_fin": FIN.isoformat(), **cambios}


# =====================================================================
# RF-03 · ReservaService.crear
# =====================================================================

def test_rf03_crear_valido_guarda_una_vez_con_sus_noches(reserva_service, repos):
    _, habitacion, reserva = repos

    resultado = reserva_service.crear(datos_reserva())

    assert resultado["id_reserva"] == 100 and resultado["total"] == 240000.0
    habitacion.esta_ocupada.assert_called_once_with(1, INICIO, FIN)
    reserva.guardar.assert_called_once_with(
        {"id_usuario": 1, "id_habitacion": 1, "fecha_inicio": INICIO, "fecha_fin": FIN},
        [INICIO, INICIO + timedelta(days=1)],
    )
    reserva.buscar_por_id.assert_called_once_with(100)   # responde con lo que quedó guardado


def test_rf03_crear_con_conflicto_no_invoca_guardar(reserva_service, repos):
    _, habitacion, reserva = repos
    habitacion.esta_ocupada.return_value = True           # hecho conocido: ya está ocupada

    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.crear(datos_reserva())

    assert e.value.codigo == "HABITACION_OCUPADA"
    reserva.guardar.assert_not_called()


def test_rf03_crear_en_mantenimiento_no_consulta_ocupacion_ni_guarda(reserva_service, repos):
    _, habitacion, reserva = repos
    habitacion.buscar_por_id.return_value = {**HABITACION_1, "estado": "mantenimiento"}

    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.crear(datos_reserva())

    assert e.value.codigo == "HABITACION_NO_OPERATIVA"
    habitacion.esta_ocupada.assert_not_called()
    reserva.guardar.assert_not_called()


def test_rf03_crear_con_huesped_inexistente_se_detiene_antes(reserva_service, repos):
    usuario, habitacion, reserva = repos
    usuario.buscar_por_id.return_value = None

    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.crear(datos_reserva(id_usuario=999))

    assert e.value.codigo == "USUARIO_NO_ENCONTRADO"
    habitacion.buscar_por_id.assert_not_called()
    reserva.guardar.assert_not_called()


def test_rf03_crear_con_entrada_invalida_no_toca_ningun_repositorio(reserva_service, repos):
    for datos in (datos_reserva(id_habitacion="abc"), datos_reserva(fecha_fin=INICIO.isoformat())):
        with pytest.raises(ErrorDeNegocio):
            reserva_service.crear(datos)
    for repo in repos:
        assert repo.mock_calls == []


def test_rf03_conflicto_detectado_por_la_base_se_propaga(reserva_service, repos):
    """Carrera: el servicio vio la habitación libre, pero otra solicitud guardó primero.
    El repositorio traduce el UNIQUE a HABITACION_OCUPADA y el servicio no lo oculta."""
    _, _, reserva = repos
    reserva.guardar.side_effect = ErrorDeNegocio("HABITACION_OCUPADA", "ocupada")

    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.crear(datos_reserva())

    assert e.value.codigo == "HABITACION_OCUPADA"
    reserva.buscar_por_id.assert_not_called()


# =====================================================================
# RF-03 · ReservaService.consultar
# =====================================================================

def test_rf03_consultar_existente_solo_lee(reserva_service, repos):
    usuario, habitacion, reserva = repos

    resultado = reserva_service.consultar(100)

    assert resultado["id_reserva"] == 100 and resultado["estado"] == "confirmada"
    reserva.buscar_por_id.assert_called_once_with(100)
    reserva.guardar.assert_not_called()
    assert usuario.mock_calls == [] and habitacion.mock_calls == []


def test_rf03_consultar_ausente(reserva_service, repos):
    _, _, reserva = repos
    reserva.buscar_por_id.return_value = None

    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.consultar(999999)

    assert e.value.codigo == "RESERVA_NO_ENCONTRADA"
    reserva.guardar.assert_not_called()


def test_rf03_consultar_id_invalido_no_llega_al_repositorio(reserva_service, repos):
    _, _, reserva = repos
    with pytest.raises(ErrorDeNegocio) as e:
        reserva_service.consultar("abc")
    assert e.value.codigo == "ID_INVALIDO"
    reserva.buscar_por_id.assert_not_called()


# =====================================================================
# RF-02 · HabitacionService.buscar_disponibles
# =====================================================================

def test_rf02_buscar_valido_solo_lee(repos):
    _, habitacion, _ = repos
    habitacion.listar_disponibles.return_value = [dict(HABITACION_1)]

    resultado = HabitacionService(habitacion).buscar_disponibles(INICIO.isoformat(), FIN.isoformat(), "estandar")

    assert resultado == [{**HABITACION_1, "precio": 120000.0}]
    habitacion.listar_disponibles.assert_called_once_with(INICIO, FIN, "estandar")


def test_rf02_buscar_con_fechas_invalidas_no_consulta(repos):
    _, habitacion, _ = repos
    with pytest.raises(ErrorDeNegocio) as e:
        HabitacionService(habitacion).buscar_disponibles(FIN.isoformat(), INICIO.isoformat())
    assert e.value.codigo == "RANGO_INVALIDO"
    habitacion.listar_disponibles.assert_not_called()


# =====================================================================
# RF-01 · UsuarioService.registrar
# =====================================================================

NUEVO = {"nombre": "Luis", "apellido": "Pérez", "correo": "luis@correo.com", "password": "Hotel2026!"}


def test_rf01_registrar_valido_guarda_el_hash_no_la_contrasena(repos):
    usuario, _, _ = repos
    usuario.buscar_por_correo.return_value = None
    usuario.guardar.return_value = 6
    hasher = create_autospec(BcryptHasher, instance=True)
    hasher.generar.return_value = "HASH-SIMULADO"

    resultado = UsuarioService(usuario, hasher).registrar(NUEVO)

    assert resultado["id_usuario"] == 6 and "password" not in resultado
    hasher.generar.assert_called_once_with("Hotel2026!")
    usuario.guardar.assert_called_once_with("Luis", "Pérez", None, "luis@correo.com", "HASH-SIMULADO")


def test_rf01_registrar_correo_repetido_no_cifra_ni_guarda(repos):
    usuario, _, _ = repos
    usuario.buscar_por_correo.return_value = {"id_usuario": 1, "correo": "luis@correo.com"}
    hasher = create_autospec(BcryptHasher, instance=True)

    with pytest.raises(ErrorDeNegocio) as e:
        UsuarioService(usuario, hasher).registrar(NUEVO)

    assert e.value.codigo == "CORREO_REGISTRADO"
    hasher.generar.assert_not_called()
    usuario.guardar.assert_not_called()
