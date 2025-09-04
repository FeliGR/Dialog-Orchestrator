#!/usr/bin/env python3
# experiments/run_all.py
import os, sys, json, time, math, subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Config básica ----------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "eval" / "run_mpi_http.py"
AGG_MOD = REPO_ROOT / "eval" / "mpi_aggregator.py"
CSV_PATH = REPO_ROOT / "inventories" / "mpi_120.csv"

PERSONA_ENGINE = os.environ.get("ENGINE_URL", "http://localhost:5001")
DIALOG_URL     = os.environ.get("DIALOG_URL", "http://localhost:5002")

RUNS_DIR = REPO_ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# semillas y orden
SEEDS = [111, 222, 333]
ORDER_SEEDS: List[Optional[int]] = [None, 7]

# Condiciones (target indica el rasgo bajo prueba)
# Map códigos O,C,E,A,N a nombres: openness, conscientiousness, extraversion, agreeableness, neuroticism
CONDITIONS: Dict[str, Dict] = {
    "NEUTRAL": {"openness":3.0, "conscientiousness":3.0, "extraversion":3.0, "agreeableness":3.0, "neuroticism":3.0, "target": None},
    "E_HIGH":  {"openness":3.0, "conscientiousness":3.0, "extraversion":4.5, "agreeableness":3.0, "neuroticism":3.0, "target": "E"},
    "C_HIGH":  {"openness":3.0, "conscientiousness":4.5, "extraversion":3.0, "agreeableness":3.0, "neuroticism":3.0, "target": "C"},
    "N_LOW":   {"openness":3.0, "conscientiousness":3.0, "extraversion":3.0, "agreeableness":3.0, "neuroticism":2.0, "target": "N"},
    # Gradiente de E (sensibilidad)
    "E_20":    {"openness":3.0, "conscientiousness":3.0, "extraversion":2.0, "agreeableness":3.0, "neuroticism":3.0, "target": "E"},
    "E_30":    {"openness":3.0, "conscientiousness":3.0, "extraversion":3.0, "agreeableness":3.0, "neuroticism":3.0, "target": "E"},
    "E_40":    {"openness":3.0, "conscientiousness":3.0, "extraversion":4.0, "agreeableness":3.0, "neuroticism":3.0, "target": "E"},
    "E_50":    {"openness":3.0, "conscientiousness":3.0, "extraversion":5.0, "agreeableness":3.0, "neuroticism":3.0, "target": "E"},
    # Perfil real del test_user
    "TEST_USER": {"openness":3.0, "conscientiousness":4.2, "extraversion":4.5, "agreeableness":3.0, "neuroticism":2.1, "target": None},
}

TRAIT_CODE_MAP = {"openness":"O","conscientiousness":"C","extraversion":"E","agreeableness":"A","neuroticism":"N"}
CODE_TO_NAME = {v:k for k,v in TRAIT_CODE_MAP.items()}
CODES = ["O","C","E","A","N"]

# --- Utils HTTP persona engine ----------------------------------------------
import requests

def set_persona(user_id: str, config: Dict[str,float]) -> None:
    # create (idempotente)
    requests.post(f"{PERSONA_ENGINE}/api/personas/", json={"user_id": user_id}, timeout=10)
    # update 5 rasgos
    for trait, val in config.items():
        if trait=="target": continue
        requests.put(f"{PERSONA_ENGINE}/api/personas/{user_id}",
                     json={"trait": trait, "value": float(val)}, timeout=10)

def get_persona(user_id: str) -> Dict[str,float]:
    r = requests.get(f"{PERSONA_ENGINE}/api/personas/{user_id}", timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {})
    # Devuelve nombres largos, el agregador los entiende
    return {
        "openness": data.get("openness",3.0),
        "conscientiousness": data.get("conscientiousness",3.0),
        "extraversion": data.get("extraversion",3.0),
        "agreeableness": data.get("agreeableness",3.0),
        "neuroticism": data.get("neuroticism",3.0),
    }

# --- Llamadas a runner/aggregador -------------------------------------------
def run_mpi(user_id: str, out_path: Path, seed: int, order_seed: Optional[int]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable, str(RUNNER),
        "--csv", str(CSV_PATH),
        "--url", DIALOG_URL,
        "--user", user_id,
        "--output", str(out_path),
        "--seed", str(seed),
    ]
    if order_seed is not None:
        args += ["--item-order-seed", str(order_seed)]
    print("▶ running:", " ".join(args))
    subprocess.run(args, check=True)

def aggregate_to_md(results_json: Path, persona_json: Dict[str,float], md_out: Path):
    # import dinámico del agregador
    sys.path.insert(0, str(REPO_ROOT))
    from eval.mpi_aggregator import MPIResultsAggregator  # type: ignore
    agg = MPIResultsAggregator()
    agg.load_results(str(results_json))
    agg.aggregate_traits()
    # genera md + compara con persona
    md_out.parent.mkdir(parents=True, exist_ok=True)
    agg.generate_report(str(md_out), persona_json)
    return agg  # para reusar métricas

# --- Métricas adicionales ----------------------------------------------------
def extract_means(agg_obj) -> Dict[str,float]:
    means={}
    for code in CODES:
        m = agg_obj.aggregated["trait_summary"][code]["mean"]
        means[code] = float("nan") if (m!=m) else float(m)  # NaN check
    return means

def compute_leakage(means: Dict[str,float], baseline_means: Dict[str,float], target_code: Optional[str]) -> Optional[float]:
    if not target_code: return None
    deltas=[]
    for code in CODES:
        if code==target_code: continue
        a=means.get(code); b=baseline_means.get(code)
        if a is None or b is None or (a!=a) or (b!=b):  # NaN
            continue
        deltas.append(abs(a-b))
    return sum(deltas)/len(deltas) if deltas else None

def linear_fit(x: List[float], y: List[float]) -> Tuple[float,float]:
    # pendiente, R^2
    n=len(x)
    if n<2: return float("nan"), float("nan")
    sx=sum(x); sy=sum(y)
    sxx=sum(v*v for v in x); syy=sum(v*v for v in y)
    sxy=sum(a*b for a,b in zip(x,y))
    denom = n*sxx - sx*sx
    if denom==0: return float("nan"), float("nan")
    slope = (n*sxy - sx*sy)/denom
    # R^2
    mx=sx/n; my=sy/n
    ss_tot = sum((v-my)**2 for v in y)
    ss_res = sum((yi - (slope*(xi-mx)+my))**2 for xi,yi in zip(x,y))
    r2 = 1 - (ss_res/ss_tot) if ss_tot>0 else float("nan")
    return slope, r2

# --- Loop maestro ------------------------------------------------------------
def main():
    print(f"🚀 Iniciando experimentos MPI-AE completos")
    print(f"Persona Engine: {PERSONA_ENGINE}")
    print(f"Dialog Orchestrator: {DIALOG_URL}")
    print(f"CSV: {CSV_PATH}")
    
    # Validaciones rápidas
    assert RUNNER.exists(), f"No encuentro {RUNNER}"
    assert AGG_MOD.exists(), f"No encuentro {AGG_MOD}"
    assert CSV_PATH.exists(), f"No encuentro {CSV_PATH}"

    # prioriza generar baseline NEUTRAL para todos seed/orden
    ordered_conditions = ["NEUTRAL"] + [k for k in CONDITIONS.keys() if k!="NEUTRAL"]

    summary_path = RUNS_DIR / "summary.csv"
    write_header = not summary_path.exists()
    with summary_path.open("a", encoding="utf-8") as fh:
        if write_header:
            fh.write(",".join([
                "condition","user_id","seed","order_seed","target",
                "mean_O","mean_C","mean_E","mean_A","mean_N",
                "persona_O","persona_C","persona_E","persona_A","persona_N",
                "correlation","MAE","RMSE",
                "leakage_vs_NEUTRAL",
                "valid_rate","unk_count","extreme_bias","consistency_std",
                "avg_latency_ms","total_tokens","results_path","report_path"
            ])+"\n")

        # cache baseline por (seed,order)
        baselines: Dict[Tuple[int,Optional[int]], Dict[str,float]] = {}

        for cond in ordered_conditions:
            conf = CONDITIONS[cond]
            user_id = cond
            print(f"\n📋 Procesando condición: {cond}")
            
            # 1) set persona
            print(f"  ⚙️  Configurando persona {user_id}...")
            set_persona(user_id, conf)
            persona = get_persona(user_id)
            print(f"     ✅ Persona configurada: {persona}")

            # 2) por cada combinación seed/orden
            for seed in SEEDS:
                for order_seed in ORDER_SEEDS:
                    print(f"  🎯 Ejecutando seed={seed}, order={order_seed}...")
                    subdir = RUNS_DIR / cond
                    subdir.mkdir(parents=True, exist_ok=True)
                    tag = f"{cond}__seed-{seed}__order-{order_seed}"
                    res_path = subdir / f"{tag}.json"
                    md_path  = subdir / f"{tag}.md"
                    
                    # run MPI assessment
                    run_mpi(user_id, res_path, seed, order_seed)
                    
                    # aggregate+report
                    agg = aggregate_to_md(res_path, persona, md_path)
                    means = extract_means(agg)
                    print(f"     📊 Medias: {means}")

                    # persona vector
                    persona_vec = {
                        "O": float(persona["openness"]),
                        "C": float(persona["conscientiousness"]),
                        "E": float(persona["extraversion"]),
                        "A": float(persona["agreeableness"]),
                        "N": float(persona["neuroticism"]),
                    }
                    comp = agg.compare_with_persona(persona)
                    corr = comp["overall_metrics"]["correlation"]
                    mae  = comp["overall_metrics"]["mean_absolute_error"]
                    rmse = comp["overall_metrics"]["root_mean_square_error"]
                    print(f"     📈 Correlación: {corr:.3f}, MAE: {mae:.3f}")

                    # baseline y leakage
                    key = (seed, order_seed)
                    leakage = None
                    if cond=="NEUTRAL":
                        baselines[key] = means
                    else:
                        base = baselines.get(key)
                        if base:
                            target_code = conf.get("target")  # "E", "N", etc o None
                            leakage = compute_leakage(means, base, target_code)
                            if leakage is not None:
                                print(f"     🔍 Leakage: {leakage:.4f}")

                    # calidad/eficiencia
                    meta = agg.aggregated["metadata"]
                    choice_counts = agg.aggregated["choice_counts"]
                    quality = agg.aggregated["quality_metrics"]
                    valid_rate = meta["completion_rate"]
                    unk_count = choice_counts.get("UNK", 0)
                    extreme_bias = quality["extreme_response_bias"]
                    consistency_std = quality["avg_within_trait_consistency"]
                    
                    # metadata de eficiencia
                    metadata = agg.results_data.get("metadata", {})
                    avg_lat = metadata.get("avg_latency_ms", 0)
                    total_tok = metadata.get("total_tokens", 0)

                    # escribe una fila en summary.csv
                    row = [
                        cond, user_id, str(seed), str(order_seed), str(conf.get("target")),
                        f"{means['O']:.4f}", f"{means['C']:.4f}", f"{means['E']:.4f}", f"{means['A']:.4f}", f"{means['N']:.4f}",
                        f"{persona_vec['O']:.1f}", f"{persona_vec['C']:.1f}", f"{persona_vec['E']:.1f}", f"{persona_vec['A']:.1f}", f"{persona_vec['N']:.1f}",
                        f"{corr:.6f}" if corr==corr else "nan",
                        f"{mae:.6f}" if mae==mae else "nan",
                        f"{rmse:.6f}" if rmse==rmse else "nan",
                        f"{leakage:.6f}" if leakage is not None else "",
                        f"{valid_rate:.6f}",
                        str(unk_count),
                        f"{extreme_bias:.6f}" if extreme_bias==extreme_bias else "nan",
                        f"{consistency_std:.6f}" if consistency_std==consistency_std else "nan",
                        f"{avg_lat:.2f}", str(total_tok),
                        str(res_path), str(md_path)
                    ]
                    fh.write(",".join(row)+"\n")
                    fh.flush()

        print(f"\n🧮 Calculando sensibilidad E_GRAD...")
        # 3) Sensibilidad (E_GRAD) usando seed=111, order=None (ajusta aquí si quieres promediar)
        targets = {"E_20":2.0, "E_30":3.0, "E_40":4.0, "E_50":5.0}
        xs=[]; ys=[]
        for name,val in targets.items():
            tag = f"{name}__seed-111__order-None"
            path = RUNS_DIR / name / f"{tag}.json"
            # reutiliza agregador para tomar mean_E
            from eval.mpi_aggregator import MPIResultsAggregator  # type: ignore
            agg = MPIResultsAggregator(); agg.load_results(str(path)); agg.aggregate_traits()
            mean_E = agg.aggregated["trait_summary"]["E"]["mean"]
            xs.append(val); ys.append(mean_E)
            print(f"  📐 {name}: target={val:.1f} → measured={mean_E:.3f}")
            
        slope, r2 = linear_fit(xs, ys)
        sens = {
            "target_trait":"E", 
            "pairs": [{"target":x,"measured":y} for x,y in zip(xs,ys)], 
            "slope":slope, 
            "r2":r2
        }
        (RUNS_DIR / "sensitivity_E_grad.json").write_text(json.dumps(sens, indent=2))
        print(f"📈 Sensibilidad E_GRAD -> slope={slope:.3f}, R²={r2:.3f}")
        
        print(f"\n✅ Experimentos completos!")
        print(f"📁 Resumen: {summary_path}")
        print(f"📊 Sensibilidad: {RUNS_DIR}/sensitivity_E_grad.json")
        print(f"📋 Reportes individuales: runs/*/*.md")

if __name__=="__main__":
    main()
