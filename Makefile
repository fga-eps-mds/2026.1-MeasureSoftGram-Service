COMPOSE = docker compose

.PHONY: help up down restart build rebuild logs ps clear \
        migrate migrations shell superuser \
        test test-smoke test-cov \
        bash

help:
	@echo "Targets disponiveis:"
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
	@echo "  bash         - bash dentro do service"
	@echo "  clear        - down -v --remove-orphans (apaga volumes)"

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
	$(COMPOSE) exec service python src/manage.py migrate

migrations:
	$(COMPOSE) exec service python src/manage.py makemigrations

shell:
	$(COMPOSE) exec service python src/manage.py shell

superuser:
	$(COMPOSE) exec service python src/manage.py createsuperuser

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
