COMPOSE = docker compose

.PHONY: help env setup dev seed up down restart build rebuild logs ps clear \
        migrate migrations shell superuser \
        test test-smoke test-cov lint format migrations-check check \
        bash

help:
	@echo "Targets disponiveis:"
	@echo "  env          - copia env-vars-example -> env-vars (nao sobrescreve)"
	@echo "  setup        - do zero a stack de pe: env-vars + build + up + espera health"
	@echo "  dev          - sobe a stack com hot-reload (docker compose up --watch)"
	@echo "  seed         - popula dados (load_initial_data + seed_grafana)"
	@echo "  up           - sobe a stack em background"
	@echo "  down         - derruba a stack"
	@echo "  restart      - reinicia todos os services"
	@echo "  build        - build das imagens (sem cache)"
	@echo "  rebuild      - down + build + up"
	@echo "  logs         - tail -f de todos os logs"
	@echo "  ps           - status dos services"
	@echo "  migrate      - aplica migrations"
	@echo "  migrations   - gera novas migrations"
	@echo "  shell        - shell Django (manage.py shell)"
	@echo "  superuser    - cria superuser"
	@echo "  test         - pytest verbose"
	@echo "  test-smoke   - smokes do math_model"
	@echo "  test-cov     - pytest com coverage"
	@echo "  lint         - flake8 src/ (mesma checagem do CI)"
	@echo "  format       - black + isort no src/ (opt-in, nao roda no CI)"
	@echo "  migrations-check - detecta model sem migration (mesma checagem do CI)"
	@echo "  check        - lint + test + migrations-check (espelha o CI local)"
	@echo "  bash         - bash dentro do service"
	@echo "  clear        - down -v --remove-orphans (apaga volumes)"

# --- Onboarding -------------------------------------------------------------

# Copia os templates de ambiente. Idempotente: nao sobrescreve env-vars ja
# ajustados (as credenciais reais ficam so em env-vars/, que e gitignored).
env:
	@test -d env-vars || cp -R env-vars-example env-vars
	@echo ">>> env-vars pronto (ajuste GITHUB_CLIENT_ID/SECRET pro login GitHub; ver README)."

# Do zero a stack de pe num comando: copia os env-vars (se ainda nao existirem),
# builda as imagens, sobe e espera o container service ficar healthy (usa o
# healthcheck do compose). E idempotente: nao sobrescreve env-vars ja ajustados.
setup:
	@test -d env-vars || cp -R env-vars-example env-vars
	$(COMPOSE) build
	$(COMPOSE) up -d
	@echo ">>> aguardando o service ficar healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' service 2>/dev/null)" = "healthy" ]; do \
	    sleep 2; \
	done
	@echo ">>> stack de pe. API em http://localhost:8080/  Grafana em http://localhost:5000/"

# Sobe com hot-reload: sincroniza src/ e refaz deps quando pyproject muda
# (usa o bloco develop.watch do docker-compose.yml).
dev:
	$(COMPOSE) up --watch

# Popula as entidades suportadas e provisiona os dashboards do Grafana.
seed:
	$(COMPOSE) exec service python manage.py load_initial_data
	$(COMPOSE) exec service python manage.py seed_grafana

# --- Lifecycle --------------------------------------------------------------

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) build --no-cache

rebuild: down build up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

clear:
	$(COMPOSE) down -v --remove-orphans

# --- Django -----------------------------------------------------------------

migrate:
	$(COMPOSE) exec service python manage.py migrate

migrations:
	$(COMPOSE) exec service python manage.py makemigrations

shell:
	$(COMPOSE) exec service python manage.py shell

superuser:
	$(COMPOSE) exec service python manage.py createsuperuser

bash:
	$(COMPOSE) exec service bash

# --- Quality ----------------------------------------------------------------

test:
	$(COMPOSE) run --rm \
	    -e DJANGO_SETTINGS_MODULE=config.settings.test \
	    -w /src service /app/.venv/bin/pytest -v

test-smoke:
	$(COMPOSE) run --rm \
	    -e DJANGO_SETTINGS_MODULE=config.settings.test \
	    -w /src service /app/.venv/bin/pytest math_model/tests/test_atomicity_smoke.py -vv

test-cov:
	$(COMPOSE) run --rm \
	    -e DJANGO_SETTINGS_MODULE=config.settings.test \
	    -w /src service /app/.venv/bin/pytest --cov --cov-report=term-missing

# flake8 nao esta nas deps do projeto; o CI instala via `uv tool install`.
# uvx roda a mesma ferramenta de forma efemera, sem sujar o ambiente.
lint:
	uvx flake8 src/

# black + isort ainda nao sao deps do projeto; rodam via uvx. Opt-in: o CI
# nao exige formatacao, entao este target nao reformata em massa sozinho.
format:
	uvx black src/
	uvx isort src/

# Mesma checagem que o job de testes do CI faz (makemigrations --check),
# que hoje so falha depois de abrir o PR.
migrations-check:
	$(COMPOSE) run --rm \
	    -e DJANGO_SETTINGS_MODULE=config.settings.test \
	    -w /src service /app/.venv/bin/python manage.py makemigrations --check --dry-run

# Espelha localmente os gates do CI: flake8 + suite de testes + migrations.
check: lint test migrations-check
