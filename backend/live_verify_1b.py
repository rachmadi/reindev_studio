import os
import sys
import time
from pathlib import Path

# Pastikan UTF-8 dan unbuffered stdout aktif di Windows console
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.state import SquadState
from backend.graph import squad_graph

def main():
    print("=" * 70, flush=True)
    print("REINDEV STUDIO — LIVE SQUAD PIPELINE VERIFICATION (ITERASI 1b)", flush=True)
    print("Provider: Ollama Local (Resident VRAM 6GB: qwen2.5-coder:7b)", flush=True)
    print("=" * 70, flush=True)

    task_description = (
        "Buat modul Python kalkulator matematika dengan dua fungsi utama:\n"
        "1. is_prime(n: int) -> bool: Memeriksa apakah bilangan n adalah prima (kembalikan False jika n <= 1).\n"
        "2. fibonacci_sequence(count: int) -> list[int]: Menghasilkan list deret Fibonacci sebanyak count (lempar ValueError jika count < 0)."
    )

    initial_state: SquadState = {
        "task": task_description,
        "provider": "ollama",
        "model_name": "qwen2.5-coder:7b",
        "target_language": "python",
        "specifications": "",
        "architecture_plan": "",
        "code_files": {},
        "test_files": {},
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 3,
        "review_notes": "",
        "status": "init",
        "logs": []
    }

    print(f"\n[INTENT ARCHITECT TASK]:\n{task_description}\n", flush=True)
    print("Memulai eksekusi LangGraph Squad Pipeline secara streaming...", flush=True)
    
    start_total = time.time()
    final_state = {}
    current_state = initial_state.copy()

    for event in squad_graph.stream(initial_state):
        for node_name, node_output in event.items():
            elapsed = round(time.time() - start_total, 2)
            print(f"\n>>> [NODE SELESAI: {node_name.upper()}] (Waktu: {elapsed}s)", flush=True)
            if "logs" in node_output and node_output["logs"]:
                # Print log dengan aman
                log_text = str(node_output['logs'][-1])
                print(f"    Log: {log_text}", flush=True)
            current_state.update(node_output)
            final_state = current_state

    total_duration = round(time.time() - start_total, 2)

    print("\n" + "=" * 70, flush=True)
    print(f"PIPELINE SELESAI DALAM {total_duration} DETIK", flush=True)
    print("=" * 70, flush=True)

    print("\n1. SPESIFIKASI PRODUCT MANAGER:", flush=True)
    print("-" * 50, flush=True)
    print(final_state.get("specifications", "")[:300] + "\n... (dipotong)", flush=True)

    print("\n2. RENCANA SYSTEM ARCHITECT:", flush=True)
    print("-" * 50, flush=True)
    print(final_state.get("architecture_plan", "")[:300] + "\n... (dipotong)", flush=True)

    print("\n3. FILE KODE DEVELOPER:", flush=True)
    print("-" * 50, flush=True)
    for fname, code in final_state.get("code_files", {}).items():
        print(f"=== File: {fname} ({len(code)} karakter) ===", flush=True)

    print("\n4. FILE TEST QA TESTER:", flush=True)
    print("-" * 50, flush=True)
    for fname, code in final_state.get("test_files", {}).items():
        print(f"=== File: {fname} ({len(code)} karakter) ===", flush=True)

    print("\n5. HASIL SANDBOX TEST RUNNER:", flush=True)
    print("-" * 50, flush=True)
    results = final_state.get("test_results", {})
    print(f"Status Passed  : {results.get('passed')}", flush=True)
    print(f"Total Tests    : {results.get('total')}", flush=True)
    print(f"Passed Count   : {results.get('passed_count')}", flush=True)
    print(f"Failed Count   : {results.get('failed_count')}", flush=True)
    print(f"Exit Code      : {results.get('exit_code')}", flush=True)
    print(f"Pytest Output  :\n{results.get('output', '')}", flush=True)

    print("\n6. LAPORAN CODE REVIEWER:", flush=True)
    print("-" * 50, flush=True)
    print(final_state.get("review_notes", "")[:400] + "\n... (dipotong)", flush=True)

    print(f"\nFinal State Status: {final_state.get('status')}", flush=True)
    print(f"Iterasi Perbaikan : {final_state.get('iteration_count')}x", flush=True)

if __name__ == "__main__":
    main()
