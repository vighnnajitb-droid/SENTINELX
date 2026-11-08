FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y libpq-dev gcc \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
