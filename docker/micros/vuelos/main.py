"""Micro de vuelos (FastAPI + PostgreSQL) — "Micro de vuelos" del diagrama.

Los vuelos de una ruta y una fecha se generan de forma determinista la primera vez que se consultan
y se guardan en la tabla "vuelos"; a partir de ahí se leen de la base de datos.
    POST /vuelos/busqueda   {origen, destino, fecha (AAAA-MM-DD), pasajeros}  -> {tipo: "vuelos", vuelos: [...]}
    GET  /vuelos/{vueloId}?pasajeros=N                                         -> {tipo: "vuelo", vuelo: {...}}
Errores de negocio: HTTP 400/404 con {tipo: "error", codigo, mensaje}.
"""
import math
import os
import re
import zlib
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Request
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, select
from sqlalchemy.exc import IntegrityError

from common.aeropuertos import AEROPUERTOS, CODIGOS_CONOCIDOS, codigo_aeropuerto, distancia_km, info_aeropuerto
from common.db import crear_engine
from common.util import cuerpo_json, error, ok

COMPANIA = os.getenv("COMPANIA", "DA")
NOMBRE_COMPANIA = os.getenv("NOMBRE_COMPANIA", "Aerolinea Demo")
PRECIO_BASE = float(os.getenv("PRECIO_BASE", "39"))
PRECIO_KM = float(os.getenv("PRECIO_KM", "0.085"))
PLAZAS_MAX = int(os.getenv("PLAZAS_MAX", "9"))
FACTORES_PRECIO = [1.15, 0.92, 1.0, 1.08]

meta = MetaData()
vuelos = Table(
    "vuelos", meta,
    Column("vuelo_id", String(40), primary_key=True),
    Column("origen", String(3), nullable=False, index=True),
    Column("destino", String(3), nullable=False, index=True),
    Column("fecha", String(10), nullable=False, index=True),
    Column("numero", String(10), nullable=False),
    Column("salida", String(16), nullable=False),
    Column("llegada", String(16), nullable=False),
    Column("duracion_min", Integer, nullable=False),
    Column("distancia_km", Integer, nullable=False),
    Column("plazas_libres", Integer, nullable=False),
    Column("precio_pasajero", Float, nullable=False),
)

engine = crear_engine()
meta.create_all(engine)
app = FastAPI(title="Micro de vuelos")


@app.get("/health")
def health():
    return {"estado": "ok"}


def _generar(origen: str, destino: str, fecha: str):
    a, b = AEROPUERTOS[origen], AEROPUERTOS[destino]
    dist = distancia_km(a, b)
    duracion = round((dist / 780 * 60 + 35) / 5) * 5
    dif_horaria = (b["tz"] - a["tz"]) * 60
    s = zlib.crc32((origen + destino + fecha).encode())
    horarios = ["11:15", "16:40"] if dist > 3000 else ["07:10", "10:35", "14:50", "19:25"]
    filas = []
    for i, hora in enumerate(horarios):
        salida = datetime.fromisoformat(f"{fecha}T{hora}:00") + timedelta(minutes=((s + i) % 4) * 5)
        llegada = salida + timedelta(minutes=duracion + dif_horaria)
        numero = 1000 + ((s + i * 137) % 8000)
        precio_bruto = (PRECIO_BASE + dist * PRECIO_KM) * FACTORES_PRECIO[i] + ((s + i) % 7)
        filas.append(dict(
            vuelo_id=f"{COMPANIA}{numero}_{origen}{destino}_{fecha.replace('-', '')}",
            origen=origen, destino=destino, fecha=fecha, numero=f"{COMPANIA} {numero}",
            salida=salida.strftime("%Y-%m-%dT%H:%M"), llegada=llegada.strftime("%Y-%m-%dT%H:%M"),
            duracion_min=duracion, distancia_km=dist,
            plazas_libres=1 + ((s + i * 3) % PLAZAS_MAX),
            precio_pasajero=math.floor(precio_bruto) + 0.99,
        ))
    return filas


def _vuelos_de_ruta(origen: str, destino: str, fecha: str):
    with engine.begin() as con:
        filas = con.execute(select(vuelos).where(vuelos.c.origen == origen, vuelos.c.destino == destino, vuelos.c.fecha == fecha)
                            .order_by(vuelos.c.salida)).mappings().all()
        if not filas:
            try:
                con.execute(vuelos.insert(), _generar(origen, destino, fecha))
            except IntegrityError:  # otra petición los generó a la vez
                pass
            filas = con.execute(select(vuelos).where(vuelos.c.origen == origen, vuelos.c.destino == destino, vuelos.c.fecha == fecha)
                                .order_by(vuelos.c.salida)).mappings().all()
    return filas


def _json_vuelo(f, pasajeros: int):
    h, m = divmod(f["duracion_min"], 60)
    return {
        "vueloId": f["vuelo_id"], "numeroVuelo": f["numero"], "compania": NOMBRE_COMPANIA,
        "origen": info_aeropuerto(f["origen"]), "destino": info_aeropuerto(f["destino"]),
        "salida": f["salida"], "llegada": f["llegada"],
        "duracionMin": f["duracion_min"], "duracion": f"{h} h {m} min", "distanciaKm": f["distancia_km"],
        "escalas": 0, "tarifa": "Turista (equipaje de mano incluido)",
        "plazasLibres": f["plazas_libres"], "disponible": f["plazas_libres"] >= pasajeros,
        "pasajeros": pasajeros, "precioPorPasajero": f["precio_pasajero"],
        "precioTotal": round(f["precio_pasajero"] * pasajeros * 100) / 100, "moneda": "EUR",
    }


def _entero(v, defecto=1):
    try:
        return int(v) if v is not None and str(v).strip() != "" else defecto
    except (TypeError, ValueError):
        return None


@app.post("/vuelos/busqueda")
async def buscar(request: Request):
    p = await cuerpo_json(request)
    origen, destino = codigo_aeropuerto(p.get("origen")), codigo_aeropuerto(p.get("destino"))
    fecha = str(p.get("fecha") or "").strip()
    pasajeros = _entero(p.get("pasajeros"))
    hoy = date.today()
    if origen is None:
        return error("AEROPUERTO_DESCONOCIDO", f"No conozco el aeropuerto de origen '{p.get('origen') or ''}'. Aeropuertos disponibles: {CODIGOS_CONOCIDOS}")
    if destino is None:
        return error("AEROPUERTO_DESCONOCIDO", f"No conozco el aeropuerto de destino '{p.get('destino') or ''}'. Aeropuertos disponibles: {CODIGOS_CONOCIDOS}")
    if origen == destino:
        return error("RUTA_NO_VALIDA", f"El origen y el destino son el mismo aeropuerto ({origen})")
    try:
        d = date.fromisoformat(fecha) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha) else None
    except ValueError:
        d = None
    if d is None:
        return error("FECHA_NO_VALIDA", f"La fecha '{fecha}' no es válida: usa el formato AAAA-MM-DD. Hoy es {hoy.isoformat()}")
    if d < hoy:
        return error("FECHA_PASADA", f"La fecha {fecha} ya ha pasado. Hoy es {hoy.isoformat()}")
    if pasajeros is None or not 1 <= pasajeros <= 9:
        return error("PASAJEROS_NO_VALIDO", "El número de pasajeros debe estar entre 1 y 9")
    lista = [_json_vuelo(f, pasajeros) for f in _vuelos_de_ruta(origen, destino, fecha)]
    return ok({"tipo": "vuelos", "origen": info_aeropuerto(origen), "destino": info_aeropuerto(destino),
               "fecha": fecha, "pasajeros": pasajeros, "totalResultados": len(lista), "vuelos": lista})


@app.get("/vuelos/{vuelo_id}")
def detalle(vuelo_id: str, pasajeros: str = "1"):
    n = _entero(pasajeros)
    partes = vuelo_id.split("_")
    no_existe = error("VUELO_NO_ENCONTRADO", f"No existe el vuelo '{vuelo_id}'. Usa un vueloId devuelto por la búsqueda de vuelos.", 404)
    if len(partes) != 3 or len(partes[1]) != 6 or not re.fullmatch(r"\d{8}", partes[2]):
        return no_existe
    origen, destino = partes[1][:3], partes[1][3:]
    f8 = partes[2]
    fecha = f"{f8[:4]}-{f8[4:6]}-{f8[6:]}"
    try:
        date.fromisoformat(fecha)
    except ValueError:
        return no_existe
    if origen not in AEROPUERTOS or destino not in AEROPUERTOS or origen == destino:
        return no_existe
    f = next((x for x in _vuelos_de_ruta(origen, destino, fecha) if x["vuelo_id"] == vuelo_id), None)
    if f is None:
        return no_existe
    if n is None or not 1 <= n <= 9:
        return error("PASAJEROS_NO_VALIDO", "El número de pasajeros debe estar entre 1 y 9")
    return ok({"tipo": "vuelo", "vuelo": _json_vuelo(f, n)})
