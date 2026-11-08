"""Semana 1 (guía semana 13, Actividad 3): pruebas REALES contra MySQL.

Estado inicial conocido (02_seed.sql):
  - Habitación 1 ocupada las noches 2026-12-10 y 2026-12-11 (reserva 1).
  - Habitación 2 libre en esas fechas.
  - Habitación 24 en 'mantenimiento'.
  - Usuario 1: ana@correo.com
"""
import time
from datetime import date

import mysql.connector
import pytest

from src.dominio.reglas_reserva import ErrorDeNegocio
from src.persistencia.db import CONFIG
from src.persistencia.habitacion_repository import HabitacionRepository
from src.persistencia.reserva_repository import ReservaRepository
from src.persistencia.usuario_repository import UsuarioRepository

pytestmark = pytest.mark.usefixtures("bd_reiniciada")

usuarios = UsuarioRepository()
habitaciones = HabitacionRepository()
reservas = ReservaRepository()

INICIO_REF, FIN_REF = date(2026, 12, 10), date(2026, 12, 12)


def test_guardar_reserva_y_recuperarla_desde_conexion_nueva():
    nueva = {"id_usuario": 2, "id_habitacion": 2, "fecha_inicio": INICIO_REF, "fecha_fin": FIN_REF}
    id_reserva = reservas.guardar(nueva, [date(2026, 12, 10), date(2026, 12, 11)])
    assert id_reserva > 0

    # Conexión completamente nueva, independiente del repositorio
    cnx = mysql.connector.connect(**CONFIG)
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT id_habitacion, estado FROM reservas WHERE id_reserva = %s", (id_reserva,))
    fila = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) AS n FROM reservas_noches WHERE id_reserva = %s", (id_reserva,))
    noches = cursor.fetchone()["n"]
    cnx.close()

    assert fila == {"id_habitacion": 2, "estado": "confirmada"}
    assert noches == 2


def test_guardar_usuario_y_recuperarlo():
    nuevo_id = usuarios.guardar("Prueba", "Uno", None, "prueba1@correo.com", "$2b$10$hashdeprueba")
    recuperado = usuarios.buscar_por_id(nuevo_id)
    assert recuperado["correo"] == "prueba1@correo.com"
    assert recuperado["rol"] == "huesped"            # valor por defecto de la base
    assert "password" not in recuperado


def test_id_inexistente_retorna_none():
    assert reservas.buscar_por_id(99999) is None
    assert habitaciones.buscar_por_id(99999) is None
    assert usuarios.buscar_por_id(99999) is None
    assert usuarios.buscar_por_correo("nadie@correo.com") is None


def test_restriccion_correo_unico():
    with pytest.raises(ErrorDeNegocio) as error:
        usuarios.guardar("Otra", "Ana", None, "ana@correo.com", "$2b$10$hashdeprueba")
    assert error.value.codigo == "CORREO_REGISTRADO"


def test_listar_disponibles_excluye_ocupadas_y_mantenimiento():
    numeros = [h["numero"] for h in habitaciones.listar_disponibles(INICIO_REF, FIN_REF)]
    assert "1" not in numeros     # ocupada en el seed
    assert "2" not in numeros     # reservada en la primera prueba
    assert "24" not in numeros    # en mantenimiento
    assert "3" in numeros
    assert len(numeros) == 21


def test_listar_disponibles_filtra_por_tipo():
    suites = habitaciones.listar_disponibles(INICIO_REF, FIN_REF, "suite")
    assert {h["tipo"] for h in suites} == {"suite"}
    assert len(suites) == 6


def test_esta_ocupada_usa_rango_semiabierto():
    assert habitaciones.esta_ocupada(1, date(2026, 12, 11), date(2026, 12, 13)) is True
    # La noche del día de salida (12) no está ocupada: otro huésped puede entrar ese día
    assert habitaciones.esta_ocupada(1, date(2026, 12, 12), date(2026, 12, 14)) is False


def test_rnf02_doble_reserva_se_revierte_sin_registros_parciales():
    """La reserva se inserta, la noche 2026-12-11 choca con UNIQUE -> rollback total."""
    antes = reservas.contar()
    choque = {"id_usuario": 3, "id_habitacion": 1,
              "fecha_inicio": date(2026, 12, 11), "fecha_fin": date(2026, 12, 13)}
    with pytest.raises(ErrorDeNegocio) as error:
        reservas.guardar(choque, [date(2026, 12, 11), date(2026, 12, 12)])
    assert error.value.codigo == "HABITACION_OCUPADA"
    assert reservas.contar() == antes


def test_rnf01_linea_base_busqueda_20_consultas():
    tiempos = []
    for i in range(20):
        inicio, fin = date(2027, 1, 1 + i), date(2027, 1, 3 + i)
        t0 = time.perf_counter()
        habitaciones.listar_disponibles(inicio, fin)
        tiempos.append((time.perf_counter() - t0) * 1000)
    print("\nRNF-01 tiempos (ms):", [round(t, 1) for t in tiempos])
    print(f"RNF-01 máximo: {max(tiempos):.1f} ms | promedio: {sum(tiempos) / len(tiempos):.1f} ms")
    assert max(tiempos) <= 300
