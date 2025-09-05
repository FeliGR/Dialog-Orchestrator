# MPI-AE Experimental Framework Makefile
PYTHON ?= python3
ENGINE_URL ?= http://localhost:5001
DIALOG_URL ?= http://localhost:5002

# Default target - show help instead of running experiments
.PHONY: help
help:
	@echo ""
	@echo "MPI-AE Experimental Framework"
	@echo "=============================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  help              Show this help message (default)"
	@echo "  health-check      Verify services are running"
	@echo "  quick-test        Run single NEUTRAL condition test"
	@echo "  run-experiments   Execute complete experimental matrix"
	@echo "  validate          Run experimental validation checks"
	@echo "  clean             Clean generated results and reports"
	@echo ""
	@echo "Service URLs:"
	@echo "  Persona Engine:      $(ENGINE_URL)"
	@echo "  Dialog Orchestrator: $(DIALOG_URL)"
	@echo ""

.PHONY: health-check
health-check: ensure-up

.PHONY: ensure-up
ensure-up:
	@echo ""
	@echo "Checking service availability..."
	@curl -fsS $(ENGINE_URL)/health >/dev/null || (echo "ERROR: Persona Engine not responding at $(ENGINE_URL)"; exit 1)
	@curl -fsS $(DIALOG_URL)/health >/dev/null || (echo "ERROR: Dialog Orchestrator not responding at $(DIALOG_URL)"; exit 1)
	@echo "Services are running properly"
	@echo ""

.PHONY: dirs
dirs:
	@mkdir -p runs experiments scripts inventories

# Minimal persona verification (orchestrator will override per condition)
.PHONY: personas
personas:
	@echo "Verifying Persona Engine connectivity..."
	@ENGINE_URL=$(ENGINE_URL) bash scripts/set_persona.sh NEUTRAL 3 3 3 3 3
	@echo ""

.PHONY: quick-test
quick-test: ensure-up
	@echo ""
	@echo "Running quick test (NEUTRAL condition only, single seed)..."
	@ENGINE_URL=$(ENGINE_URL) DIALOG_URL=$(DIALOG_URL) $(PYTHON) experiments/quick_test.py
	@echo ""

# Execute complete orchestrated experiment (set personas per condition, run assessments, aggregate, consolidate)
.PHONY: matrix
matrix:
	@echo "Executing complete MPI-AE experimental matrix..."
	@ENGINE_URL=$(ENGINE_URL) DIALOG_URL=$(DIALOG_URL) $(PYTHON) experiments/run_all.py
	@echo ""

# Generate reports and analysis
.PHONY: reports
reports:
	@echo "Generating consolidated reports..."
	@$(PYTHON) experiments/summarize.py
	@echo ""
	@echo "Summary available at runs/summary.csv"
	@echo ""
	@echo "Validating experimental results..."
	@$(PYTHON) experiments/checks.py
	@echo ""

.PHONY: summary
summary:
	@echo ""
	@echo "Generating global summary..."
	@$(PYTHON) experiments/summarize.py
	@echo ""

.PHONY: checks
checks:
	@echo ""
	@echo "Validating experimental results..."
	@$(PYTHON) experiments/checks.py
	@echo ""

.PHONY: validate
validate: checks

# Complete experimental workflow
.PHONY: run-experiments
run-experiments: ensure-up dirs personas matrix reports
	@echo ""
	@echo "Complete experimental matrix execution finished"
	@echo ""

.PHONY: ci
ci: ensure-up quick-test summary checks
	@echo "CI Pipeline completed successfully"
	@echo ""

.PHONY: clean
clean: clean-runs

.PHONY: clean-runs
clean-runs:
	@echo ""
	@echo "Cleaning previous experimental results..."
	@rm -rf runs/*
	@echo "Results directory cleaned"
	@echo ""
