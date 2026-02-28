FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY src ./src
COPY .env.example ./.env.example
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "src/main.py"]
