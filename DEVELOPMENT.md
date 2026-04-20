# Development Guide

## Repository layout

- `backend/`: Django application, REST API, Celery wiring, and domain models
- `frontend/`: Vite + React + TypeScript application
- `docker-compose.yml`: local container topology for Postgres, Redis, API, worker, beat, and frontend

## Phase 1 scope delivered here

- Authentication with token-based API access
- Organization and role membership model
- Invitation flow with first-login password rotation
- Admin impersonation entry point
- Strategy CRUD with immutable versions and backend validation
- Admin surface for users and invitations
- Broker account, portfolio, deployment, and audit models scaffolded for later phases

## Core assumptions

- The current delivery treats Phase 1 as the implemented milestone.
- The schema and model boundaries are intentionally ready for future multi-organization expansion.
- Strategy logic is declarative JSON, not user-authored Python.
- Backtesting and live execution are not implemented yet, but their target models and UI routes are in place.

## Local backend workflow

1. Create a virtual environment in the repo root.
2. Install `backend/requirements/dev.txt`.
3. Set environment variables from `.env.example`.
4. From `backend/`, run migrations and create a superuser.
5. Start the API with `python manage.py runserver`.

## Local frontend workflow

1. Install dependencies inside `frontend/`.
2. Run `npm run dev`.
3. The frontend will proxy `/api` requests to the Django server in local development.

## Docker workflow

1. Copy `.env.example` to `.env`.
2. Set `DJANGO_DB_ENGINE=postgres`.
3. Run `docker compose up --build`.

## Extension notes

- Backtests should attach to the existing strategy definition contract, not invent a separate schema.
- Live execution should consume `StrategyVersion`, `BrokerAccount`, `Portfolio`, and `LiveDeployment` rather than redefining those boundaries.
- Object-level permissions should continue to use organization-scoped membership checks as new apps are added.
