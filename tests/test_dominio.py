"""Reglas puras: no necesitan base de datos ni servidor."""
from datetime import date

import pytest

from src.dominio import reglas_reserva as r

HOY = date(2026, 11, 7)


def test_rango_valido_no_lanza():
    r.validar_rango_fechas(date(2026, 12, 10), date(2026, 12, 12), hoy=HOY)


@pytest.mark.parametrize("inicio,fin,codigo", [
    (date(2026, 11, 1), date(2026, 11, 3), "FECHA_PASADA"),
    (date(2026, 12, 10), date(2026, 12, 10), "RANGO_INVALIDO"),
    (date(2026, 12, 12), date(2026, 12, 10), "RANGO_INVALIDO"),
])
def test_rangos_invalidos(inicio, fin, codigo):
    with pytest.raises(r.ErrorDeNegocio) as e:
        r.validar_rango_fechas(inicio, fin, hoy=HOY)
    assert e.value.codigo == codigo


def test_fecha_con_formato_incorrecto():
    with pytest.raises(r.ErrorDeNegocio) as e:
        r.convertir_fecha("10/12/2026", "fecha de inicio")
    assert e.value.codigo == "FECHA_INVALIDA"


def test_noches_y_total():
    noches = r.noches_de_estancia(date(2026, 12, 10), date(2026, 12, 13))
    assert noches == [date(2026, 12, 10), date(2026, 12, 11), date(2026, 12, 12)]
    assert r.calcular_total(120000, date(2026, 12, 10), date(2026, 12, 13)) == 360000.00


def test_habitacion_en_mantenimiento():
    with pytest.raises(r.ErrorDeNegocio) as e:
        r.validar_habitacion_operativa({"numero": "24", "estado": "mantenimiento"})
    assert e.value.codigo == "HABITACION_NO_OPERATIVA"


@pytest.mark.parametrize("datos,codigo", [
    ({"nombre": "A", "apellido": "B", "correo": "a@b.co"}, "DATOS_FALTANTES"),
    ({"nombre": "A", "apellido": "B", "correo": "sin-arroba", "password": "12345678"}, "CORREO_INVALIDO"),
    ({"nombre": "A", "apellido": "B", "correo": "a@b.co", "password": "123"}, "PASSWORD_DEBIL"),
    ({"nombre": "A", "apellido": "B", "correo": "a@b.co", "password": "12345678",
      "fecha_nacimiento": "14/03/1995"}, "FECHA_INVALIDA"),
])
def test_registro_invalido(datos, codigo):
    with pytest.raises(r.ErrorDeNegocio) as e:
        r.validar_datos_registro(datos)
    assert e.value.codigo == codigo
