PYTHON  := .venv/bin/python
PIP     := .venv/bin/pip
PYTEST  := .venv/bin/pytest
RUFF    := .venv/bin/ruff
BLACK   := .venv/bin/black
UVICORN := .venv/bin/uvicorn

.PHONY: install test test-integration lint run migrate

install:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

test:
	$(PYTEST) --ignore=tests/integration; \
	EXIT=$$?; [ $$EXIT -eq 0 ] || [ $$EXIT -eq 5 ]

test-integration:
	$(PYTEST) tests/integration/ -v; \
	EXIT=$$?; [ $$EXIT -eq 0 ] || [ $$EXIT -eq 5 ]

lint:
	$(RUFF) check app tests
	$(BLACK) --check app tests

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	.venv/bin/alembic upgrade head
