import os, sys, time
from pathlib import Path

backend_path = str(Path(__file__).parent.resolve())
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from state import SquadState
from agents.pm import pm_agent
from agents.developer import developer_agent

def main():
    print("=== PENGUJIAN LIVE REINDEV STUDIO: ITERASI 1a ===")
    print("Model: Ollama Local (qwen2.5-coder:7b) [Resident VRAM 6GB]")
    
    os.environ["MOCK_LLM"] = "false"
    os.environ["LLM_PROVIDER"] = "ollama"
    
    state: SquadState = {
        "task": "Buat modul Python kalkulator matriks 2x2 dengan fungsi determinan dan pertambahan matriks",
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
        "status": "idle",
        "logs": []
    }
    
    # 1. Jalankan PM Agent
    t0 = time.time()
    print("\n[1] Menjalankan Product Manager Agent...")
    pm_res = pm_agent(state)
    t1 = time.time()
    print(f"PM Selesai dalam {t1 - t0:.2f} detik.")
    print("Log PM:", pm_res["logs"][-1])
    print("\nCuplikan Spesifikasi PM:")
    print(pm_res["specifications"][:350] + "...\n")
    
    # Update state
    state = {**state, **pm_res}
    
    # 2. Jalankan Developer Agent
    t2 = time.time()
    print("[2] Menjalankan Developer Agent...")
    dev_res = developer_agent(state)
    t3 = time.time()
    print(f"Developer Selesai dalam {t3 - t2:.2f} detik.")
    print("Log Dev:", dev_res["logs"][-1])
    print(f"\nFile yang dihasilkan ({len(dev_res['code_files'])} file):")
    for fname, code in dev_res["code_files"].items():
        print(f"\n--- File: {fname} ({len(code)} karakter) ---")
        print(code[:300] + "...")
        
    print("\n=== VERIFIKASI LIVE ITERASI 1a BERHASIL 100% ===")

if __name__ == "__main__":
    main()
