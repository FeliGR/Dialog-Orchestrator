# Makefile en la raíz del repo
PYTHON ?= python3
ENGINE_URL ?= http://localhost:5001
DIALOG_URL ?= http://localhost:5002

# Default target
.PHONY: run-experiments
run-experiments: ensure-up dirs personas matrix reports

.PHONY: ensure-up
ensure-up:
	@echo "🔍 Verificando servicios..."
	@curl -fsS $(ENGINE_URL)/health >/dev/null || (echo "❌ ERROR: Persona Engine no responde en $(ENGINE_URL)"; exit 1)
	@curl -fsS $(DIALOG_URL)/health >/dev/null || (echo "❌ ERROR: Dialog Orchestrator no responde en $(DIALOG_URL)"; exit 1)
	@echo "✅ Servicios OK"

.PHONY: dirs
dirs:
	@mkdir -p runs experiments scripts inventories

# Personas "dummy" mínimas para verificar conectividad (el orquestador las sobreescribe por condición)
.PHONY: personas
personas:
	@echo "🧑‍💼 Verificando conectividad con Persona Engine..."
	@ENGINE_URL=$(ENGINE_URL) bash scripts/set_persona.sh NEUTRAL 3 3 3 3 3

# Corre TODO el experimento orquestado (set personas por condición, correr runner, agregar, consolidar)
.PHONY: matrix
matrix:
	@echo "🚀 Ejecutando experimentos MPI-AE completos..."
	@ENGINE_URL=$(ENGINE_URL) DIALOG_URL=$(DIALOG_URL) $(PYTHON) experiments/run_all.py

# Alias
.PHONY: reports
reports:
	@echo "📊 Reportes generados en runs/<COND>/*.md y resumen en runs/summary.csv"
	@echo "📈 Sensibilidad en runs/sensitivity_E_grad.json"

.PHONY: clean-runs
clean-runs:
	@echo "🧹 Limpiando resultados anteriores..."
	rm -rf runs/*

.PHONY: quick-test
quick-test: ensure-up
	@echo "⚡ Ejecutando test rápido (solo NEUTRAL, 1 seed)..."
	@ENGINE_URL=$(ENGINE_URL) DIALOG_URL=$(DIALOG_URL) $(PYTHON) experiments/quick_test.py

.PHONY: help
help:
	@echo "🎯 Targets disponibles:"
	@echo "  make run-experiments   -> Ejecuta TODO (personas + corridas + reportes + resumen)"
	@echo "  make quick-test        -> Test rápido con solo NEUTRAL"
	@echo "  make clean-runs        -> Limpia la carpeta runs/"
	@echo ""
	@echo "⚙️  Variables de entorno:"
	@echo "  ENGINE_URL=$(ENGINE_URL)"
	@echo "  DIALOG_URL=$(DIALOG_URL)"
	@echo "  PYTHON=$(PYTHON)"
