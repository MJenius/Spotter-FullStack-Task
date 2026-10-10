# Developer commands (requires GNU make; Windows users can run the commands in README directly).
.PHONY: setup backend frontend test lint check

setup:
	cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm ci

backend:
	cd backend && .venv/bin/python manage.py runserver 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run typecheck && npm run lint && npm run format:check

check: lint test
	cd backend && .venv/bin/python manage.py check
	cd frontend && npm run build
