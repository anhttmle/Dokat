.PHONY: help setup env run build up up-d down test lint shell

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
IMAGE := api-gateway:local

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  setup   Create venv, install deps, copy .env.example → .env"
	@echo "  env     Alias for setup"
	@echo "  shell   Open shell with virtualenv activated"
	@echo "  run     Run gateway locally (uvicorn --reload)"
	@echo "  build   Build Docker image ($(IMAGE))"
	@echo "  up      docker compose up --build"
	@echo "  up-d    docker compose up --build -d (detached)"
	@echo "  down    docker compose down"
	@echo "  test    Run pytest"
	@echo "  lint    Run ruff check + format check"

setup env: $(VENV)/bin/python
	$(PIP) install -e ".[dev]"
	@test -f .env || cp .env.example .env

$(VENV)/bin/python:
	python3 -m venv $(VENV)

shell: setup
	@echo "Virtualenv activated. Type 'exit' to leave."
	@bash --rcfile <(echo "source $(VENV)/bin/activate")

run: setup
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

build:
	docker build -t $(IMAGE) .

up:
	docker compose up --build

up-d:
	docker compose up --build -d

down:
	docker compose down

test: setup
	$(PYTEST) tests/ -v --cov=app --cov-fail-under=80

lint: setup
	$(RUFF) check .
	$(RUFF) format --check .
