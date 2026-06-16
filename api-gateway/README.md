# Dokat API Gateway

Single entry point for Dokat microservices — Firebase auth, rate limiting,
request proxying, and health checks.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Redis (included in Docker Compose)

## Setup

```bash
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY, upstream URLs, and optional AI_API_KEY
```

Required env vars are documented in [`.env.example`](.env.example).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services:

- **api-gateway** — `http://localhost:8000`
- **redis** — `localhost:6379`

Health check: `curl http://localhost:8000/health`

## Tests

```bash
# All tests
pytest

# With coverage (CI threshold: 80%)
pytest tests/ -v --cov=app --cov-fail-under=80

# Lint
ruff check .
ruff format --check .

# Docker build smoke test
bash tests/smoke/test_docker_build.sh
```

## Environment variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | yes | HS256 secret for Internal JWT |
| `REDIS_URL` | yes | Redis connection URL |
| `FIREBASE_CREDENTIALS_PATH` | yes | Path to Firebase service account JSON |
| `UPSTREAM_*_SERVICE_URL` | yes | Base URLs for each upstream service |
| `AI_API_KEY` | if `/ai/*` enabled | Third-party AI provider API key |
