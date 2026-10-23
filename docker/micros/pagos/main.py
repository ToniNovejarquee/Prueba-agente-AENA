"""Micro de pagos (FastAPI + PostgreSQL) con pasarela simulada tipo Sipay — "API pagos" + "Mock Sipay" del diagrama.
    POST /pagos            {referencia, importe, concepto}  -> 201 {tipo: "pago", idPago, estado: "PENDIENTE", urlPago, ...}
    GET  /pagos/{idPago}                                   -> {tipo: "pago", estado: PENDIENTE | PAGADO | CANCELADO, ...}
    GET  /pago/{idPago}   (HTML)  página de pago que abre el usuario en el navegador
    POST /pago/{idPago}   (formulario accion=pagar|cancelar)
"""
import html
import os
import uuid
from datetime import datetime
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import JSON, Column, MetaData, String, Table, select

from common.db import crear_engine
from common.util import cuerpo_json, error, eur, ok

MONEDA = os.getenv("PAGOS_MONEDA", "EUR")
PASARELA = os.getenv("PAGOS_PASARELA", "Sipay (simulada)")
PUBLIC_URL = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:8203").rstrip("/")

meta = MetaData()
pagos = Table("pagos", meta,
              Column("id_pago", String(20), primary_key=True),
              Column("datos", JSON, nullable=False))
engine = crear_engine()
meta.create_all(engine)
app = FastAPI(title="Micro de pagos")


@app.get("/health")
def health():
    return {"estado": "ok"}


def _ahora():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _leer(id_pago: str):
    with engine.connect() as con:
        fila = con.execute(select(pagos.c.datos).where(pagos.c.id_pago == id_pago)).first()
    return fila[0] if fila else None


def _guardar(p: dict):
    with engine.begin() as con:
        con.execute(pagos.update().where(pagos.c.id_pago == p["idPago"]).values(datos=p))


@app.post("/pagos")
async def crear(request: Request):
    p = await cuerpo_json(request)
    try:
        importe = float(p.get("importe") or 0)
    except (TypeError, ValueError):
        importe = 0
    if importe <= 0:
        return error("IMPORTE_NO_VALIDO", "El importe del pago debe ser mayor que cero")
    if not str(p.get("referencia") or "").strip():
        return error("REFERENCIA_OBLIGATORIA", "Falta la referencia del pago (localizador de la reserva)")
    id_pago = "SP-" + uuid.uuid4().hex[:10].upper()
    pago = {
        "tipo": "pago", "idPago": id_pago, "estado": "PENDIENTE", "referencia": str(p["referencia"]),
        "concepto": str(p.get("concepto") or f"Pago {p['referencia']}"),
        "importe": round(importe * 100) / 100, "moneda": MONEDA, "pasarela": PASARELA,
        "urlPago": f"{PUBLIC_URL}/pago/{id_pago}", "creado": _ahora(), "pagadoEn": None, "codigoAutorizacion": None,
    }
    with engine.begin() as con:
        con.execute(pagos.insert().values(id_pago=id_pago, datos=pago))
    return ok(pago, 201)


@app.get("/pagos/{id_pago}")
def consultar(id_pago: str):
    idp = id_pago.upper()
    pago = _leer(idp)
    if pago is None:
        return error("PAGO_NO_ENCONTRADO", f"No existe el pago '{idp}'", 404)
    return ok(pago)


# ---------------------------------------------------------------- página de pago (HTML)
CSS = """body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f3f5f9;color:#1d2433}
.top{background:#0b2a5b;color:#fff;padding:16px 24px;font-weight:600;letter-spacing:.3px}
.card{max-width:440px;margin:32px auto;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.08);padding:28px}
h1{font-size:20px;margin:0 0 4px}.muted{color:#6b7385;font-size:14px}.importe{font-size:34px;font-weight:700;margin:18px 0}
dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:14px;margin:0 0 20px}dt{color:#6b7385}dd{margin:0}
label{display:block;font-size:13px;color:#6b7385;margin:10px 0 4px}
input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #d5dae3;border-radius:8px;font-size:15px;background:#f8f9fb}
.fila{display:flex;gap:10px}.fila>div{flex:1}
button{width:100%;padding:13px;border:0;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-top:16px}
.pagar{background:#1a7f37;color:#fff}.cancelar{background:transparent;color:#6b7385;margin-top:6px}
.ok{background:#e7f6ec;color:#1a7f37;padding:14px;border-radius:8px}.ko{background:#fdecec;color:#b42318;padding:14px;border-radius:8px}
.aviso{font-size:12px;color:#8a91a1;margin-top:18px;text-align:center}"""


def _pagina(pg, id_pago: str) -> str:
    e = lambda t: html.escape(str(t if t is not None else ""))
    if pg is None:
        cuerpo = f"<h1>Pago no encontrado</h1><p class='ko'>No existe el pago {e(id_pago)}. Pide a tu asistente un nuevo enlace de pago.</p>"
    else:
        detalle = (f"<dl><dt>Concepto</dt><dd>{e(pg['concepto'])}</dd><dt>Referencia</dt><dd>{e(pg['referencia'])}</dd>"
                   f"<dt>Id. de pago</dt><dd>{e(pg['idPago'])}</dd></dl>")
        if pg["estado"] == "PAGADO":
            cuerpo = (f"<h1>Pago completado</h1><div class='importe'>{eur(pg['importe'])}</div>{detalle}"
                      f"<p class='ok'>Pago autorizado (código {e(pg['codigoAutorizacion'])}). Ya puedes cerrar esta ventana y decirle a tu asistente: <b>«ya he pagado»</b>.</p>")
        elif pg["estado"] == "CANCELADO":
            cuerpo = f"<h1>Pago cancelado</h1>{detalle}<p class='ko'>Has cancelado el pago. Puedes pedir a tu asistente un nuevo enlace de pago.</p>"
        else:
            cuerpo = (f"<h1>Confirma tu pago</h1><div class='muted'>Reserva de viaje</div><div class='importe'>{eur(pg['importe'])}</div>{detalle}"
                      "<form method='post'><label>Titular de la tarjeta</label><input value='CLIENTE DEMO' readonly>"
                      "<label>Número de tarjeta</label><input value='4111 1111 1111 1111' readonly>"
                      "<div class='fila'><div><label>Caducidad</label><input value='12/30' readonly></div><div><label>CVV</label><input value='123' readonly></div></div>"
                      f"<button class='pagar' name='accion' value='pagar'>Pagar {eur(pg['importe'])}</button>"
                      "<button class='cancelar' name='accion' value='cancelar'>Cancelar</button></form>")
    return (f"<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>Pago seguro</title><style>{CSS}</style></head><body><div class='top'>{e(PASARELA)} · Pago seguro</div><div class='card'>{cuerpo}"
            "<p class='aviso'>Entorno de demostración: no se realiza ningún cargo real.</p></div></body></html>")


@app.get("/pago/{id_pago}", response_class=HTMLResponse)
def ver_pagina(id_pago: str):
    idp = id_pago.upper()
    pg = _leer(idp)
    return HTMLResponse(_pagina(pg, idp), status_code=200 if pg else 404)


@app.post("/pago/{id_pago}", response_class=HTMLResponse)
async def accion_pagina(id_pago: str, request: Request):
    idp = id_pago.upper()
    pg = _leer(idp)
    accion = (parse_qs((await request.body()).decode("utf-8", "ignore")).get("accion") or [""])[0]
    if pg and pg["estado"] == "PENDIENTE":
        if accion == "pagar":
            pg = {**pg, "estado": "PAGADO", "pagadoEn": _ahora(), "codigoAutorizacion": "AUT" + uuid.uuid4().hex[:6].upper()}
            _guardar(pg)
        elif accion == "cancelar":
            pg = {**pg, "estado": "CANCELADO"}
            _guardar(pg)
    return HTMLResponse(_pagina(pg, idp), status_code=200 if pg else 404)
