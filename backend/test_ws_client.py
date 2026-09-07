import asyncio
import json
import websockets
import sys

# Konfigurasi UTF-8 dan unbuffered stdout
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

async def main():
    uri = "ws://127.0.0.1:8000/ws/squad"
    print(f"Menghubungkan ke WebSocket Hub di {uri}...", flush=True)
    
    try:
        async with websockets.connect(uri) as ws:
            # 1. Terima event sambutan koneksi
            conn_msg = await ws.recv()
            print("<<< Terkoneksi:", conn_msg, flush=True)
            
            # 2. Kirim ping untuk verifikasi latency
            await ws.send(json.dumps({"action": "ping"}))
            pong_msg = await ws.recv()
            print("<<< Respons Ping:", pong_msg, flush=True)
            
            # 3. Kirim perintah squad
            task_msg = {
                "action": "start_squad",
                "task": "Modul kalkulator konversi suhu fungsi c_to_f dan f_to_c dengan validasi batas nol mutlak (-273.15 C).",
                "provider": "ollama",
                "target_language": "python"
            }
            print(f"\n>>> Mengirim Perintah Squad:\n{task_msg['task']}\n", flush=True)
            await ws.send(json.dumps(task_msg))
            
            # 4. Terima streaming event secara real-time
            while True:
                raw_event = await ws.recv()
                event = json.loads(raw_event)
                event_name = event.get("event")
                timestamp = event.get("timestamp", "")
                
                if event_name == "session_start":
                    print(f"[{timestamp}] [SESSION START]: Task={event.get('task')}", flush=True)
                elif event_name == "agent_state":
                    print(f"[{timestamp}] [AGENT STATE] Node: {event.get('node')} | Status: {event.get('status')} | Log: {event.get('log')}", flush=True)
                elif event_name == "agent_thought":
                    agent = event.get("agent")
                    thought = event.get("thought", "")[:120].replace('\n', ' ')
                    print(f"[{timestamp}] [THOUGHT - {agent.upper()}]: {thought}...", flush=True)
                elif event_name == "code_update":
                    files = list(event.get("files", {}).keys())
                    print(f"[{timestamp}] [CODE UPDATE - {event.get('agent')}]: {files}", flush=True)
                elif event_name == "test_log":
                    results = event.get("results", {})
                    print(f"[{timestamp}] [TEST LOG]: Passed={results.get('passed')} ({results.get('passed_count')} passed, {results.get('failed_count')} failed)", flush=True)
                elif event_name == "review_report":
                    print(f"[{timestamp}] [REVIEW REPORT]: Status={event.get('status')}", flush=True)
                elif event_name == "complete":
                    print("\n" + "=" * 60, flush=True)
                    print(f"[{timestamp}] [SQUAD MISSION COMPLETED]", flush=True)
                    print(f"Project Name   : {event.get('project_name')}", flush=True)
                    print(f"Project Dir    : {event.get('project_dir')}", flush=True)
                    print(f"Duration       : {event.get('duration_sec')}s", flush=True)
                    print(f"Generated Files: {list(event.get('files', {}).keys())}", flush=True)
                    print("=" * 60, flush=True)
                    break
                elif event_name == "error":
                    print(f"[ERROR]: {event.get('message')}", flush=True)
                    break
                    
    except ConnectionRefusedError:
        print("ERROR: Server FastAPI belum berjalan.", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR WebSocket: {str(e)}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
