# Project directories
PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
LOG_FILE := $(PROJECT_DIR)/log.ini

# Backend configuration
FASTAPI_PORT := 8000

# Docker configuration
DOCKER_FILE := $(PROJECT_DIR)/docker-compose.yml

# Shell colors
SHELL_GREEN := \033[32m
SHELL_YELLOW := \033[33m
SHELL_RED := \033[31m
SHELL_NC := \033[0m

# Default goal
.DEFAULT_GOAL := help

# Help command
help:
	@echo "$(SHELL_YELLOW)Application management:$(SHELL_NC)"
	@echo "$(SHELL_GREEN)  run$(SHELL_NC)                   - Start both the FastAPI application and Redis."
	@echo "$(SHELL_GREEN)  stop$(SHELL_NC)                  - Stop the FastAPI application and Redis."
	@echo "$(SHELL_GREEN)  start-fastapi$(SHELL_NC)         - Start the FastAPI application only."
	@echo "$(SHELL_GREEN)  kill-fastapi$(SHELL_NC)          - Terminate the FastAPI process running on port $(FASTAPI_PORT)."
	@echo "$(SHELL_GREEN)  kill-all$(SHELL_NC)              - Terminate all processes related to the application."
	@echo "$(SHELL_GREEN)  start-docker-compose$(SHELL_NC)  - Start the Redis container."
	@echo "$(SHELL_GREEN)  stop-docker-compose$(SHELL_NC)   - Stop the Redis container."
	@echo ""

kill-fastapi:
	@if lsof -i:$(FASTAPI_PORT) > /dev/null; then \
		echo "$(SHELL_YELLOW)Killing process on port $(FASTAPI_PORT)...$(SHELL_NC)"; \
		sudo kill -9 `sudo lsof -t -i:$(FASTAPI_PORT)`; \
	else \
		echo "$(SHELL_YELLOW)No process running on port $(FASTAPI_PORT).$(SHELL_NC)"; \
	fi

kill-all: kill-fastapi

start-fastapi:
	@cd $(PROJECT_DIR) && uvicorn src.app:app --reload || echo "$(SHELL_RED)Failed to start FastAPI.$(SHELL_NC)"

run: start-docker-compose start-fastapi
	@echo "$(SHELL_GREEN)FastAPI and Redis are running.$(SHELL_NC)"

run-prod: start-docker-compose
	@gunicorn --worker-class uvicorn.workers.UvicornWorker src.app:app --bind 0.0.0.0:$(FASTAPI_PORT) --log-config="logging.ini"

stop:
	@$(MAKE) kill-all && $(MAKE) stop-docker-compose || echo "$(SHELL_RED)An error occurred while stopping services.$(SHELL_NC)"

start-docker-compose:
	@docker compose -f $(DOCKER_FILE) --env-file .env up -d || \
	docker-compose -f $(DOCKER_FILE) --env-file .env up -d || \
	echo "$(SHELL_RED)Failed to start the database.$(SHELL_NC)"

stop-docker-compose:
	@docker compose -f $(DOCKER_FILE) --env-file .env down || \
	docker-compose -f $(DOCKER_FILE) --env-file .env down || \
	echo "$(SHELL_RED)Failed to stop the database.$(SHELL_NC)"
