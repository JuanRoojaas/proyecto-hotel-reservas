# RNF-01 · Tiempo de respuesta de la búsqueda (RF-02)

**Fecha de la medición:** 2026-11-16 17:25
**Resultado: CUMPLE** — 20 de 20 consultas respondieron en ≤ 1000 ms con código 200.
Máximo 81.2 ms · mínimo 41.9 ms · promedio 56.8 ms (el promedio es informativo; el criterio es cada consulta).

## Entorno

| Elemento | Valor |
|---|---|
| Equipo | Windows 11 · AMD64 · Intel64 Family 6 Model 186 Stepping 2, GenuineIntel |
| Python | 3.12.10 |
| MySQL | 8.0.45 en localhost:3306, base `hotel_corte_vertical` |
| API | http://127.0.0.1:3000 (servidor de desarrollo de Flask, mismo equipo) |
| Datos | 24 habitaciones · 60 reservas · 193 noches ocupadas |
| Cliente | Un solo cliente (`urllib`), consultas una tras otra |
| Caché | Sin caché en la aplicación; MySQL con su configuración por defecto. La primera consulta se incluye en la medición |
| Qué se mide | Respuesta HTTP completa desde el cliente: envío, espera y lectura del cuerpo JSON |

## Consultas

| # | Rango | HTTP | Habitaciones | ms | ≤ 1000 ms |
|---|---|---|---|---|---|
| 1 | 2027-01-04 → 2027-01-06 | 200 | 22 | 65.9 | sí |
| 2 | 2027-01-05 → 2027-01-07 | 200 | 20 | 58.1 | sí |
| 3 | 2027-01-06 → 2027-01-08 | 200 | 18 | 57.2 | sí |
| 4 | 2027-01-07 → 2027-01-09 | 200 | 18 | 47.3 | sí |
| 5 | 2027-01-08 → 2027-01-10 | 200 | 17 | 49.4 | sí |
| 6 | 2027-01-09 → 2027-01-11 | 200 | 13 | 61.0 | sí |
| 7 | 2027-01-10 → 2027-01-12 | 200 | 11 | 50.3 | sí |
| 8 | 2027-01-11 → 2027-01-13 | 200 | 11 | 81.2 | sí |
| 9 | 2027-01-12 → 2027-01-14 | 200 | 8 | 64.9 | sí |
| 10 | 2027-01-13 → 2027-01-15 | 200 | 13 | 47.1 | sí |
| 11 | 2027-01-14 → 2027-01-16 | 200 | 13 | 52.8 | sí |
| 12 | 2027-01-15 → 2027-01-17 | 200 | 12 | 47.4 | sí |
| 13 | 2027-01-16 → 2027-01-18 | 200 | 11 | 47.7 | sí |
| 14 | 2027-01-17 → 2027-01-19 | 200 | 8 | 60.8 | sí |
| 15 | 2027-01-18 → 2027-01-20 | 200 | 13 | 62.3 | sí |
| 16 | 2027-01-19 → 2027-01-21 | 200 | 15 | 62.7 | sí |
| 17 | 2027-01-20 → 2027-01-22 | 200 | 16 | 60.1 | sí |
| 18 | 2027-01-21 → 2027-01-23 | 200 | 15 | 41.9 | sí |
| 19 | 2027-01-22 → 2027-01-24 | 200 | 15 | 53.6 | sí |
| 20 | 2027-01-23 → 2027-01-25 | 200 | 15 | 63.6 | sí |

## Alcance de la prueba

Prueba acotada: un cliente, datos de prueba y equipo local. No demuestra el comportamiento con
más volumen de datos ni con usuarios concurrentes.
