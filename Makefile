# Functionality DSL (FDSL) - Makefile
# Easy entry points for development, testing, and deployment
#
# Platform Support:
#   - Linux/macOS: Native make support
#   - Windows: Requires WSL, Git Bash, or make for Windows
#   - CI/CD: Works in GitHub Actions and other CI environments
#
# Usage without venv:
#   This Makefile will fall back to system Python/pip/pytest if no venv is found

# Auto-detect platform and set appropriate paths
ifeq ($(OS),Windows_NT)
	# Windows (cmd/PowerShell)
	VENV_DIR := venv_WIN
	VENV_BIN := $(VENV_DIR)/Scripts
	PYTHON_EXT := .exe
else
	# Unix-like (Linux/macOS/WSL)
	VENV_DIR := venv_WSL
	VENV_BIN := $(VENV_DIR)/bin
	PYTHON_EXT :=
endif

# Try to use venv if it exists, otherwise fall back to system Python
PYTHON := $(shell if [ -f "$(VENV_BIN)/python$(PYTHON_EXT)" ]; then echo "$(VENV_BIN)/python$(PYTHON_EXT)"; else echo "python3"; fi)
FDSL := $(shell if [ -f "$(VENV_BIN)/fdsl$(PYTHON_EXT)" ]; then echo "$(VENV_BIN)/fdsl$(PYTHON_EXT)"; else echo "fdsl"; fi)
PIP := $(shell if [ -f "$(VENV_BIN)/pip$(PYTHON_EXT)" ]; then echo "$(VENV_BIN)/pip$(PYTHON_EXT)"; else echo "pip3"; fi)
PYTEST := $(shell if [ -f "$(VENV_BIN)/pytest$(PYTHON_EXT)" ]; then echo "$(VENV_BIN)/pytest$(PYTHON_EXT)"; else echo "pytest"; fi)

# Directories
EXAMPLES_DIR := examples
TESTS_DIR := tests
GENERATED_DIR := generated

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Functionality DSL - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

.PHONY: env-info
env-info: ## Show detected environment and paths
	@echo "$(BLUE)Environment Information$(NC)"
	@echo "Platform: $(OS)"
	@echo "Virtual environment: $(VENV_DIR)"
	@echo "Python: $(PYTHON)"
	@echo "FDSL: $(FDSL)"
	@echo "Pytest: $(PYTEST)"
	@echo "PIP: $(PIP)"

# ==============================================================================
# Setup & Installation
# ==============================================================================

.PHONY: setup
setup: ## Install dependencies and set up development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment at $(VENV_DIR)..."; \
		python3 -m venv $(VENV_DIR) || python -m venv $(VENV_DIR); \
	fi
	@echo "Installing dependencies..."
	$(PIP) install -e .
	$(PIP) install pytest pytest-cov black flake8
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "Virtual environment: $(VENV_DIR)"
	@echo "Python: $(PYTHON)"

.PHONY: clean
clean: ## Clean generated files and caches
	@echo "$(YELLOW)Cleaning generated files...$(NC)"
	rm -rf $(GENERATED_DIR)
	rm -rf test_gen test_ast_gen generated_ws_test
	rm -rf **/__pycache__ **/*.pyc **/*.pyo
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf *.egg-info build dist
	@echo "$(GREEN)Clean complete!$(NC)"

# ==============================================================================
# Validation
# ==============================================================================

.PHONY: validate-all
validate-all: ## Validate all example FDSL files
	@echo "$(BLUE)Validating all examples...$(NC)"
	@for dir in $(EXAMPLES_DIR)/*; do \
		if [ -d "$$dir" ]; then \
			echo "$(YELLOW)Checking $$dir...$(NC)"; \
			for file in $$dir/*.fdsl; do \
				if [ -f "$$file" ]; then \
					echo "  Validating $$file..."; \
					$(FDSL) validate "$$file" || exit 1; \
				fi \
			done \
		fi \
	done
	@echo "$(GREEN)All examples validated successfully!$(NC)"

.PHONY: validate-tests
validate-tests: ## Validate test FDSL files (pass and fail cases)
	@echo "$(BLUE)Validating test files...$(NC)"
	@echo "$(YELLOW)=== PASS Tests (should succeed) ===$(NC)"
	@find $(TESTS_DIR) -name "*-pass.fdsl" | while read file; do \
		echo "   $$file"; \
		$(FDSL) validate "$$file" > /dev/null 2>&1 || (echo "$(RED)FAILED (expected pass)$(NC)" && exit 1); \
	done
	@echo "$(YELLOW)=== FAIL Tests (should fail) ===$(NC)"
	@find $(TESTS_DIR) -name "*-fail.fdsl" | while read file; do \
		echo "   $$file"; \
		$(FDSL) validate "$$file" > /dev/null 2>&1 && (echo "$(RED)PASSED (expected fail)$(NC)" && exit 1) || true; \
	done
	@echo "$(GREEN)All test validations passed!$(NC)"

.PHONY: validate
validate: ## Validate a specific file (usage: make validate FILE=path/to/file.fdsl)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE not specified$(NC)"; \
		echo "Usage: make validate FILE=examples/rest-basics/main.fdsl"; \
		exit 1; \
	fi
	@echo "$(BLUE)Validating $(FILE)...$(NC)"
	$(FDSL) validate $(FILE)

# ==============================================================================
# Code Generation
# ==============================================================================

.PHONY: generate
generate: ## Generate code from FDSL file (usage: make generate FILE=path/to/file.fdsl)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE not specified$(NC)"; \
		echo "Usage: make generate FILE=examples/rest-basics/main.fdsl"; \
		exit 1; \
	fi
	@echo "$(BLUE)Generating code from $(FILE)...$(NC)"
	$(FDSL) generate $(FILE) --out $(GENERATED_DIR)
	@echo "$(GREEN)Code generated in $(GENERATED_DIR)/$(NC)"

.PHONY: generate-all
generate-all: ## Generate code for all examples
	@echo "$(BLUE)Generating code for all examples...$(NC)"
	@for example in rest-basics json-parsing user-management websocket-chat iot-sensors; do \
		echo "$(YELLOW)Generating $$example...$(NC)"; \
		$(FDSL) generate $(EXAMPLES_DIR)/$$example/main.fdsl --out $(GENERATED_DIR)/$$example || exit 1; \
	done
	@echo "$(GREEN)All examples generated!$(NC)"

.PHONY: gen
gen: generate ## Alias for 'generate'

# ==============================================================================
# Testing
# ==============================================================================

.PHONY: test
test: ## Run all tests (validation + unit tests)
	@echo "$(BLUE)Running all tests...$(NC)"
	$(PYTEST) $(TESTS_DIR) -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) $(TESTS_DIR) -v -k "not integration"

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) $(TESTS_DIR)/integration -v

.PHONY: test-validation
test-validation: validate-tests ## Alias for validate-tests

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) $(TESTS_DIR) --cov=functionality_dsl --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

# ==============================================================================
# Docker & Deployment
# ==============================================================================

.PHONY: docker-build
docker-build: ## Build Docker image for generated app
	@if [ ! -d "$(GENERATED_DIR)" ]; then \
		echo "$(RED)Error: No generated code found$(NC)"; \
		echo "Run 'make generate FILE=...' first"; \
		exit 1; \
	fi
	@echo "$(BLUE)Building Docker image...$(NC)"
	cd $(GENERATED_DIR) && docker compose -p thesis build
	@echo "$(GREEN)Docker image built!$(NC)"

.PHONY: docker-up
docker-up: ## Start generated app in Docker
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	cd $(GENERATED_DIR) && docker compose -p thesis up -d
	@echo "$(GREEN)Containers started!$(NC)"

.PHONY: docker-down
docker-down: ## Stop Docker containers
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	cd $(GENERATED_DIR) && docker compose -p thesis down
	@echo "$(GREEN)Containers stopped!$(NC)"

.PHONY: docker-logs
docker-logs: ## Show Docker container logs
	cd $(GENERATED_DIR) && docker compose -p thesis logs -f

.PHONY: docker-clean
docker-clean: ## Clean all Docker resources (containers, images, networks)
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	bash scripts/cleanup.sh
	@echo "$(GREEN)Docker cleanup complete!$(NC)"

# ==============================================================================
# Development
# ==============================================================================

.PHONY: format
format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	$(PYTHON) -m black functionality_dsl/
	@echo "$(GREEN)Formatting complete!$(NC)"

.PHONY: lint
lint: ## Lint code with flake8
	@echo "$(BLUE)Linting code...$(NC)"
	$(PYTHON) -m flake8 functionality_dsl/ --max-line-length=120
	@echo "$(GREEN)Linting complete!$(NC)"

.PHONY: check
check: lint validate-all ## Run all checks (lint + validate)

# ==============================================================================
# Quick Examples
# ==============================================================================

.PHONY: demo-rest
demo-rest: ## Generate and run REST basics example
	@echo "$(BLUE)Running REST basics demo...$(NC)"
	$(FDSL) generate $(EXAMPLES_DIR)/rest-basics/main.fdsl --out $(GENERATED_DIR)/demo
	cd $(GENERATED_DIR)/demo && docker compose -p thesis up

.PHONY: demo-ws
demo-ws: ## Generate and run WebSocket chat example
	@echo "$(BLUE)Running WebSocket chat demo...$(NC)"
	$(FDSL) generate $(EXAMPLES_DIR)/websocket-chat/main.fdsl --out $(GENERATED_DIR)/demo
	cd $(GENERATED_DIR)/demo && docker compose -p thesis up

.PHONY: demo-users
demo-users: ## Generate and run user management example
	@echo "$(BLUE)Running user management demo...$(NC)"
	$(FDSL) generate $(EXAMPLES_DIR)/user-management/login.fdsl --out $(GENERATED_DIR)/demo
	cd $(GENERATED_DIR)/demo && docker compose -p thesis up

# ==============================================================================
# Utilities
# ==============================================================================

.PHONY: count-lines
count-lines: ## Count lines of code in the project
	@echo "$(BLUE)Counting lines of code...$(NC)"
	@find functionality_dsl -name "*.py" | xargs wc -l | tail -1
	@find examples -name "*.fdsl" | xargs wc -l | tail -1

.PHONY: show-structure
show-structure: ## Show project directory structure
	@echo "$(BLUE)Project Structure:$(NC)"
	@find . -type d -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/venv*' -not -path '*/__pycache__/*' | sed 's|[^/]*/| |g'

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Dev dependencies installed!$(NC)"

# ==============================================================================
# Common Workflows
# ==============================================================================

.PHONY: dev
dev: clean validate-all test ## Full development workflow (clean, validate, test)

.PHONY: quick-test
quick-test: ## Quick validation of core examples
	@echo "$(BLUE)Quick validation test...$(NC)"
	$(FDSL) validate $(EXAMPLES_DIR)/rest-basics/main.fdsl
	$(FDSL) validate $(EXAMPLES_DIR)/websocket-chat/main.fdsl
	$(FDSL) validate $(EXAMPLES_DIR)/user-management/register.fdsl
	@echo "$(GREEN)Quick test passed!$(NC)"

.PHONY: full-test
full-test: clean validate-all validate-tests test-cov ## Full test suite with coverage

# Default target
.DEFAULT_GOAL := help
