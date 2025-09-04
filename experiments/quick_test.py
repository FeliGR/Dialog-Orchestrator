#!/usr/bin/env python3
"""
Quick test - Solo una corrida NEUTRAL para verificar que todo funciona
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Configuración mínima
ENGINE_URL = os.getenv("ENGINE_URL", "http://localhost:5001")
DIALOG_URL = os.getenv("DIALOG_URL", "http://localhost:5002")
SEED = 111
USER_ID = "NEUTRAL"

def set_persona_neutral():
    """Configura persona NEUTRAL"""
    script_path = Path(__file__).parent.parent / "scripts" / "set_persona.sh"
    cmd = [
        "bash", str(script_path),
        USER_ID, "3", "3", "3", "3", "3"
    ]
    subprocess.run(cmd, check=True, env={**os.environ, "ENGINE_URL": ENGINE_URL})
    print(f"✅ Persona {USER_ID} configurada")

def run_quick_test():
    """Ejecuta una sola corrida MPI"""
    print(f"🧪 Test rápido: {USER_ID}, seed={SEED}")
    
    # Preparar directorios
    runs_dir = Path(__file__).parent.parent / "runs"
    test_dir = runs_dir / "quick-test"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Archivo de salida
    output_file = test_dir / f"quick_test_seed_{SEED}.json"
    
    # Ejecutar MPI runner
    csv_path = Path(__file__).parent.parent / "inventories" / "mpi_120.csv"
    runner_path = Path(__file__).parent.parent / "eval" / "run_mpi_http.py"
    
    args = [
        "python3", str(runner_path),
        "--csv", str(csv_path),
        "--url", f"{DIALOG_URL}",
        "--user", USER_ID,
        "--output", str(output_file),
        "--seed", str(SEED)
    ]
    
    print(f"▶ Ejecutando: {' '.join(args)}")
    subprocess.run(args, check=True)
    
    # Mostrar resultados básicos
    if output_file.exists():
        with open(output_file) as f:
            data = json.load(f)
        
        # El formato del JSON usa "results" no "responses"
        valid_count = len([r for r in data["results"] if r["response"] != "UNKNOWN"])
        total_count = len(data["results"])
        
        print(f"✅ Test completado: {valid_count}/{total_count} respuestas válidas")
        print(f"📁 Resultados en: {output_file}")
    
    return output_file

def main():
    print("⚡ QUICK TEST - Solo una corrida NEUTRAL")
    print("-" * 40)
    
    try:
        # 1. Configurar persona
        set_persona_neutral()
        
        # 2. Ejecutar test
        result_file = run_quick_test()
        
        print("-" * 40)
        print("✅ Quick test completado exitosamente")
        print(f"📊 Archivo resultado: {result_file}")
        
    except Exception as e:
        print(f"❌ Error en quick test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
