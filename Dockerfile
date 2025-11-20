# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The bot reads BOT_TOKEN from the environment and uses ./data for the database
VOLUME ["/app/data"]

CMD ["python", "main.py"]
