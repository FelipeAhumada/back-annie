FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código  <<-- CAMBIO: copiamos el directorio "app" a /app/app
COPY app /app
ENV PYTHONPATH=/app

# Gunicorn
CMD exec gunicorn main:app \
  --bind 0.0.0.0:8080 \
  --workers ${API_WORKERS:-2} \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 60
