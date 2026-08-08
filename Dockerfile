# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 3000

# Bind 0.0.0.0 so the container accepts traffic from outside
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
