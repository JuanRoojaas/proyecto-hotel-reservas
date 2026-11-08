"""Reglas de negocio del hotel.

Este módulo NO importa Flask ni MySQL: son reglas puras que se prueban
de forma aislada (igual que reglasDeAgenda.js en el ejemplo de citas).
"""
import re
from datetime import date, timedelta


class ErrorDeNegocio(Exception):
    """Error simbólico del negocio. La presentación lo traduce a HTTP."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _faltantes(datos, campos):
    return [c for c in campos if datos.get(c) in (None, "")]


# ---------------------------------------------------------------- RF-01
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LONGITUD_MINIMA_PASSWORD = 8


def validar_datos_registro(datos):
    faltantes = _faltantes(datos, ("nombre", "apellido", "correo", "password"))
    if faltantes:
        raise ErrorDeNegocio("DATOS_FALTANTES", f"Faltan datos obligatorios: {', '.join(faltantes)}")
    if not PATRON_CORREO.match(datos["correo"]):
        raise ErrorDeNegocio("CORREO_INVALIDO", "El correo no tiene un formato válido")
    if len(datos["password"]) < LONGITUD_MINIMA_PASSWORD:
        raise ErrorDeNegocio(
            "PASSWORD_DEBIL",
            f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres",
        )
    if datos.get("fecha_nacimiento"):
        convertir_fecha(datos["fecha_nacimiento"], "fecha de nacimiento")


def validar_correo_disponible(correo_ya_registrado):
    # Averiguar si existe es tarea de persistencia; aquí solo se decide.
    if correo_ya_registrado:
        raise ErrorDeNegocio("CORREO_REGISTRADO", "Ya existe una cuenta con ese correo")


# ---------------------------------------------------------------- RF-02
def convertir_fecha(texto, campo):
    try:
        return date.fromisoformat(str(texto))
    except (TypeError, ValueError):
        raise ErrorDeNegocio("FECHA_INVALIDA", f"La {campo} debe tener formato AAAA-MM-DD")


def validar_rango_fechas(inicio, fin, hoy=None):
    hoy = hoy or date.today()
    if inicio < hoy:
        raise ErrorDeNegocio("FECHA_PASADA", "La fecha de inicio no puede estar en el pasado")
    if fin <= inicio:
        raise ErrorDeNegocio("RANGO_INVALIDO", "La fecha de fin debe ser posterior a la de inicio")


# ---------------------------------------------------------------- RF-03
def validar_datos_reserva(datos):
    faltantes = _faltantes(datos, ("id_usuario", "id_habitacion", "fecha_inicio", "fecha_fin"))
    if faltantes:
        raise ErrorDeNegocio("DATOS_FALTANTES", f"Faltan datos obligatorios: {', '.join(faltantes)}")


def validar_existe(registro, codigo, mensaje):
    if registro is None:
        raise ErrorDeNegocio(codigo, mensaje)


def validar_habitacion_operativa(habitacion):
    if habitacion["estado"] != "disponible":
        raise ErrorDeNegocio(
            "HABITACION_NO_OPERATIVA",
            f"La habitación {habitacion['numero']} está en {habitacion['estado']}",
        )


def validar_habitacion_libre(ocupada):
    if ocupada:
        raise ErrorDeNegocio("HABITACION_OCUPADA", "La habitación ya está reservada en esas fechas")


def noches_de_estancia(inicio, fin):
    """Noches ocupadas: desde la fecha de inicio hasta el día anterior a la de fin."""
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days)]


def calcular_total(precio, inicio, fin):
    return round(float(precio) * (fin - inicio).days, 2)
