"""Catálogo de aeropuertos de la POC (el mismo que usaba el mock de Mule)."""
import math
import unicodedata

AEROPUERTOS = {
    "MAD": dict(nombre="Adolfo Suárez Madrid-Barajas", ciudad="Madrid", pais="España", aena=True, terminal="T4", lat=40.4719, lon=-3.5626, tz=1, alias=["madrid", "barajas", "madrid-barajas"]),
    "BCN": dict(nombre="Josep Tarradellas Barcelona-El Prat", ciudad="Barcelona", pais="España", aena=True, terminal="T1", lat=41.2971, lon=2.0785, tz=1, alias=["barcelona", "el prat"]),
    "AGP": dict(nombre="Málaga-Costa del Sol", ciudad="Málaga", pais="España", aena=True, terminal="T3", lat=36.6749, lon=-4.4991, tz=1, alias=["malaga"]),
    "PMI": dict(nombre="Palma de Mallorca", ciudad="Palma", pais="España", aena=True, terminal="T", lat=39.5517, lon=2.7388, tz=1, alias=["palma", "mallorca", "palma de mallorca"]),
    "SVQ": dict(nombre="Sevilla", ciudad="Sevilla", pais="España", aena=True, terminal="T", lat=37.4180, lon=-5.8931, tz=1, alias=["sevilla", "seville"]),
    "VLC": dict(nombre="Valencia", ciudad="Valencia", pais="España", aena=True, terminal="T", lat=39.4893, lon=-0.4816, tz=1, alias=["valencia"]),
    "ALC": dict(nombre="Alicante-Elche Miguel Hernández", ciudad="Alicante", pais="España", aena=True, terminal="T", lat=38.2822, lon=-0.5582, tz=1, alias=["alicante", "elche"]),
    "BIO": dict(nombre="Bilbao", ciudad="Bilbao", pais="España", aena=True, terminal="T", lat=43.3011, lon=-2.9106, tz=1, alias=["bilbao"]),
    "LPA": dict(nombre="Gran Canaria", ciudad="Las Palmas de Gran Canaria", pais="España", aena=True, terminal="T", lat=27.9319, lon=-15.3866, tz=0, alias=["gran canaria", "las palmas"]),
    "TFN": dict(nombre="Tenerife Norte-Ciudad de La Laguna", ciudad="Tenerife", pais="España", aena=True, terminal="T", lat=28.4827, lon=-16.3415, tz=0, alias=["tenerife", "tenerife norte"]),
    "LHR": dict(nombre="Londres Heathrow", ciudad="Londres", pais="Reino Unido", aena=False, terminal="T5", lat=51.4700, lon=-0.4543, tz=0, alias=["londres", "london", "heathrow"]),
    "CDG": dict(nombre="París-Charles de Gaulle", ciudad="París", pais="Francia", aena=False, terminal="T2", lat=49.0097, lon=2.5479, tz=1, alias=["paris", "charles de gaulle"]),
    "FCO": dict(nombre="Roma Fiumicino", ciudad="Roma", pais="Italia", aena=False, terminal="T1", lat=41.8003, lon=12.2389, tz=1, alias=["roma", "rome", "fiumicino"]),
    "AMS": dict(nombre="Ámsterdam Schiphol", ciudad="Ámsterdam", pais="Países Bajos", aena=False, terminal="T", lat=52.3105, lon=4.7683, tz=1, alias=["amsterdam", "schiphol"]),
    "LIS": dict(nombre="Lisboa Humberto Delgado", ciudad="Lisboa", pais="Portugal", aena=False, terminal="T1", lat=38.7742, lon=-9.1342, tz=0, alias=["lisboa", "lisbon"]),
    "FRA": dict(nombre="Fráncfort", ciudad="Fráncfort", pais="Alemania", aena=False, terminal="T1", lat=50.0379, lon=8.5622, tz=1, alias=["francfort", "frankfurt"]),
    "JFK": dict(nombre="Nueva York John F. Kennedy", ciudad="Nueva York", pais="Estados Unidos", aena=False, terminal="T1", lat=40.6413, lon=-73.7781, tz=-5, alias=["nueva york", "new york", "jfk"]),
}

CODIGOS_CONOCIDOS = ", ".join(AEROPUERTOS)


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def codigo_aeropuerto(texto):
    """Código IATA a partir de un código o de una ciudad/aeropuerto; None si no se conoce."""
    t = (texto or "").strip() if isinstance(texto, str) else ""
    if t.upper() in AEROPUERTOS:
        return t.upper()
    nombre = sin_tildes(t)
    for codigo, a in AEROPUERTOS.items():
        if nombre in a["alias"]:
            return codigo
    return None


def info_aeropuerto(codigo):
    a = AEROPUERTOS.get(codigo)
    if not a:
        return None
    return {"codigo": codigo, "aeropuerto": a["nombre"], "ciudad": a["ciudad"], "pais": a["pais"],
            "terminal": a["terminal"], "redAena": a["aena"]}


def distancia_km(a, b) -> int:
    """Distancia en círculo máximo (haversine)."""
    r = math.radians
    dlat, dlon = r(b["lat"] - a["lat"]), r(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(r(a["lat"])) * math.cos(r(b["lat"])) * math.sin(dlon / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)))
