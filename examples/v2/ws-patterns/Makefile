.PHONY: gen clean test-all test-pattern help

# Default values
EXAMPLE ?= 01-subscribe-simple
OUTPUT ?= generated

# Paths
FDSL_BIN = ../../../venv_WSL/bin/fdsl
CLEANUP_SCRIPT = ../../../scripts/docker_cleanup.sh

help:
	@echo "WebSocket Patterns - Make Commands"
	@echo "===================================="
	@echo ""
	@echo "  make gen EXAMPLE=<pattern> OUTPUT=<dir>  - Generate code for a pattern"
	@echo "  make test-all                             - Test all patterns automatically"
	@echo "  make test-pattern EXAMPLE=<pattern>       - Test a specific pattern"
	@echo "  make clean                                - Clean up containers and generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make gen EXAMPLE=01-subscribe-simple OUTPUT=generated-test"
	@echo "  make test-all"
	@echo "  make test-pattern EXAMPLE=05-bidirectional-simple"
	@echo ""

gen:
	@echo "Generating FDSL code for $(EXAMPLE)..."
	@$(FDSL_BIN) generate $(EXAMPLE).fdsl --out $(OUTPUT)
	@echo "✓ Generated to $(OUTPUT)/"

clean:
	@echo "Cleaning up..."
	@bash $(CLEANUP_SCRIPT) 2>/dev/null || true
	@rm -rf generated-* 2>/dev/null || true
	@echo "✓ Cleanup complete"

test-all:
	@bash test-all-patterns.sh

test-pattern:
	@echo "Testing pattern: $(EXAMPLE)"
	@bash test-all-patterns.sh $(EXAMPLE)
