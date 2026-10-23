# Imagen única para los 4 micros: cada servicio del docker-compose arranca el suyo con "command".
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY vuelos ./vuelos
COPY parking ./parking
COPY pagos ./pagos
COPY reservas ./reservas
ENV PYTHONUNBUFFERED=1
