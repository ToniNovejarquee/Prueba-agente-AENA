import json
import re
from fastapi.responses import JSONResponse


def error(codigo: str, mensaje: str, status: int = 400):
    return JSONResponse(status_code=status, content={"tipo": "error", "codigo": codigo, "mensaje": mensaje})


def ok(contenido, status: int = 200):
    return JSONResponse(status_code=status, content=contenido)


def eur(x) -> str:
    """1234.5 -> '1.234,50 €'"""
    if x is None:
        return "-"
    centimos = round(float(x) * 100)
    entero, dec = divmod(centimos, 100)
    return f"{entero:,}".replace(",", ".") + f",{dec:02d} €"


EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def vacio(x) -> bool:
    return x is None or str(x).strip() == ""


async def cuerpo_json(request):
    """Cuerpo JSON como dict; {} si viene vacío o no es un objeto."""
    try:
        d = await request.json()
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}
