# Micros FastAPI + PostgreSQL

    docker compose up -d --build

Comprobar (deben responder {"estado":"ok"}):
http://localhost:8201/health  (vuelos) · 8202 (parking) · 8203 (pagos) · 8101 (reservas)

Parar: `docker compose down`   ·   Borrar datos: `docker compose down -v`
Ver BBDD: host localhost, puerto 5433, usuario poc, clave poc (bases: vuelos, parking, pagos, reservas).
