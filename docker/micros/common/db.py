"""Conexión a la base de datos (PostgreSQL en Docker; SQLite solo para pruebas locales sin Docker)."""
import os
import time

from sqlalchemy import create_engine


def crear_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, pool_pre_ping=True, future=True)
    # PostgreSQL puede tardar unos segundos en aceptar conexiones al arrancar el compose
    for _ in range(60):
        try:
            with engine.connect():
                return engine
        except Exception:
            time.sleep(1)
    raise RuntimeError("No se pudo conectar con la base de datos: " + url.split("@")[-1])
