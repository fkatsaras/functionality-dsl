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
clean: ## Clean generated files, Docker resources, and caches
	@echo "$(YELLOW)Cleaning previous generated app...$(NC)"
	@bash scripts/docker_cleanup.sh
	@echo "$(YELLOW)Cleaning Python caches...$(NC)"
	@rm -rf cookies.txt
	@rm -rf test_gen test_ast_gen generated_ws_test
	@rm -rf **/__pycache__ **/*.pyc **/*.pyo
	@rm -rf .pytest_cache .coverage htmlcov
	@rm -rf *.egg-info build dist
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

.PHONY: visualize
visualize: ## Visualize FDSL model (usage: make visualize FILE=path/to/file.fdsl)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE not specified$(NC)"; \
		echo "Usage: make visualize FILE=examples/v2/nested-entities/main.fdsl"; \
		exit 1; \
	fi
	@echo "$(BLUE)Generating model visualization for $(FILE)...$(NC)"
	$(FDSL) visualize $(FILE) --output docs
	@echo "$(GREEN)Visualization generated!$(NC)"
	@echo "DOT file: docs/$$(basename $(FILE) .fdsl)_diagram.dot"
	@if command -v dot > /dev/null 2>&1; then \
		echo "PNG file: docs/$$(basename $(FILE) .fdsl)_diagram.png"; \
	else \
		echo "$(YELLOW)Note: Install GraphViz to generate PNG files$(NC)"; \
		echo "To convert: dot -Tpng docs/$$(basename $(FILE) .fdsl)_diagram.dot -o docs/$$(basename $(FILE) .fdsl)_diagram.png"; \
	fi

.PHONY: viz
viz: visualize ## Alias for 'visualize'

.PHONY: viz-no-components
viz-no-components: ## Visualize without UI components (usage: make viz-no-components FILE=path/to/file.fdsl)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE not specified$(NC)"; \
		exit 1; \
	fi
	$(FDSL) visualize $(FILE) --output docs --no-components

.PHONY: viz-metamodel
viz-metamodel: ## Generate metamodel visualization (TextX grammar diagram, PlantUML)
	@echo "$(BLUE)Generating metamodel visualization...$(NC)"
	$(FDSL) visualize functionality_dsl/grammar/model.tx --output docs --metamodel --engine plantuml
	@echo "$(GREEN)Metamodel visualization generated!$(NC)"
	@echo "PlantUML file: docs/model_metamodel.pu"

.PHONY: transform
transform: ## Transform OpenAPI/AsyncAPI spec to FDSL (usage: make transform SPEC=path/to/spec.yaml)
	@if [ -z "$(SPEC)" ]; then \
		echo "$(RED)Error: SPEC not specified$(NC)"; \
		echo "Usage: make transform SPEC=examples/m2m/openapi/jsonplaceholder.yaml"; \
		echo "       make transform SPEC=api.yaml OUT=generated.fdsl"; \
		echo "       make transform SPEC=api.yaml SERVER=MyAPI PORT=3000"; \
		exit 1; \
	fi
	@echo "$(BLUE)Transforming OpenAPI/AsyncAPI spec: $(SPEC)...$(NC)"
	@if [ -n "$(OUT)" ]; then \
		$(FDSL) transform $(SPEC) --out $(OUT) $(if $(SERVER),--server-name $(SERVER)) $(if $(HOST),--host $(HOST)) $(if $(PORT),--port $(PORT)); \
	else \
		$(FDSL) transform $(SPEC) $(if $(SERVER),--server-name $(SERVER)) $(if $(HOST),--host $(HOST)) $(if $(PORT),--port $(PORT)); \
	fi
	@echo "$(GREEN)Transformation complete!$(NC)"

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

.PHONY: count-fdsl
count-fdsl: ## Count FDSL lines in example (usage: make count-fdsl EXAMPLE=rest-basics)
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "$(RED)Error: EXAMPLE not specified$(NC)"; \
		echo "Usage: make count-fdsl EXAMPLE=rest-basics"; \
		echo "       make count-fdsl EXAMPLE=delivery-tracking"; \
		exit 1; \
	fi
	@if [ ! -d "$(EXAMPLES_DIR)/$(EXAMPLE)" ]; then \
		echo "$(RED)Error: Example '$(EXAMPLE)' not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Counting FDSL lines in $(EXAMPLE) (excluding comments)...$(NC)"
	@echo ""
	@TOTAL=0; \
	for file in $$(find $(EXAMPLES_DIR)/$(EXAMPLE) -name "*.fdsl"); do \
		COUNT=$$(grep -v '^\s*//' "$$file" | grep -v '^\s*$$' | wc -l | tr -d ' '); \
		FILENAME=$$(basename "$$file"); \
		printf "  %-30s %s\n" "$$FILENAME:" "$$COUNT"; \
		TOTAL=$$((TOTAL + COUNT)); \
	done; \
	echo ""; \
	echo "$(GREEN)Total FDSL lines (minus comments): $$TOTAL$(NC)"

.PHONY: count-generated
count-generated: ## Count lines of code in generated app (usage: make count-generated APP=path/to/generated/app)
	@if [ -z "$(APP)" ]; then \
		echo "$(RED)Error: APP path not specified$(NC)"; \
		echo "Usage: make count-generated APP=generated/rest-basics"; \
		exit 1; \
	fi
	@if [ ! -d "$(APP)" ]; then \
		echo "$(RED)Error: Directory $(APP) does not exist$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Counting lines in generated app: $(APP)$(NC)"
	@echo ""
	@echo "$(YELLOW)=== Backend (Python) ===$(NC)"
	@find "$(APP)" -name "*.py" -not -path "*/venv*" -not -path "*/__pycache__/*" | xargs wc -l 2>/dev/null | tail -1 || echo "  No Python files found"
	@echo ""
	@echo "$(YELLOW)Backend breakdown:$(NC)"
	@if [ -d "$(APP)/app/api/routers" ]; then \
		echo -n "  Routers:       "; \
		find "$(APP)/app/api/routers" -name "*.py" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo "0"; \
	fi
	@if [ -d "$(APP)/app/services" ]; then \
		echo -n "  Services:      "; \
		find "$(APP)/app/services" -name "*.py" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo "0"; \
	fi
	@if [ -d "$(APP)/app/domain" ]; then \
		echo -n "  Models:        "; \
		find "$(APP)/app/domain" -name "*.py" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo "0"; \
	fi
	@if [ -d "$(APP)/app/core" ]; then \
		echo -n "  Core:          "; \
		find "$(APP)/app/core" -name "*.py" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo "0"; \
	fi
	@echo ""
	@echo "$(YELLOW)=== Frontend (Svelte/TypeScript) ===$(NC)"
	@if [ -d "$(APP)/frontend" ]; then \
		SVELTE_COUNT=$$(find "$(APP)/frontend/src" -name "*.svelte" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0); \
		TS_COUNT=$$(find "$(APP)/frontend/src" -name "*.ts" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0); \
		TOTAL_FE=$$((SVELTE_COUNT + TS_COUNT)); \
		if [ $$TOTAL_FE -gt 0 ]; then \
			echo "  Svelte:        $$SVELTE_COUNT"; \
			echo "  TypeScript:    $$TS_COUNT"; \
			echo "  Total:         $$TOTAL_FE"; \
		else \
			echo "  No frontend files found"; \
		fi \
	else \
		echo "  No frontend generated"; \
	fi
	@echo ""
	@echo "$(YELLOW)=== Infrastructure ===$(NC)"
	@if [ -f "$(APP)/Dockerfile" ]; then \
		echo -n "  Dockerfile:    "; \
		wc -l < "$(APP)/Dockerfile"; \
	fi
	@if [ -f "$(APP)/docker-compose.yml" ]; then \
		echo -n "  Compose:       "; \
		wc -l < "$(APP)/docker-compose.yml"; \
	fi
	@if [ -f "$(APP)/pyproject.toml" ]; then \
		echo -n "  Pyproject:     "; \
		wc -l < "$(APP)/pyproject.toml"; \
	fi
	@echo ""
	@echo "$(GREEN)=== Total Generated Code ===$(NC)"
	@TOTAL=0; \
	PY=$$(find "$(APP)" -name "*.py" -not -path "*/venv*" -not -path "*/__pycache__/*" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0); \
	SVELTE=$$(find "$(APP)/frontend/src" -name "*.svelte" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0); \
	TS=$$(find "$(APP)/frontend/src" -name "*.ts" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}' || echo 0); \
	DOCKER=$$(wc -l < "$(APP)/Dockerfile" 2>/dev/null || echo 0); \
	COMPOSE=$$(wc -l < "$(APP)/docker-compose.yml" 2>/dev/null || echo 0); \
	PYPROJECT=$$(wc -l < "$(APP)/pyproject.toml" 2>/dev/null || echo 0); \
	TOTAL=$$((PY + SVELTE + TS + DOCKER + COMPOSE + PYPROJECT)); \
	echo "  Total lines:   $$TOTAL"
	@echo ""

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
# Syntax Highlighting
# ==============================================================================

.PHONY: syntax-build
syntax-build: ## Build VS Code syntax highlighting extension
	@echo "$(BLUE)Building syntax highlighting extension...$(NC)"
	cd functionality_dsl/syntax && npx @vscode/vsce package
	@echo "$(GREEN)Extension built successfully!$(NC)"
	@echo "Install with: make syntax-install"

.PHONY: syntax-install
syntax-install: ## Install syntax highlighting extension to VS Code
	@echo "$(BLUE)Installing syntax highlighting extension...$(NC)"
	@VSIX=$$(ls -t functionality_dsl/syntax/*.vsix 2>/dev/null | head -n1); \
	if [ -z "$$VSIX" ]; then \
		echo "$(RED)Error: No .vsix file found. Run 'make syntax-build' first$(NC)"; \
		exit 1; \
	fi; \
	echo "Installing $$VSIX..."; \
	code --install-extension "$$VSIX" --force || echo "$(YELLOW)Note: 'code' command not found. Install manually from VS Code Extensions view$(NC)"
	@echo "$(GREEN)Extension installed! Reload VS Code to activate.$(NC)"

.PHONY: syntax-update
syntax-update: syntax-build syntax-install ## Build and install syntax highlighting (full update)

.PHONY: syntax
syntax: syntax-update ## Alias for syntax-update

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
