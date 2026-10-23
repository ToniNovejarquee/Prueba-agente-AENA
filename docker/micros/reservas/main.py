"""Micro de reservas de la aerolínea (FastAPI + PostgreSQL) — "Micro clientes" del diagrama (reservas y vuelos de cada cliente).
    POST  /reservas                {vuelo, pasajeros, titular{nombre, apellidos, email}}  -> 201 {tipo: "reserva", localizador, estado: "PENDIENTE_PAGO", ...}
    GET   /reservas/{localizador}                                                        -> {tipo: "reserva", ...}
    PATCH /reservas/{localizador}  {parking?, pago?, estado?}                            -> {tipo: "reserva", ...} (recalcula los importes)
Errores de negocio: HTTP 400/404 con {tipo: "error", codigo, mensaje}.
"""
import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from sqlalchemy import JSON, Column, MetaData, String, Table, select

from common.db import crear_engine
from common.util import EMAIL, cuerpo_json, error, ok, vacio

ESTADOS = ["PENDIENTE_PAGO", "CONFIRMADA", "CANCELADA"]

meta = MetaData()
reservas = Table("reservas", meta,
                 Column("localizador", String(10), primary_key=True),
                 Column("estado", String(20), nullable=False),
                 Column("datos", JSON, nullable=False))
engine = crear_engine()
meta.create_all(engine)
app = FastAPI(title="Micro de reservas (aerolínea)")


@app.get("/health")
def health():
    return {"estado": "ok"}


def _ahora():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _leer(con, localizador: str):
    fila = con.execute(select(reservas.c.datos).where(reservas.c.localizador == localizador)).first()
    return fila[0] if fila else None


@app.post("/reservas")
async def crear(request: Request):
    p = await cuerpo_json(request)
    v = p.get("vuelo") if isinstance(p.get("vuelo"), dict) else {}
    t = p.get("titular") if isinstance(p.get("titular"), dict) else {}
    try:
        pasajeros = int(p.get("pasajeros") or v.get("pasajeros") or 1)
        precio = float(v.get("precioPorPasajero") or 0)
    except (TypeError, ValueError):
        return error("VUELO_NO_VALIDO", "Falta el vuelo (con vueloId y precioPorPasajero) a reservar")
    if vacio(v.get("vueloId")) or precio <= 0:
        return error("VUELO_NO_VALIDO", "Falta el vuelo (con vueloId y precioPorPasajero) a reservar")
    if vacio(t.get("nombre")) or vacio(t.get("apellidos")) or vacio(t.get("email")):
        return error("TITULAR_INCOMPLETO", "Faltan datos del titular: nombre, apellidos y email son obligatorios")
    if not EMAIL.fullmatch(str(t["email"])):
        return error("EMAIL_NO_VALIDO", "El email del titular no es válido")
    importe_vuelo = round(precio * pasajeros * 100) / 100
    reserva = {
        "tipo": "reserva", "localizador": uuid.uuid4().hex[:6].upper(), "estado": "PENDIENTE_PAGO", "creada": _ahora(),
        "titular": {"nombre": t["nombre"], "apellidos": t["apellidos"], "email": t["email"]},
        "pasajeros": pasajeros,
        "vuelo": {k: v.get(k) for k in ("vueloId", "numeroVuelo", "compania", "origen", "destino", "salida", "llegada", "duracion", "tarifa")}
                 | {"precioPorPasajero": precio},
        "parking": None, "pago": None,
        "importes": {"vuelo": importe_vuelo, "parking": 0, "total": importe_vuelo}, "moneda": "EUR",
    }
    with engine.begin() as con:
        con.execute(reservas.insert().values(localizador=reserva["localizador"], estado=reserva["estado"], datos=reserva))
    return ok(reserva, 201)


@app.get("/reservas/{localizador}")
def consultar(localizador: str):
    loc = localizador.strip().upper()
    with engine.connect() as con:
        r = _leer(con, loc)
    if r is None:
        return error("RESERVA_NO_ENCONTRADA", f"No existe ninguna reserva con el localizador '{loc}'", 404)
    return ok(r)


@app.patch("/reservas/{localizador}")
async def actualizar(localizador: str, request: Request):
    loc = localizador.strip().upper()
    c = await cuerpo_json(request)
    with engine.begin() as con:
        r = _leer(con, loc)
        if r is None:
            return error("RESERVA_NO_ENCONTRADA", f"No existe ninguna reserva con el localizador '{loc}'", 404)
        parking = c["parking"] if c.get("parking") is not None else r.get("parking")
        pago = ({**(r.get("pago") or {}), **c["pago"]} if isinstance(c.get("pago"), dict) else r.get("pago"))
        estado = str(c.get("estado") or r["estado"])
        if estado not in ESTADOS:
            return error("ESTADO_NO_VALIDO", f"Estado '{estado}' no válido. Valores: {', '.join(ESTADOS)}")
        if r["estado"] == "CONFIRMADA" and c.get("parking") is not None:
            return error("RESERVA_YA_PAGADA", f"La reserva {r['localizador']} ya está pagada: no se puede añadir parking")
        importe_parking = float((parking or {}).get("importe") or 0)
        nueva = {**r, "estado": estado, "parking": parking, "pago": pago,
                 "importes": {"vuelo": r["importes"]["vuelo"], "parking": importe_parking,
                              "total": round((r["importes"]["vuelo"] + importe_parking) * 100) / 100},
                 "actualizada": _ahora()}
        con.execute(reservas.update().where(reservas.c.localizador == loc).values(estado=estado, datos=nueva))
    return ok(nueva)
