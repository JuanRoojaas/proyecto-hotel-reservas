# Sistema de Reservas – Hotel Cancun Resort & Spa
### Corte vertical "Reservar una habitación" · Arquitectura de Sistemas I · Semana 13

**Stack:** Python 3.12 + MySQL 8.0 · arquitectura por capas.

> **Resumen.** Construiremos tres RF: **RF-03 Crear la reserva** (prioridad 1), **RF-02 Búsqueda de habitaciones** (2) y **RF-01 Registro de usuario** (3). RF-03 va primero porque es la operación principal y la de mayor exigencia arquitectónica; RF-02 reutiliza su consulta de ocupación, y RF-01 no bloquea a los otros porque los huéspedes vienen de los datos de prueba. Esperamos búsquedas rápidas (≤ 1 s), reservas sin registros a medias, contraseñas protegidas y SQL aislado en la capa de persistencia. Lo verifican las pruebas de `tests/test_persistencia.py` contra MySQL real y las capturas de `evidencias/`.
>
> **Alcance:** la guía pide dos RF; el profesor autorizó tres porque el corte los necesita para cerrar el flujo. La prioridad indica el orden; ninguno sale del alcance. **Fuera:** inicio de sesión con JWT, 2FA, cancelaciones, pagos y roles de recepcionista y administrador.

---

## 1. Ficha de los RF

| Elemento | RF-03 Crear la reserva | RF-02 Búsqueda de habitaciones | RF-01 Registro de usuario |
|---|---|---|---|
| **Enunciado** | El huésped reserva una habitación disponible para unas fechas | El huésped consulta habitaciones libres entre dos fechas, con filtro opcional por tipo | El visitante se registra con nombre, apellido, correo y contraseña |
| **Actor y resultado esperado** | Huésped registrado → ID de reserva, estado `confirmada` y total. Rechazo si está ocupada o en mantenimiento | Huésped → lista de habitaciones libres y operativas (o lista vacía). Rechazo si las fechas no son válidas | Visitante → ID de usuario con rol `huesped`. Rechazo si el correo ya existe |
| **Prioridad** | **1** | **2** | **3** |
| **Valor / relevancia arquitectónica / dependencia** | Valor alto · Alta: transacción, regla de disponibilidad, restricción de integridad · Necesita huésped y habitación: se cubren con el seed | Valor alto · Media-alta: consulta por rango de fechas compartida con RF-03 · Necesita habitaciones y reservas | Valor medio · Media: correo único y contraseña con hash; solo inserta y consulta un usuario · Sin dependencias |
| **RNF asociados** | RNF-02, RNF-04, RNF-05 | RNF-01, RNF-04, RNF-05 | RNF-03, RNF-04, RNF-05 |
| **ISO/IEC 25010** | Seguridad / Integridad | Eficiencia de desempeño / Comportamiento temporal | Seguridad / Confidencialidad |
| **Condición, medida y umbral** | Ver RNF-02 en §2 | Ver RNF-01 en §2 | Ver RNF-03 en §2 |
| **Datos y operaciones de persistencia** | `reservas`, `reservas_noches` · `ReservaRepository.guardar`, `buscar_por_id`; `HabitacionRepository.esta_ocupada` | `habitaciones`, `reservas_noches` · `HabitacionRepository.listar_disponibles` | `usuarios` · `UsuarioRepository.guardar`, `buscar_por_correo`, `buscar_por_id` |
| **Resultado semana 1** | ✅ Guardada y recuperada desde una conexión nueva; la doble reserva se revierte sin registros parciales | ✅ Excluye ocupadas y en mantenimiento; filtro por tipo; máx. 38,5 ms en 20 consultas | ✅ Correo único verificado; contraseñas guardadas con hash bcrypt |
| **Pendiente** | Servicio y API (sem. 2); interfaz (sem. 3) | RNF-01 sobre la API (sem. 2); interfaz (sem. 3) | Prueba del servicio para RNF-03 (sem. 2); interfaz (sem. 3) |

## 2. Matriz RF–RNF

| RNF | RF | ISO/IEC 25010:2023 | Condición → medida y umbral | Evidencia | Semana |
|---|---|---|---|---|---|
| **RNF-01** Tiempo de búsqueda | RF-02 | Eficiencia de desempeño / Comportamiento temporal | 24 habitaciones y 60 reservas, local, un cliente, 20 búsquedas seguidas → cada una **≤ 300 ms** en el repositorio y **≤ 1 s** en la API | Los 20 tiempos impresos por la prueba | 1 (línea base) · 2 (API) |
| **RNF-02** Reserva atómica | RF-03 | Seguridad / Integridad | Fallo después del primer `INSERT` → **0 registros parciales** (los conteos no cambian) | `test_rnf02_...` | 1 |
| **RNF-03** Contraseñas protegidas | RF-01 | Seguridad / Confidencialidad | Consulta directa a `usuarios` → **0 contraseñas en texto plano**, bcrypt costo ≥ 10; la respuesta no incluye el hash | Captura de `SELECT correo, password` | 1 (datos) · 2 (servicio) |
| **RNF-04** Probar sin base real | Los 3 | Mantenibilidad / Capacidad para ser probado | Servicios con repositorio simulado → 1 prueba válida + 1 de rechazo por servicio, sin MySQL | `tests/test_servicios.py` | 1 (contrato) · 2 |
| **RNF-05** SQL aislado | Los 3 | Mantenibilidad / Modularidad | Búsqueda de `SELECT/INSERT/UPDATE/DELETE` fuera de `src/persistencia/` → **0 coincidencias** | Salida de `grep` | 1, 2 y 3 |

> "No reservar una habitación ocupada en esas fechas" es una **regla de negocio** de RF-03, no un RNF: la decide el servicio y la refuerza la base de datos.

## 3. Persistencia

### 3.1 Datos mínimos

| Tabla | Claves y restricciones | Sirve a |
|---|---|---|
| `usuarios` | PK `id_usuario`; `UNIQUE(correo)`; `rol` por defecto `huesped` | RF-01; RF-03 (verificar huésped) |
| `habitaciones` | PK `id_habitacion`; `UNIQUE(numero)`; `estado` ∈ {`disponible`, `mantenimiento`} | RF-02 y RF-03 |
| `reservas` | PK `id_reserva`; FK a `usuarios` y `habitaciones`; `CHECK(fecha_fin > fecha_inicio)` | RF-03 |
| `reservas_noches` **(nueva)** | PK `(id_reserva, fecha)`; **`UNIQUE(id_habitacion, fecha)`** | RF-02 (ocupación); RF-03 (impide la doble reserva) |

**Adaptación frente al ejemplo de citas de la guía:** allí basta una restricción única por médico, fecha y hora porque la franja es fija. Una estancia dura varias noches, así que cada reserva se guarda también como una fila por noche; `UNIQUE(id_habitacion, fecha)` impide que dos reservas ocupen la misma noche, aunque lleguen al mismo tiempo.

**Cambios frente al modelo previo:** los `ALTER` se unieron en un solo `CREATE` por tabla; `numero` pasa a único; `estado` queda como estado operativo (la ocupación depende de las fechas); `id_usuario`, `id_habitacion` y `apellido` pasan a obligatorios; se agrega `reservas_noches`; el total se calcula como precio × noches. La base se llama `hotel_corte_vertical` porque las pruebas la recrean y así no se toca la base `hotel` de otro proyecto.

### 3.2 Repositorio (contrato para la semana 2)

| Operación | Entrada → Resultado | RF |
|---|---|---|
| `UsuarioRepository.guardar` | nombre, apellido, fecha_nacimiento, correo, hash → `id_usuario` · correo repetido → `CORREO_REGISTRADO` | RF-01 |
| `UsuarioRepository.buscar_por_correo` / `buscar_por_id` | correo / id → `dict` o `None` | RF-01, RF-03 |
| `HabitacionRepository.buscar_por_id` | id → `dict` o `None` | RF-03 |
| `HabitacionRepository.listar_disponibles` | inicio, fin, tipo opcional → `list[dict]` | RF-02 |
| `HabitacionRepository.esta_ocupada` | id, inicio, fin → `bool` | RF-03 |
| `ReservaRepository.guardar` | reserva, noches → `id_reserva` · noche ocupada → rollback y `HABITACION_OCUPADA` | RF-03 |
| `ReservaRepository.buscar_por_id` | id → `dict` o `None` | RF-03 |

**Transacción y conexiones:** el método que escribe hace `commit` si todo sale bien y `rollback` ante cualquier error. Cada método abre su conexión con `with obtener_conexion()`, que la cierra siempre. Las rutas y los servicios no contienen SQL.

**Código:** `db/` (scripts), `src/persistencia/` (conexión y repositorios), `tests/test_persistencia.py` (pruebas reales).

## 4. Cómo repetir la verificación

**Versiones:** Python 3.12.10 · MySQL Server 8.0.45 · MySQL Workbench 8.0.46 · librerías en `requirements.txt`.

```bash
# 1. Entorno e instalación
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 2. Conexión: copiar el ejemplo y poner usuario y contraseña locales (sin credenciales reales en el repo)
copy .env.example .env             # Linux/Mac: cp .env.example .env

# 3. Base y datos (o abrir los dos scripts en MySQL Workbench y ejecutarlos en orden)
mysql -u root -p < db/01_schema.sql
mysql -u root -p < db/02_seed.sql

# 4. Pruebas de persistencia (recrean la base antes de correr)
python -m pytest tests/test_persistencia.py -v -s
```

**Estado inicial (`02_seed.sql`):** 5 usuarios (contraseña de prueba `Hotel2026!`, guardada con hash), 24 habitaciones (1-12 estándar, 13-18 suite, 19-24 familiar) y 60 reservas. **Caso de referencia:** la habitación 1 está ocupada las noches 2026-12-10 y 2026-12-11; la 2 está libre esas fechas; la 24 está en mantenimiento.

**Resultado esperado:** `9 passed`. Con `python -m pytest -v`: `26 passed`.

| Prueba | Demuestra |
|---|---|
| `test_guardar_reserva_y_recuperarla_desde_conexion_nueva` | Escritura y persistencia real |
| `test_guardar_usuario_y_recuperarlo` | Escritura y lectura de usuario, sin exponer el hash |
| `test_id_inexistente_retorna_none` | Identificador inexistente → `None` |
| `test_restriccion_correo_unico` | Restricción de integridad → `CORREO_REGISTRADO` |
| `test_listar_disponibles_excluye_ocupadas_y_mantenimiento` · `..._filtra_por_tipo` | Consulta de RF-02 |
| `test_esta_ocupada_usa_rango_semiabierto` | El día de salida queda libre |
| `test_rnf02_doble_reserva_se_revierte_sin_registros_parciales` | RNF-02 |
| `test_rnf01_linea_base_busqueda_20_consultas` | RNF-01: máx. 38,5 ms, promedio 35,1 ms |

**Evidencias:**
[Base creada](evidencias/1.bd_creada_workbench.png) ·
[Pruebas de persistencia](evidencias/2.pruebas_persistencia.png) ·
[RNF-01 tiempos](evidencias/3.RNF01_tiempos_busqueda.png) ·
[RNF-03 contraseñas con hash](evidencias/4.RNF03_Contrase%C3%B1a_Hasheada.png) ·
[Todas las pruebas](evidencias/5.pruebas_generales.png) ·
[Salida completa de pytest](evidencias/pruebas_semana1.txt)

## 5. Criterios de revisión

| Criterio | Cumple | Evidencia |
|---|:---:|---|
| RF identificados, priorizados y justificados | ✅ | §1 |
| Cada RF se vincula con sus RNF e ISO/IEC 25010 | ✅ | §1 y §2 |
| Los RNF incluyen condición, medida, umbral y verificación | ✅ | §2 |
| Los datos y operaciones cubren los RF | ✅ | §3, `src/persistencia/` |
| La base y los datos de prueba pueden recrearse | ✅ | `db/01_schema.sql`, `db/02_seed.sql` |
| Se demuestra lectura, escritura y persistencia real | ✅ | §4, `tests/test_persistencia.py`, `evidencias/` |
| El README indica requisitos y pasos exactos de prueba | ✅ | §4 |
| Se distingue lo probado de lo pendiente para semanas 2 y 3 | ✅ | §1 (filas "Resultado" y "Pendiente"), §2 (columna "Semana") |
