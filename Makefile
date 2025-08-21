COMPOSE = docker compose
PROFILE_MIGRATION = --profile migration

up:
	$(COMPOSE) $(PROFILE_MIGRATION) up --build

up-app:
	$(COMPOSE) up --build app db

migrate:
	$(COMPOSE) $(PROFILE_MIGRATION) up migrations

down:
	$(COMPOSE) down

rebuild:
	$(COMPOSE) build --no-cache
	$(MAKE) up

logs:
	$(COMPOSE) logs -f

clean-db:
	$(COMPOSE) down -v
