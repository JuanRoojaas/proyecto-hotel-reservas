"""RNF-01 · Eficiencia de desempeño / Comportamiento temporal (RF-02 Búsqueda).

Meta: con la base de prueba (24 habitaciones, 60 reservas), un solo cliente y
entorno local, 20 búsquedas consecutivas por HTTP; CADA una debe responder en
máximo 1 segundo (1000 ms).

Qué se mide: el tiempo COMPLETO de la respuesta HTTP visto desde el cliente
(enviar la petición + esperar + leer todo el cuerpo JSON), no solo la consulta SQL.

Uso (con el servidor encendido en otra terminal: python app.py):
    python scripts/medir_rnf01.py

Resultado: evidencias/rnf01_resultados.csv (una fila por consulta) y
           evidencias/rnf01_reporte.md (entorno, tabla y conclusión).
"""
import csv
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.persistencia.db import CONFIG, obtener_conexion  # noqa: E402

# 127.0.0.1 y no "localhost": en Windows, localhost puede intentar primero IPv6 y sumar ~2 s por petición
API = os.getenv("API_URL", f"http://127.0.0.1:{os.getenv('PORT', '3000')}")
UMBRAL_MS = 1000
CONSULTAS = 20
EVIDENCIAS = RAIZ / "evidencias"


def pedir(url):
    """Hace un GET y devuelve (código HTTP, cuerpo JSON, milisegundos)."""
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            codigo, cuerpo = r.status, r.read()
    except urllib.error.HTTPError as e:
        codigo, cuerpo = e.code, e.read()
    ms = (time.perf_counter() - inicio) * 1000
    return codigo, json.loads(cuerpo or b"null"), ms


def datos_de_la_base():
    with obtener_conexion() as cnx:
        cursor = cnx.cursor()
        cursor.execute("SELECT VERSION(), (SELECT COUNT(*) FROM habitaciones), "
                       "(SELECT COUNT(*) FROM reservas), (SELECT COUNT(*) FROM reservas_noches)")
        version, habitaciones, reservas, noches = cursor.fetchone()
        cursor.close()
    return {"mysql": version, "habitaciones": habitaciones, "reservas": reservas, "noches": noches}


def main():
    # 1. El servidor debe estar encendido
    try:
        codigo, _, _ = pedir(f"{API}/api/salud")
    except urllib.error.URLError:
        sys.exit(f"No se pudo conectar a {API}. Encienda el servidor con: python app.py")
    if codigo != 200:
        sys.exit(f"{API}/api/salud respondió {codigo}")

    base = datos_de_la_base()

    # 2. Las 20 búsquedas: rangos de 2 noches, uno distinto por consulta (ene-2027, donde hay reservas)
    filas = []
    for i in range(CONSULTAS):
        inicio = date(2027, 1, 4) + timedelta(days=i)
        fin = inicio + timedelta(days=2)
        url = f"{API}/api/habitaciones/disponibles?fecha_inicio={inicio}&fecha_fin={fin}"
        codigo, cuerpo, ms = pedir(url)
        filas.append({
            "n": i + 1, "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(),
            "codigo_http": codigo,
            "habitaciones": len(cuerpo) if isinstance(cuerpo, list) else "",
            "ms": round(ms, 1),
            "cumple": "sí" if codigo == 200 and ms <= UMBRAL_MS else "no",
        })

    # 3. Comparar CADA consulta con el umbral (el promedio no reemplaza este criterio)
    cumplen = sum(f["cumple"] == "sí" for f in filas)
    tiempos = [f["ms"] for f in filas]
    veredicto = "CUMPLE" if cumplen == CONSULTAS else "NO CUMPLE"

    EVIDENCIAS.mkdir(exist_ok=True)
    with open(EVIDENCIAS / "rnf01_resultados.csv", "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel muestra bien las tildes
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)

    tabla = "\n".join(
        f"| {f['n']} | {f['fecha_inicio']} → {f['fecha_fin']} | {f['codigo_http']} | "
        f"{f['habitaciones']} | {f['ms']} | {f['cumple']} |" for f in filas)
    reporte = f"""# RNF-01 · Tiempo de respuesta de la búsqueda (RF-02)

**Fecha de la medición:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Resultado: {veredicto}** — {cumplen} de {CONSULTAS} consultas respondieron en ≤ {UMBRAL_MS} ms con código 200.
Máximo {max(tiempos):.1f} ms · mínimo {min(tiempos):.1f} ms · promedio {sum(tiempos) / len(tiempos):.1f} ms (el promedio es informativo; el criterio es cada consulta).

## Entorno

| Elemento | Valor |
|---|---|
| Equipo | {platform.system()} {platform.release()} · {platform.machine()} · {platform.processor() or 'procesador no informado'} |
| Python | {platform.python_version()} |
| MySQL | {base['mysql']} en {CONFIG['host']}:{CONFIG['port']}, base `{CONFIG['database']}` |
| API | {API} (servidor de desarrollo de Flask, mismo equipo) |
| Datos | {base['habitaciones']} habitaciones · {base['reservas']} reservas · {base['noches']} noches ocupadas |
| Cliente | Un solo cliente (`urllib`), consultas una tras otra |
| Caché | Sin caché en la aplicación; MySQL con su configuración por defecto. La primera consulta se incluye en la medición |
| Qué se mide | Respuesta HTTP completa desde el cliente: envío, espera y lectura del cuerpo JSON |

## Consultas

| # | Rango | HTTP | Habitaciones | ms | ≤ {UMBRAL_MS} ms |
|---|---|---|---|---|---|
{tabla}

## Alcance de la prueba

Prueba acotada: un cliente, datos de prueba y equipo local. No demuestra el comportamiento con
más volumen de datos ni con usuarios concurrentes.
"""
    (EVIDENCIAS / "rnf01_reporte.md").write_text(reporte, encoding="utf-8")

    print(f"RNF-01: {veredicto} — {cumplen}/{CONSULTAS} consultas ≤ {UMBRAL_MS} ms "
          f"(máx. {max(tiempos):.1f} ms, promedio {sum(tiempos) / len(tiempos):.1f} ms)")
    print("Evidencia: evidencias/rnf01_reporte.md y evidencias/rnf01_resultados.csv")
    sys.exit(0 if veredicto == "CUMPLE" else 1)


if __name__ == "__main__":
    main()
