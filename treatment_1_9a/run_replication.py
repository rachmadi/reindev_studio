# -*- coding: utf-8 -*-
"""
Replication Runner for Treatment #1.9A — Architect Semantic Mapping
Runs Replication 2 and Replication 3 (A/B/C) to verify stability and stochasticity.
"""

import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(r"D:\Pekerjaan\Antigravity\reindev_studio")
sys.path.insert(0, str(PROJECT_ROOT))

from treatment_1_9a.harness import (
    load_cached_context,
    build_base_prompt,
    invoke_ollama_chat,
    evaluate_condition_run,
    ARCHITECT_SYSTEM_PROMPT,
    OUTPUT_DIR,
    MODEL_NAME,
    NUM_CTX,
    NUM_PREDICT,
    TEMPERATURE
)
from backend.blueprint_schema import parse_blueprint_json

def check_scaffold_purity(raw_output: str) -> str:
    bp, _ = parse_blueprint_json(raw_output)
    if not bp or not hasattr(bp, "files") or not bp.files:
        return "UNKNOWN"
    
    has_pass_stubs = False
    has_full_logic = False
    
    for fmod in bp.files.values():
        sc = getattr(fmod, "code_scaffold", "") or (fmod.get("code_scaffold", "") if isinstance(fmod, dict) else str(fmod))
        if "pass" in sc:
            has_pass_stubs = True
        if any(term in sc for term in ["products.append", "products[", "del products", "products = ["]):
            has_full_logic = True
            
    if has_full_logic and not has_pass_stubs:
        return "OVER_GENERATED_LOGIC"
    elif has_full_logic and has_pass_stubs:
        return "MIXED_LOGIC_AND_STUBS"
    elif has_pass_stubs and not has_full_logic:
        return "MINIMAL_STUBS_PASS"
    return "STUB_OR_DECLARATION"

def run_replications():
    print("=" * 80)
    print("REPLICATION #1.9A: ARCHITECT SEMANTIC MAPPING (RUNS 2 & 3)")
    print(f"Model: {MODEL_NAME} | Temp: {TEMPERATURE} | num_ctx: {NUM_CTX} | num_predict: {NUM_PREDICT}")
    print("=" * 80)

    context = load_cached_context()
    
    # Load R1 results
    r1_summary_file = OUTPUT_DIR / "treatment_1_9a_summary.json"
    with open(r1_summary_file, 'r', encoding='utf-8') as f:
        r1_data = json.load(f)
        
    all_runs = {"R1": {}}
    for cond in ["A", "B", "C"]:
        r1_raw_file = OUTPUT_DIR / f"raw_output_condition_{cond}.txt"
        with open(r1_raw_file, 'r', encoding='utf-8') as f:
            raw_t = f.read()
        purity = check_scaffold_purity(raw_t)
        all_runs["R1"][cond] = dict(r1_data[cond])
        all_runs["R1"][cond]["scaffold_purity"] = purity

    # Run R2 and R3
    for run_num in [2, 3]:
        run_key = f"R{run_num}"
        all_runs[run_key] = {}
        print(f"\n=================== STARTING REPLICATION {run_num} ===================")
        
        for cond in ["A", "B", "C"]:
            print(f"\n>>> [{run_key}] Condition {cond}...")
            user_prompt = build_base_prompt(context, condition_mode=cond)
            
            # Save prompt
            prompt_file = OUTPUT_DIR / f"prompt_condition_{cond}_{run_key.lower()}.txt"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(f"=== SYSTEM PROMPT ===\n{ARCHITECT_SYSTEM_PROMPT}\n\n=== USER PROMPT ===\n{user_prompt}")

            raw_out, latency, p_tokens, e_tokens = invoke_ollama_chat(
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )

            # Save raw output
            raw_out_file = OUTPUT_DIR / f"raw_output_condition_{cond}_{run_key.lower()}.txt"
            with open(raw_out_file, 'w', encoding='utf-8') as f:
                f.write(raw_out)

            metrics = evaluate_condition_run(
                condition_name=f"{cond}_{run_key}",
                raw_output=raw_out,
                latency=latency,
                prompt_tokens=p_tokens,
                eval_tokens=e_tokens
            )
            purity = check_scaffold_purity(raw_out)
            metrics["scaffold_purity"] = purity
            
            all_runs[run_key][cond] = metrics

            print(f"  Verdict: {metrics['verdict']} | Seal: {metrics['seal_success']} | Latency: {metrics['latency_sec']}s | Chars: {metrics['raw_output_chars']}")
            print(f"  Structural Validity: {metrics['structural_blueprint_validity']}")
            print(f"  Coverage: {metrics['obligation_coverage']['covered_count']}/{metrics['obligation_coverage']['total_obligations']}")
            print(f"  Identity Fidelity: {metrics['identity_fidelity']} (Paths: {metrics['observed_paths']})")
            print(f"  Scaffold Purity: {purity}")
            print(f"  Declared Routes Count: {metrics['semantic_mapping_fidelity']['declared_routes_count']}")
            if metrics['errors']:
                print(f"  Errors: {metrics['errors'][:1]}")

    # Save complete 3x3 summary
    summary_3x3_file = OUTPUT_DIR / "treatment_1_9a_3x3_summary.json"
    with open(summary_3x3_file, 'w', encoding='utf-8') as f:
        json.dump(all_runs, f, indent=2)

    print("\n" + "=" * 80)
    print("3x3 REPLICATION COMPLETE")
    print("=" * 80)
    
    print("\n| Run | Condition | Seal | Coverage | Identity | Scaffold | Latency | Verdict |")
    print("|-----|-----------|------|----------|----------|----------|---------|---------|")
    for r_k in ["R1", "R2", "R3"]:
        for c_k in ["A", "B", "C"]:
            m = all_runs[r_k][c_k]
            cov = f"{m['obligation_coverage']['covered_count']}/{m['obligation_coverage']['total_obligations']}"
            ident = "YES" if m['identity_fidelity'] else "DRIFT"
            seal = "FROZEN" if m['seal_success'] else "REJECTED"
            scaf = m['scaffold_purity']
            lat = f"{m['latency_sec']}s"
            v = m['verdict']
            print(f"| {r_k}  | {c_k}         | {seal:8} | {cov:8} | {ident:8} | {scaf:16} | {lat:7} | {v:7} |")

if __name__ == "__main__":
    run_replications()
