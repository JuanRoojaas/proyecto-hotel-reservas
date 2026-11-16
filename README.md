# Sistema de Reservas – Hotel Cancun Resort & Spa
### Corte vertical "Reservar una habitación" · Arquitectura de Sistemas I · Semana 14

**Stack:** Python 3.12 + Flask + MySQL 8.0 · arquitectura por capas · API en `http://127.0.0.1:3000/api`

> **Resumen.** Los tres RF priorizados en la semana 13 funcionan por API: **RF-03 Crear la reserva** (prioridad 1), **RF-02 Búsqueda de habitaciones** (2) y **RF-01 Registro de usuario** (3). Cada endpoint delega en un servicio que aplica las reglas; el SQL vive solo en los repositorios. Verificamos los cinco RNF: la búsqueda responde en máx. **81,2 ms** por HTTP (umbral 1 s), la reserva no deja registros a medias, las contraseñas se guardan con hash, los servicios se prueban sin base de datos y no hay SQL fuera de persistencia. Queda para la semana 3 conectar la interfaz y repetir el RNF-01 desde la pantalla.
>
> **Alcance sin cambios:** mismos identificadores, prioridad y alcance de la semana 13. 
> **Fuera:** inicio de sesión con JWT, 2FA, cancelaciones, pagos y roles de recepcionista y administrador.

---

## 1. RF y servicios

Flujo: **API** (`src/presentacion/hotel_routes.py`) → **servicio** (`src/aplicacion/`) → **repositorio** (`src/persistencia/`) → **MySQL**. Las reglas de negocio están en `src/dominio/reglas_reserva.py`.

| | RF-03 Crear la reserva | RF-02 Búsqueda | RF-01 Registro |
|---|---|---|---|
| **Prioridad** | 1 | 2 | 3 |
| **Servicio** | `ReservaService.crear` · `consultar` | `HabitacionService.buscar_disponibles` | `UsuarioService.registrar` |
| **Entrada** | `id_usuario`, `id_habitacion`, `fecha_inicio`, `fecha_fin` | `fecha_inicio`, `fecha_fin`, `tipo` (opcional) | `nombre`, `apellido`, `correo`, `password`, `fecha_nacimiento` (opcional) |
| **Reglas y condiciones** | IDs enteros positivos · fecha de inicio no pasada y fin posterior · huésped y habitación existen · habitación operativa · **sin noches ocupadas en el rango** | Fechas válidas, inicio no pasado y fin posterior · excluye ocupadas y en mantenimiento | Campos obligatorios · correo válido y único · contraseña ≥ 8 caracteres, guardada con hash bcrypt |
| **Repositorio** | `UsuarioRepository.buscar_por_id` · `HabitacionRepository.buscar_por_id`, `esta_ocupada` · `ReservaRepository.guardar`, `buscar_por_id` | `HabitacionRepository.listar_disponibles` | `UsuarioRepository.buscar_por_correo`, `guardar` |
| **Resultado válido** | 201 con la reserva guardada (ID real, noches, total, estado `confirmada`) | 200 con la lista de habitaciones libres (puede ser vacía) | 201 con el usuario creado y rol `huesped`, sin contraseña |
| **Rechazo esperado** | 409 si está ocupada o en mantenimiento · 404 si no existe el huésped o la habitación · 400 por entrada inválida | 400 por fechas inválidas | 409 si el correo ya existe · 400 por entrada inválida |

**Transacción y conexiones.** `ReservaRepository.guardar` inserta la reserva y sus noches en **una sola transacción**: `commit` si todo sale bien, `rollback` ante cualquier error. Cada método abre su conexión con `with obtener_conexion()`, que la cierra siempre. La API responde 201 **después** del `commit`, con la reserva leída de la base.

**Solicitudes simultáneas.** El servicio revisa la disponibilidad antes de guardar. Si dos solicitudes pasan esa revisión al mismo tiempo, la restricción `UNIQUE(id_habitacion, fecha)` de `reservas_noches` rechaza la segunda. El repositorio traduce **solo ese error de unicidad** a `HABITACION_OCUPADA` (409); cualquier otro error de base de datos sigue siendo un 500.

## 2. Contratos de la API

**Convenciones:** JSON en `snake_case`, IDs enteros, fechas `AAAA-MM-DD`. El ID y el estado inicial los define el backend. **Todos los errores** responden con el mismo formato y con un `codigo` que la interfaz puede usar:

```json
{ "detail": "La habitación ya está reservada en esas fechas", "codigo": "HABITACION_OCUPADA" }
```

Un fallo interno responde `500` con `{"detail": "Error interno del servidor", "codigo": "ERROR_INTERNO"}`, sin detalles técnicos; el error completo queda en la consola del servidor.

| RF | Método y ruta | Entrada | Éxito | Errores |
|---|---|---|---|---|
| RF-03 | `POST /api/reservas` | JSON: `id_usuario`, `id_habitacion`, `fecha_inicio`, `fecha_fin` | **201** reserva creada | **400** `DATOS_FALTANTES`, `ID_INVALIDO`, `FECHA_INVALIDA`, `FECHA_PASADA`, `RANGO_INVALIDO` · **404** `USUARIO_NO_ENCONTRADO`, `HABITACION_NO_ENCONTRADA` · **409** `HABITACION_OCUPADA`, `HABITACION_NO_OPERATIVA` |
| RF-03 | `GET /api/reservas/{id_reserva}` | ID entero positivo en la ruta | **200** reserva | **400** `ID_INVALIDO` · **404** `RESERVA_NO_ENCONTRADA` |
| RF-02 | `GET /api/habitaciones/disponibles?fecha_inicio=&fecha_fin=&tipo=` | Query: fechas obligatorias, `tipo` opcional | **200** lista (puede ser `[]`) | **400** `FECHA_INVALIDA`, `FECHA_PASADA`, `RANGO_INVALIDO` |
| RF-01 | `POST /api/usuarios` | JSON: `nombre`, `apellido`, `correo`, `password`, `fecha_nacimiento` (opcional) | **201** usuario creado | **400** `DATOS_FALTANTES`, `CORREO_INVALIDO`, `PASSWORD_DEBIL`, `FECHA_INVALIDA` · **409** `CORREO_REGISTRADO` |
| — | `GET /api/salud` | — | **200** `{"estado": "ok"}` | — |

Además: ruta inexistente → **404** `RUTA_NO_ENCONTRADA`; método no permitido → **405** `METODO_NO_PERMITIDO`.

### Ejemplos (respuestas reales del backend)

**RF-03 · crear** — `POST /api/reservas`
```json
{ "id_usuario": 6, "id_habitacion": 2, "fecha_inicio": "2026-12-10", "fecha_fin": "2026-12-12" }
```
`201 Created`
```json
{
  "id_reserva": 61, "id_usuario": 6, "id_habitacion": 2, "numero_habitacion": "2", "tipo": "estandar",
  "fecha_inicio": "2026-12-10", "fecha_fin": "2026-12-12", "noches": 2,
  "precio_noche": 120000.0, "total": 240000.0, "estado": "confirmada"
}
```
Con la habitación 1, ocupada esas noches → `409 Conflict`
```json
{ "detail": "La habitación ya está reservada en esas fechas", "codigo": "HABITACION_OCUPADA" }
```

**RF-03 · consultar** — `GET /api/reservas/61` → `200 OK` con el mismo cuerpo de la creación. `GET /api/reservas/999999` → `404 Not Found`:
```json
{ "detail": "La reserva no existe", "codigo": "RESERVA_NO_ENCONTRADA" }
```

**RF-02 · buscar** — `GET /api/habitaciones/disponibles?fecha_inicio=2026-12-10&fecha_fin=2026-12-12` → `200 OK`
```json
[
  { "id_habitacion": 2, "numero": "2", "tipo": "estandar", "precio": 120000.0, "estado": "disponible", "descripcion": "Habitación estándar" },
  { "id_habitacion": 3, "numero": "3", "tipo": "estandar", "precio": 120000.0, "estado": "disponible", "descripcion": "Habitación estándar" }
]
```
(22 habitaciones en total; se muestran 2.)

**RF-01 · registrar** — `POST /api/usuarios`
```json
{ "nombre": "Juan", "apellido": "Rojas", "fecha_nacimiento": "2003-05-10", "correo": "juan@correo.com", "password": "Hotel2026!" }
```
`201 Created`
```json
{ "id_usuario": 6, "nombre": "Juan", "apellido": "Rojas", "correo": "juan@correo.com", "rol": "huesped" }
```

Todas las peticiones, con sus errores, están listas para enviar en [`api.http`](api.http) (extensión REST Client de VS Code).

## 3. Pruebas funcionales

**Estado inicial** (`db/02_seed.sql`): 5 usuarios (el 1 es `ana@correo.com`), 24 habitaciones, 60 reservas. La habitación **1** está ocupada las noches del 10 y 11 de diciembre de 2026, la **2** está libre y la **24** está en mantenimiento. Cada prueba de `tests/test_api.py` **recrea la base antes de correr**, así que todas parten de este estado y se pueden repetir.

**Cómo se verifica:** cada prueba envía la petición HTTP y luego revisa la base **desde una conexión nueva**, sin pasar por la API.

| RF | Escenario | Esperado | Obtenido |
|---|---|---|---|
| RF-03 | Reservar la habitación 2 (libre) | 201 con ID real; la reserva y sus 2 noches están en la base | ✅ ID 61 · [captura](evidencias/7.reserva_creada.png) |
| RF-03 | Reservar la habitación 1 (ocupada) | 409; mismas reservas y noches antes y después | ✅ · [captura](evidencias/9.habitacion_ocupada.png) |
| RF-03 | Habitación 1 del 11 al 13 (choque parcial) | 409 | ✅ |
| RF-03 | Habitación 1 del 12 al 14 (entra el día que la otra sale) | 201 | ✅ |
| RF-03 | Habitación 24 (mantenimiento) | 409; nada guardado | ✅ |
| RF-03 | Campo faltante · `id_habitacion: "abc"` · fechas al revés o pasadas | 400; nada guardado | ✅ |
| RF-03 | Huésped 999 | 404; nada guardado | ✅ |
| RF-03 | Consultar la reserva creada | 200 con los mismos datos; el registro no cambia | ✅ |
| RF-03 | Consultar 999999 (comprobado que no existe) | 404; la API sigue respondiendo | ✅ · [captura](evidencias/10.reserva_noexiste.png) |
| RF-03 | Consultar `abc`, `0`, `-5` | 400 | ✅ |
| RF-02 | Buscar del 10 al 12 de dic. | 200; 22 habitaciones, sin la 1 ni la 24 | ✅ |
| RF-02 | Buscar después de reservar la 2 | 200; 21 habitaciones, sin la 2 | ✅ · [captura](evidencias/8.lista_habitaciones_restantes.png) |
| RF-02 | `tipo=suite` · `tipo=penthouse` | 6 suites · lista vacía | ✅ |
| RF-02 | Buscar no escribe nada | Conteos iguales antes y después | ✅ |
| RF-02 | Fechas al revés, mal escritas, pasadas o faltantes | 400 | ✅ |
| RF-01 | Registrar un usuario nuevo | 201, rol `huesped`; en la base la contraseña es un hash `$2b$10$...` | ✅ |
| RF-01 | Correo ya registrado | 409; no se crea otro usuario | ✅ |
| RF-01 | Contraseña corta · correo inválido · campo faltante | 400; no se crea usuario | ✅ |

**Total:** 21 pruebas de API (`tests/test_api.py`), 9 de persistencia, 13 de servicios aislados y 21 de reglas de dominio: **64 passed**.

## 4. Matriz RF–RNF con resultados

| RF / RNF | Calidad ISO/IEC 25010:2023 | Prueba y meta | Resultado y evidencia | Estado |
|---|---|---|---|---|
| RF-02 / **RNF-01** | Eficiencia de desempeño / Comportamiento temporal | 20 búsquedas por HTTP, un cliente, entorno local, 24 habitaciones y 60 reservas; **cada una ≤ 1 s** | **20/20** con 200 · máx. 81,2 ms, prom. 56,8 ms · [reporte](evidencias/rnf01_reporte.md), [CSV](evidencias/rnf01_resultados.csv), [captura](evidencias/6.cumplimiento_rnf01.png) | ✅ Verificado (API) · pendiente repetirlo desde la interfaz (sem. 3) |
| RF-03 / **RNF-02** | Seguridad / Integridad | Choque detectado en la base después del primer `INSERT` → **0 registros parciales** | Rollback total; conteos iguales · `test_rnf02_...` (persistencia) y `test_rf03_rechazo_habitacion_ocupada_...` (API) | ✅ Verificado |
| RF-01 / **RNF-03** | Seguridad / Confidencialidad | **0 contraseñas en texto plano**, bcrypt costo 10; la respuesta no la incluye | Hash `$2b$10$` en la base; respuesta sin `password` · `test_rf01_valido_registra_con_hash_...` (API), `test_rf01_registrar_valido_guarda_el_hash_...` (servicio), [captura](evidencias/4.RNF03_Contrase%C3%B1a_Hasheada.png) | ✅ Verificado |
| RF-01, RF-02, RF-03 / **RNF-04** | Mantenibilidad / Capacidad para ser probado | Servicios con repositorio simulado: ≥ 1 válido + 1 rechazo por servicio, **sin MySQL**, 3 ejecuciones seguidas | **13 pruebas** en `tests/test_servicios.py`; en un rechazo se verifica que **`guardar` no se invoca** y en una consulta que **solo se lee**; cualquier conexión real hace fallar la prueba · [captura](evidencias/12.rnf04_sin_bd.png) | ✅ Verificado |
| RF-01, RF-02, RF-03 / **RNF-05** | Mantenibilidad / Modularidad | **0 sentencias SQL** fuera de `src/persistencia/` | 0 coincidencias (comando en §5) | ✅ Verificado |

**Límites de estas pruebas:** un solo cliente, datos de prueba y equipo local. No demuestran el comportamiento con más volumen ni con usuarios concurrentes.

## 5. Ejecución

**Versiones:** Python 3.12.10 · MySQL Server 8.0.45 · MySQL Workbench 8.0.46 · Windows 11 · librerías en `requirements.txt`.

**Variables** (`.env`, a partir de [`.env.example`](.env.example); no se sube al repositorio):

| Variable | Ejemplo | Para qué |
|---|---|---|
| `DB_HOST` · `DB_PORT` | `localhost` · `3306` | Servidor MySQL |
| `DB_USER` · `DB_PASSWORD` | `root` · `su_contraseña_aqui` | Credenciales locales |
| `DB_NAME` | `hotel_corte_vertical` | Base del corte |
| `PORT` | `3000` | Puerto de la API → `http://127.0.0.1:3000/api` |
| `CORS_ORIGINS` | `http://127.0.0.1:5500,http://localhost:5500` | Origen de la interfaz (sem. 3) |

```bash
# 1. Instalar
python -m venv .venv
.venv\Scripts\activate                 # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                  # Linux/Mac: cp .env.example .env  → poner usuario y contraseña

# 2. Reiniciar los datos de prueba (o ejecutar ambos scripts en MySQL Workbench, en orden)
mysql -u root -p < db/01_schema.sql
mysql -u root -p < db/02_seed.sql

# 3. Todas las pruebas (las de BD recrean la base solas)  → 64 passed
python -m pytest -v

# 4. RNF-04: servicios sin base de datos (puede detenerse MySQL)  → 13 passed
python -m pytest tests/test_servicios.py -v

# 5. Encender la API (terminal 1)
python app.py

# 6. RNF-01 por HTTP (terminal 2, con la API encendida)  → "RNF-01: CUMPLE — 20/20"
python scripts/medir_rnf01.py

# 7. RNF-05: buscar SQL fuera de persistencia (PowerShell)  → sin resultados
Get-ChildItem src, app.py -Recurse -Include *.py | Where-Object FullName -notmatch "persistencia" | Select-String -Pattern "\b(SELECT|INSERT|UPDATE|DELETE)\b"
```

**Demo:** reiniciar los datos (paso 2), encender la API y enviar en orden las peticiones de `api.http`. Si se repite sin reiniciar, la reserva de la habitación 2 responde 409 porque ya quedó ocupada.

## 6. Relevo a la interfaz (semana 3)

- **Contratos:** los de §2. La pantalla usa `fecha_inicio`/`fecha_fin` en `AAAA-MM-DD` y muestra el `detail` de los errores; puede decidir qué hacer según el `codigo`.
- **Flujo previsto:** registrarse (`POST /api/usuarios`) → buscar (`GET /api/habitaciones/disponibles`) → reservar con el `id_usuario` recibido (`POST /api/reservas`) → mostrar la confirmación (`GET /api/reservas/{id}`).
- **Datos disponibles:** los del seed (§3). El caso de referencia sirve para probar éxito (habitación 2), conflicto (1) y mantenimiento (24) desde la pantalla.
- **CORS:** la API acepta peticiones desde `http://127.0.0.1:5500` y `http://localhost:5500` (Live Server de VS Code). Otro origen se agrega en `CORS_ORIGINS`.
- **Reintentos:** si se pierde la respuesta de una reserva, la pantalla no debe reenviarla a ciegas: primero consulta la disponibilidad. Si la reserva sí se guardó, un reenvío daría 409 por la restricción de unicidad, no una reserva duplicada.
- **Pendiente:** repetir el RNF-01 desde la pantalla; las fechas del caso de referencia (10 y 11 de dic. de 2026) deben moverse en el seed y en las pruebas si pasan antes de la entrega.

## 7. Dónde encontrar cada criterio de revisión

| Criterio | Dónde está |
|---|---|
| Los RF mantienen la prioridad y el alcance de la semana 1 | Resumen y §1 |
| Los RF tienen servicios y endpoints identificables | §1 y §2 |
| Los contratos describen éxito, entrada inválida y errores pertinentes | §2 y `api.http` |
| Hay resultado válido y rechazo/ausencia probado para cada RF | §3 y `tests/test_api.py` |
| Se verifica persistencia real y ausencia de escrituras indebidas | §3 (verificación desde otra conexión y conteos) |
| El SQL queda en persistencia y las reglas en servicio o dominio | §4 (RNF-05) y carpeta `src/` |
| Cada RF se vincula con sus RNF y atributos ISO/IEC 25010 | §4 |
| Los RNF previstos tienen medidas observadas y evidencias | §4 y carpeta `evidencias/` |
| Se distinguen incumplimientos y pendientes de la semana 3 | §4 (columna Estado) y §6 |
| El README permite ejecutar y repetir las pruebas | §5 |
**Evidencias:**
Semana 13 — [base creada](evidencias/1.bd_creada_workbench.png) · [persistencia](evidencias/2.pruebas_persistencia.png) · [RNF-01 en repositorio](evidencias/3.RNF01_tiempos_busqueda.png) · [RNF-03](evidencias/4.RNF03_Contrase%C3%B1a_Hasheada.png) · [pruebas semana 13](evidencias/5.pruebas_generales.png) · [salida pytest](evidencias/pruebas_semana1.txt)
Semana 14 — [RNF-01 por HTTP](evidencias/6.cumplimiento_rnf01.png) · [reserva creada](evidencias/7.reserva_creada.png) · [habitaciones restantes](evidencias/8.lista_habitaciones_restantes.png) · [habitación ocupada](evidencias/9.habitacion_ocupada.png) · [reserva inexistente](evidencias/10.reserva_noexiste.png) · [64 pruebas](evidencias/11.pruebas_semana14.png) · [RNF-04 sin MySQL](evidencias/12.rnf04_sin_bd.png) · [reporte RNF-01](evidencias/rnf01_reporte.md)
