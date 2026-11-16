"""Semana 14 (guía, Actividad 3): pruebas funcionales de los tres RF A TRAVÉS DE LA API,
contra MySQL real. Cada prueba parte de la base recién recreada (02_seed.sql).

Estado inicial conocido:
  - Usuario 1: ana@correo.com (huésped).
  - Habitación 1 OCUPADA las noches 2026-12-10 y 2026-12-11 (reserva 1).
  - Habitación 2 LIBRE en esas fechas.
  - Habitación 24 en 'mantenimiento'.
  - 5 usuarios, 24 habitaciones, 60 reservas.

Cada prueba indica: escenario, resultado esperado y qué se verifica en la base
desde una conexión nueva (sin pasar por la API).
"""
from tests.conftest import consultar_bd, contar

INICIO, FIN = "2026-12-10", "2026-12-12"


def reserva(**cambios):
    return {"id_usuario": 1, "id_habitacion": 2, "fecha_inicio": INICIO, "fecha_fin": FIN, **cambios}


# =====================================================================
# RF-03 Crear la reserva (prioridad 1)
# =====================================================================

def test_rf03_valido_crea_y_se_recupera_desde_otra_conexion(cliente):
    """Reservar la habitación 2 (libre) -> 201 con ID real; la base tiene la reserva y sus 2 noches."""
    r = cliente.post("/api/reservas", json=reserva())

    assert r.status_code == 201
    creada = r.get_json()
    assert creada["id_reserva"] == 61                      # 60 en el seed + esta
    assert creada["estado"] == "confirmada"
    assert creada["noches"] == 2 and creada["total"] == 240000.0

    fila = consultar_bd("SELECT id_usuario, id_habitacion, fecha_inicio, fecha_fin, estado "
                        "FROM reservas WHERE id_reserva = %s", (creada["id_reserva"],))[0]
    assert (fila["id_usuario"], fila["id_habitacion"], fila["estado"]) == (1, 2, "confirmada")
    assert (fila["fecha_inicio"].isoformat(), fila["fecha_fin"].isoformat()) == (INICIO, FIN)
    assert contar("reservas_noches", "id_reserva = %s", (creada["id_reserva"],)) == 2


def test_rf03_rechazo_habitacion_ocupada_no_cambia_registros(cliente):
    """Reservar la habitación 1 (ocupada) -> 409; mismas reservas y noches antes y después."""
    reservas_antes = contar("reservas")
    noches_antes = contar("reservas_noches", "id_habitacion = 1")

    r = cliente.post("/api/reservas", json=reserva(id_habitacion=1))

    assert r.status_code == 409
    assert r.get_json()["codigo"] == "HABITACION_OCUPADA"
    assert contar("reservas") == reservas_antes
    assert contar("reservas_noches", "id_habitacion = 1") == noches_antes


def test_rf03_rechazo_solapamiento_parcial(cliente):
    """Reservar la habitación 1 del 11 al 13 (choca solo con la noche del 11) -> 409."""
    r = cliente.post("/api/reservas", json=reserva(id_habitacion=1, fecha_inicio="2026-12-11",
                                                   fecha_fin="2026-12-13"))
    assert r.status_code == 409


def test_rf03_limite_entrar_el_dia_de_salida_de_otra_reserva(cliente):
    """La habitación 1 se libera el 12: reservar del 12 al 14 -> 201."""
    r = cliente.post("/api/reservas", json=reserva(id_habitacion=1, fecha_inicio="2026-12-12",
                                                   fecha_fin="2026-12-14"))
    assert r.status_code == 201


def test_rf03_rechazo_habitacion_en_mantenimiento(cliente):
    """Reservar la habitación 24 (mantenimiento) -> 409; no se guarda nada."""
    antes = contar("reservas")
    r = cliente.post("/api/reservas", json=reserva(id_habitacion=24))
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "HABITACION_NO_OPERATIVA"
    assert contar("reservas") == antes


def test_rf03_entrada_campo_faltante(cliente):
    """Omitir fecha_fin -> 400; sin registro huérfano."""
    antes = contar("reservas")
    datos = reserva()
    del datos["fecha_fin"]
    r = cliente.post("/api/reservas", json=datos)
    assert r.status_code == 400
    assert r.get_json()["codigo"] == "DATOS_FALTANTES"
    assert contar("reservas") == antes


def test_rf03_entrada_id_no_entero(cliente):
    """id_habitacion = "abc" -> 400 (no 404 ni 500)."""
    r = cliente.post("/api/reservas", json=reserva(id_habitacion="abc"))
    assert r.status_code == 400
    assert r.get_json()["codigo"] == "ID_INVALIDO"


def test_rf03_entrada_fechas_invalidas(cliente):
    """Fecha de fin anterior a la de inicio -> 400; fecha en el pasado -> 400."""
    r1 = cliente.post("/api/reservas", json=reserva(fecha_inicio=FIN, fecha_fin=INICIO))
    r2 = cliente.post("/api/reservas", json=reserva(fecha_inicio="2020-01-01", fecha_fin="2020-01-03"))
    assert (r1.status_code, r1.get_json()["codigo"]) == (400, "RANGO_INVALIDO")
    assert (r2.status_code, r2.get_json()["codigo"]) == (400, "FECHA_PASADA")


def test_rf03_huesped_inexistente(cliente):
    """id_usuario 999 -> 404; sin registro huérfano."""
    antes = contar("reservas")
    r = cliente.post("/api/reservas", json=reserva(id_usuario=999))
    assert r.status_code == 404
    assert r.get_json()["codigo"] == "USUARIO_NO_ENCONTRADO"
    assert contar("reservas") == antes


def test_rf03_consultar_la_reserva_creada_no_la_modifica(cliente):
    """GET con el ID real -> 200 con los mismos datos; la consulta no cambia el registro."""
    creada = cliente.post("/api/reservas", json=reserva()).get_json()
    fila_antes = consultar_bd("SELECT * FROM reservas WHERE id_reserva = %s", (creada["id_reserva"],))

    r = cliente.get(f"/api/reservas/{creada['id_reserva']}")

    assert r.status_code == 200
    assert r.get_json() == creada
    assert consultar_bd("SELECT * FROM reservas WHERE id_reserva = %s", (creada["id_reserva"],)) == fila_antes


def test_rf03_consultar_id_inexistente_y_api_sigue_disponible(cliente):
    """GET /api/reservas/999999 (comprobado que no existe) -> 404; la API sigue respondiendo."""
    assert contar("reservas", "id_reserva = 999999") == 0
    r = cliente.get("/api/reservas/999999")
    assert r.status_code == 404
    assert r.get_json()["codigo"] == "RESERVA_NO_ENCONTRADA"
    assert cliente.get("/api/salud").status_code == 200


def test_rf03_consultar_id_no_entero(cliente):
    """GET /api/reservas/abc y /api/reservas/0 -> 400 según contrato, sin error interno."""
    for id_malo in ("abc", "0", "-5"):
        r = cliente.get(f"/api/reservas/{id_malo}")
        assert r.status_code == 400, id_malo
        assert r.get_json()["codigo"] == "ID_INVALIDO"


# =====================================================================
# RF-02 Búsqueda de habitaciones disponibles (prioridad 2)
# =====================================================================

def disponibles(cliente, **params):
    params = {"fecha_inicio": INICIO, "fecha_fin": FIN, **params}
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return cliente.get(f"/api/habitaciones/disponibles?{query}")


def test_rf02_valido_excluye_ocupada_y_mantenimiento(cliente):
    """10-12 dic -> 200; no aparecen la 1 (ocupada) ni la 24 (mantenimiento); hay 22."""
    r = disponibles(cliente)
    assert r.status_code == 200
    numeros = [h["numero"] for h in r.get_json()]
    assert "1" not in numeros and "24" not in numeros
    assert "2" in numeros
    assert len(numeros) == 22


def test_rf02_refleja_una_reserva_recien_creada(cliente):
    """Después de reservar la 2 por API, la búsqueda ya no la muestra (RF-03 y RF-02 juntos)."""
    cliente.post("/api/reservas", json=reserva())
    numeros = [h["numero"] for h in disponibles(cliente).get_json()]
    assert "2" not in numeros
    assert len(numeros) == 21


def test_rf02_filtro_por_tipo_y_lista_vacia(cliente):
    """tipo=suite -> solo las 6 suites; un tipo que no existe -> 200 con lista vacía."""
    suites = disponibles(cliente, tipo="suite").get_json()
    assert len(suites) == 6 and {h["tipo"] for h in suites} == {"suite"}

    r = disponibles(cliente, tipo="penthouse")
    assert r.status_code == 200 and r.get_json() == []


def test_rf02_busqueda_no_modifica_datos(cliente):
    """Buscar no escribe nada: los conteos son iguales antes y después."""
    antes = (contar("reservas"), contar("reservas_noches"))
    disponibles(cliente)
    assert (contar("reservas"), contar("reservas_noches")) == antes


def test_rf02_entrada_fechas_invalidas(cliente):
    """Fechas al revés, formato incorrecto o faltantes -> 400."""
    casos = [
        ({"fecha_inicio": FIN, "fecha_fin": INICIO}, "RANGO_INVALIDO"),
        ({"fecha_inicio": "10/12/2026"}, "FECHA_INVALIDA"),
        ({"fecha_inicio": "2020-01-01", "fecha_fin": "2020-01-03"}, "FECHA_PASADA"),
    ]
    for params, codigo in casos:
        r = disponibles(cliente, **params)
        assert (r.status_code, r.get_json()["codigo"]) == (400, codigo), params

    r = cliente.get("/api/habitaciones/disponibles")
    assert r.status_code == 400


# =====================================================================
# RF-01 Registro de usuario (prioridad 3)
# =====================================================================

NUEVO = {"nombre": "Juan", "apellido": "Rojas", "fecha_nacimiento": "2003-05-10",
         "correo": "juan@correo.com", "password": "Hotel2026!"}


def test_rf01_valido_registra_con_hash_y_sin_exponer_password(cliente):
    """Registrar -> 201 con ID real y rol huesped; en la base la contraseña es un hash bcrypt."""
    r = cliente.post("/api/usuarios", json=NUEVO)

    assert r.status_code == 201
    creado = r.get_json()
    assert creado["id_usuario"] == 6 and creado["rol"] == "huesped"
    assert "password" not in creado

    fila = consultar_bd("SELECT correo, password FROM usuarios WHERE id_usuario = %s", (6,))[0]
    assert fila["correo"] == NUEVO["correo"]
    assert fila["password"].startswith("$2b$10$")
    assert NUEVO["password"] not in fila["password"]


def test_rf01_rechazo_correo_repetido(cliente):
    """Correo ya registrado (ana@correo.com) -> 409; no se crea otro usuario."""
    antes = contar("usuarios")
    r = cliente.post("/api/usuarios", json={**NUEVO, "correo": "ana@correo.com"})
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "CORREO_REGISTRADO"
    assert contar("usuarios") == antes


def test_rf01_entrada_invalida(cliente):
    """Contraseña corta, correo mal escrito o campo faltante -> 400; no se crea usuario."""
    antes = contar("usuarios")
    casos = [
        ({**NUEVO, "password": "123"}, "PASSWORD_DEBIL"),
        ({**NUEVO, "correo": "sin-arroba"}, "CORREO_INVALIDO"),
        ({k: v for k, v in NUEVO.items() if k != "apellido"}, "DATOS_FALTANTES"),
    ]
    for datos, codigo in casos:
        r = cliente.post("/api/usuarios", json=datos)
        assert (r.status_code, r.get_json()["codigo"]) == (400, codigo), codigo
    assert contar("usuarios") == antes


# =====================================================================
# Contrato general
# =====================================================================

def test_errores_de_ruta_y_metodo_en_json(cliente):
    """Ruta inexistente -> 404 JSON; método no permitido -> 405 JSON."""
    r1 = cliente.get("/api/no-existe")
    r2 = cliente.delete("/api/reservas")
    assert (r1.status_code, r1.get_json()["codigo"]) == (404, "RUTA_NO_ENCONTRADA")
    assert (r2.status_code, r2.get_json()["codigo"]) == (405, "METODO_NO_PERMITIDO")
