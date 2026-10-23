"""Micro de parking (FastAPI + PostgreSQL) — "Micro de parking" del diagrama.
    POST /disponibilidad   {aeropuerto, fechaEntrada, fechaSalida}                                -> {tipo: "parking_disponibilidad", opciones: [...]}
    POST /reservas         {aeropuerto, opcionId, fechaEntrada, fechaSalida, matricula?, referencia?} -> 201 {tipo: "parking_reserva", ...}
    GET  /reservas/{codigoReserva}                                                                  -> {tipo: "parking_reserva", ...}
Errores de negocio: HTTP 400/404 con {tipo: "error", codigo, mensaje}.
"""
import math
import os
import re
import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from sqlalchemy import JSON, Column, MetaData, String, Table, select

from common.aeropuertos import AEROPUERTOS, CODIGOS_CONOCIDOS, codigo_aeropuerto, info_aeropuerto
from common.db import crear_engine
from common.util import cuerpo_json, error, ok

PRECIO_EXPRESS = float(os.getenv("PRECIO_DIA_EXPRESS", "29.90"))
PRECIO_GENERAL = float(os.getenv("PRECIO_DIA_GENERAL", "18.50"))
PRECIO_LARGA = float(os.getenv("PRECIO_DIA_LARGA_ESTANCIA", "9.95"))
MIN_DIAS_LARGA = int(os.getenv("MIN_DIAS_LARGA_ESTANCIA", "4"))

meta = MetaData()
reservas = Table("reservas_parking", meta,
                 Column("codigo_reserva", String(20), primary_key=True),
                 Column("datos", JSON, nullable=False))
engine = crear_engine()
meta.create_all(engine)
app = FastAPI(title="Micro de parking")


@app.get("/health")
def health():
    return {"estado": "ok"}


def _normalizar_fecha(f):
    t = str(f or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        t += "T00:00"
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*", t):
        t = t[:16]
    else:
        return None
    try:
        datetime.fromisoformat(t)
    except ValueError:
        return None
    return t


def _productos(codigo: str, dias: int):
    term = AEROPUERTOS[codigo]["terminal"]
    catalogo = [
        {"opcionId": "EXPRESS", "nombre": f"Parking Express {term}", "descripcion": f"Junto a la terminal {term}, a 2 min a pie", "precioDia": PRECIO_EXPRESS},
        {"opcionId": "GENERAL", "nombre": "Parking General P1", "descripcion": f"A 8 min a pie de la terminal {term}", "precioDia": PRECIO_GENERAL},
        {"opcionId": "LARGA_ESTANCIA", "nombre": "Parking Larga Estancia", "descripcion": f"Con autobús lanzadera gratuito cada 10 min. Mínimo {MIN_DIAS_LARGA} días", "precioDia": PRECIO_LARGA, "minDias": MIN_DIAS_LARGA},
    ]
    return [{**p, "dias": dias, "disponible": dias >= p.get("minDias", 1),
             "precioTotal": round(p["precioDia"] * dias * 100) / 100, "moneda": "EUR"} for p in catalogo]


def _disponibilidad(p: dict):
    """Devuelve (disponibilidad, None) o (None, respuesta_de_error)."""
    texto = str(p.get("aeropuerto") or "")
    codigo = codigo_aeropuerto(p.get("aeropuerto"))
    if codigo is None:
        return None, error("AEROPUERTO_DESCONOCIDO", f"No conozco el aeropuerto '{texto}'. Aeropuertos disponibles: {CODIGOS_CONOCIDOS}")
    a = AEROPUERTOS[codigo]
    if not a["aena"]:
        return None, error("AEROPUERTO_NO_AENA", f"{a['nombre']} ({codigo}) no pertenece a la red de AENA: el parking solo se puede reservar en aeropuertos españoles de AENA")
    entrada, salida = _normalizar_fecha(p.get("fechaEntrada")), _normalizar_fecha(p.get("fechaSalida"))
    if entrada is None or salida is None:
        return None, error("FECHA_NO_VALIDA", "Las fechas de entrada y salida deben tener formato AAAA-MM-DD o AAAA-MM-DDTHH:mm")
    horas = (datetime.fromisoformat(salida) - datetime.fromisoformat(entrada)).total_seconds() / 3600
    if horas <= 0:
        return None, error("FECHAS_INCOHERENTES", "La fecha de salida del parking debe ser posterior a la de entrada")
    dias = max(1, math.ceil(horas / 24))
    return {"tipo": "parking_disponibilidad", "aeropuerto": info_aeropuerto(codigo), "fechaEntrada": entrada,
            "fechaSalida": salida, "dias": dias, "opciones": _productos(codigo, dias)}, None


@app.post("/disponibilidad")
async def disponibilidad(request: Request):
    d, err = _disponibilidad(await cuerpo_json(request))
    return err or ok(d)


@app.post("/reservas")
async def reservar(request: Request):
    p = await cuerpo_json(request)
    d, err = _disponibilidad(p)
    if err:
        return err
    opcion_id = str(p.get("opcionId") or "").strip().upper()
    opcion = next((o for o in d["opciones"] if o["opcionId"] == opcion_id), None)
    validas = ", ".join(o["opcionId"] for o in d["opciones"] if o["disponible"])
    if opcion is None:
        return error("OPCION_NO_VALIDA", f"La opción de parking '{opcion_id}' no existe. Opciones disponibles: {validas}")
    if not opcion["disponible"]:
        return error("OPCION_NO_DISPONIBLE", f"La opción {opcion['nombre']} no está disponible para {opcion['dias']} días. Opciones disponibles: {validas}")
    reserva = {
        "tipo": "parking_reserva", "codigoReserva": "PK-" + uuid.uuid4().hex[:8].upper(), "estado": "RESERVADA",
        "aeropuerto": d["aeropuerto"],
        "producto": {"opcionId": opcion["opcionId"], "nombre": opcion["nombre"], "descripcion": opcion["descripcion"]},
        "fechaEntrada": d["fechaEntrada"], "fechaSalida": d["fechaSalida"], "dias": opcion["dias"],
        "precioDia": opcion["precioDia"], "importe": opcion["precioTotal"], "moneda": "EUR",
        "matricula": str(p["matricula"]).upper() if p.get("matricula") else None,
        "referencia": p.get("referencia"),
        "creada": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with engine.begin() as con:
        con.execute(reservas.insert().values(codigo_reserva=reserva["codigoReserva"], datos=reserva))
    return ok(reserva, 201)


@app.get("/reservas/{codigo}")
def consultar(codigo: str):
    codigo = codigo.upper()
    with engine.connect() as con:
        fila = con.execute(select(reservas.c.datos).where(reservas.c.codigo_reserva == codigo)).first()
    if fila is None:
        return error("RESERVA_NO_ENCONTRADA", f"No existe la reserva de parking '{codigo}'", 404)
    return ok(fila[0])
