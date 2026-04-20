FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements ./requirements
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY backend /app

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app

USER app
