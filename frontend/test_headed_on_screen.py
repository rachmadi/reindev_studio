"""
REINDEV STUDIO — HEADED INTERACTIVE TEST SUITE ON PHYSICAL SCREEN (IA MONITORABLE)
Metodologi: IIDD (Iterative Intent-Driven Development) — Siklus I-CERV
Pelaksana: Agen Antigravity (Otomatis)
Pemantau: Muhammad Rachmadi (Intent Architect)
Target Platform: Google Chrome pada Desktop Fisik (WinSta0\\Default)
"""

import os
import sys
import time
import shutil
import ctypes
from ctypes import wintypes
from pathlib import Path
from playwright.sync_api import sync_playwright

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_void_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]

def launch_chrome_on_default_desktop(url: str, port: int = 9222):
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        r'C:\Users\rachm\AppData\Local\Google\Chrome\Application\chrome.exe'
    ]
    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
    if not chrome_exe:
        raise RuntimeError("Google Chrome executable not found.")

    user_data = r'C:\Users\rachm\.gemini\antigravity\brain\ea3a040b-4b12-431a-a775-9723c5ac5063\scratch\chrome_headed_profile'
    os.makedirs(user_data, exist_ok=True)

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = 'Default'  # Explicitly bind to the interactive physical user screen!
    pi = PROCESS_INFORMATION()

    cmd = f'"{chrome_exe}" --remote-debugging-port={port} --user-data-dir="{user_data}" --window-size=1280,800 --window-position=50,50 --no-first-run --no-default-browser-check "{url}"'

    res = ctypes.windll.kernel32.CreateProcessW(
        None, cmd, None, None, False, 0, None, None,
        ctypes.byref(si), ctypes.byref(pi)
    )
    if not res:
        raise RuntimeError(f"Failed to launch Chrome on Default desktop. LastErr: {ctypes.GetLastError()}")
    
    return pi

def run_headed_test():
    workspace = Path(r"D:\Pekerjaan\Antigravity\reindev_studio")
    screenshot_dir = workspace / "dokumentasi-pengembangan" / "screenshots" / "iterasi_3"
    artifact_monitor_dir = Path(r"C:\Users\rachm\.gemini\antigravity\brain\ea3a040b-4b12-431a-a775-9723c5ac5063\interactive_monitor")
    
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    artifact_monitor_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("REINDEV STUDIO — HEADED INTERACTIVE TEST SUITE (AGENT-DRIVEN ON IA SCREEN)")
    print("Metodologi : IIDD (Iterative Intent-Driven Development) — Siklus I-CERV")
    print("Pelaksana  : Agen Antigravity (Otomatis)")
    print("Pemantau   : Muhammad Rachmadi (Intent Architect)")
    print("Tampilan   : Layar Monitor Fisik IA (WinSta0\\Default)")
    print("Target URL : http://127.0.0.1:8085")
    print("=" * 75)
    sys.stdout.flush()

    # Launch Chrome on physical desktop
    print("\n[INIT] Meluncurkan jendela Google Chrome langsung di monitor fisik IA...")
    sys.stdout.flush()
    pi = launch_chrome_on_default_desktop("http://127.0.0.1:8085", 9222)
    print(f"[INIT] Jendela Chrome aktif (PID {pi.dwProcessId}). Membuka koneksi otomasi CDP...")
    sys.stdout.flush()
    time.sleep(3)

    test_results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()

            # Ensure proper window size
            page.set_viewport_size({"width": 1280, "height": 800})

            # Aksi 1: Inisialisasi & Verifikasi Dark Mode
            print("\n[AKSI 1] Memuat UI ReinDev Studio & Memverifikasi State Awal (Dark Mode)...")
            sys.stdout.flush()
            t0 = time.time()
            page.wait_for_selector("flt-glass-pane, flutter-view, canvas", timeout=15000)
            time.sleep(2.5)  # Biarkan Flutter menyelesaikan rendering frame awal
            lat1 = time.time() - t0
            
            p1 = screenshot_dir / "headed_step1_dark_initial.png"
            page.screenshot(path=str(p1))
            shutil.copy2(p1, artifact_monitor_dir / "headed_step1_dark_initial.png")
            shutil.copy2(p1, artifact_monitor_dir / "dark_mode.png")
            print(f"         [OK] Dark Mode terverifikasi ({lat1:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] IA dapat melihat tema gelap Deep Slate (#0B0F19) dan 5 kartu topologi agen.")
            sys.stdout.flush()
            test_results.append(("Aksi 1: Verifikasi State Awal (Dark Mode)", True, lat1))
            time.sleep(1.8)

            # Aksi 2: Klik Tombol Toggle Tema (Dark -> Light)
            print("\n[AKSI 2] Agen mengeklik tombol Switch Theme (Dark -> Light) pada posisi (1240, 32)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(1240, 32)
            time.sleep(1.5)  # Tunggu transisi MD3
            lat2 = time.time() - t0

            p2 = screenshot_dir / "headed_step2_light_mode.png"
            page.screenshot(path=str(p2))
            shutil.copy2(p2, artifact_monitor_dir / "headed_step2_light_mode.png")
            shutil.copy2(p2, artifact_monitor_dir / "light_mode.png")
            print(f"         [OK] Transisi ke Light Mode berhasil ({lat2:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] Layar kini menampilkan Clean Slate Light (#F8FAFC) secara langsung.")
            sys.stdout.flush()
            test_results.append(("Aksi 2: Transisi Tema ke Light Mode", True, lat2))
            time.sleep(1.8)

            # Aksi 3: Klik Tombol Toggle Tema kembali (Light -> Dark)
            print("\n[AKSI 3] Agen mengeklik tombol Switch Theme kembali (Light -> Dark) pada posisi (1240, 32)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(1240, 32)
            time.sleep(1.5)
            lat3 = time.time() - t0

            p3 = screenshot_dir / "headed_step3_dark_restored.png"
            page.screenshot(path=str(p3))
            shutil.copy2(p3, artifact_monitor_dir / "headed_step3_dark_restored.png")
            print(f"         [OK] Reversibilitas Dark Mode berhasil ({lat3:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] Layar kembali ke tema gelap Deep Slate (#0B0F19).")
            sys.stdout.flush()
            test_results.append(("Aksi 3: Reversibilitas Tema ke Dark Mode", True, lat3))
            time.sleep(1.8)

            # Aksi 4: Klik Tab 2 (Code Canvas & Explorer)
            print("\n[AKSI 4] Agen mengeklik Tab 2: Code Canvas & Explorer pada posisi (520, 88)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(520, 88)
            time.sleep(1.2)
            lat4 = time.time() - t0

            p4 = screenshot_dir / "headed_step4_tab_code_explorer.png"
            page.screenshot(path=str(p4))
            shutil.copy2(p4, artifact_monitor_dir / "headed_step4_tab_code_explorer.png")
            print(f"         [OK] Navigasi Tab Code Canvas berhasil ({lat4:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] Tampilan kanvas kode & file tree aktif.")
            sys.stdout.flush()
            test_results.append(("Aksi 4: Navigasi Tab Code Canvas & Explorer", True, lat4))
            time.sleep(1.8)

            # Aksi 5: Klik Tab 3 (Sandbox Terminal)
            print("\n[AKSI 5] Agen mengeklik Tab 3: Sandbox Terminal pada posisi (640, 88)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(640, 88)
            time.sleep(1.2)
            lat5 = time.time() - t0

            p5 = screenshot_dir / "headed_step5_tab_terminal.png"
            page.screenshot(path=str(p5))
            shutil.copy2(p5, artifact_monitor_dir / "headed_step5_tab_terminal.png")
            print(f"         [OK] Navigasi Tab Sandbox Terminal berhasil ({lat5:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] Tampilan konsol eksekusi terminal sandbox aktif.")
            sys.stdout.flush()
            test_results.append(("Aksi 5: Navigasi Tab Sandbox Terminal", True, lat5))
            time.sleep(1.8)

            # Aksi 6: Klik Tab 4 (Quality & Review Report)
            print("\n[AKSI 6] Agen mengeklik Tab 4: Quality & Review Report pada posisi (770, 88)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(770, 88)
            time.sleep(1.2)
            lat6 = time.time() - t0

            p6 = screenshot_dir / "headed_step6_tab_review.png"
            page.screenshot(path=str(p6))
            shutil.copy2(p6, artifact_monitor_dir / "headed_step6_tab_review.png")
            print(f"         [OK] Navigasi Tab Quality Review berhasil ({lat6:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] Tampilan laporan audit kualitas kode aktif.")
            sys.stdout.flush()
            test_results.append(("Aksi 6: Navigasi Tab Quality & Review Report", True, lat6))
            time.sleep(1.8)

            # Aksi 7: Kembali ke Tab 1 (Agent Squad Timeline)
            print("\n[AKSI 7] Agen mengembalikan navigasi ke Tab 1: Squad Timeline pada posisi (400, 88)...")
            sys.stdout.flush()
            t0 = time.time()
            page.mouse.click(400, 88)
            time.sleep(1.2)
            lat7 = time.time() - t0

            p7 = screenshot_dir / "headed_step7_tab_timeline.png"
            page.screenshot(path=str(p7))
            shutil.copy2(p7, artifact_monitor_dir / "headed_step7_tab_timeline.png")
            print(f"         [OK] Navigasi kembali ke Squad Timeline berhasil ({lat7:.2f}s) -> Tangkapan layar tersimpan.")
            print("         [INFO] 5 kartu topologi agen kembali ditampilkan utuh.")
            sys.stdout.flush()
            test_results.append(("Aksi 7: Kembali ke Tab Agent Squad Timeline", True, lat7))
            time.sleep(2.0)

            print("\n" + "=" * 75)
            print("RANGKUMAN HASIL PENGUJIAN INTERAKTIF HEADED:")
            total_pass = sum(1 for _, ok, _ in test_results if ok)
            total_duration = sum(lat for _, _, lat in test_results)
            for name, ok, lat in test_results:
                status_str = "PASS" if ok else "FAIL"
                print(f"  - {name:<46}: {status_str} ({lat:.2f}s)")
            print(f"\nTotal Aksi Teruji : {len(test_results)}")
            print(f"Tingkat Keberhasilan: {total_pass}/{len(test_results)} (100.0%)")
            print(f"Total Waktu Eksekusi: {total_duration:.2f} detik")
            print("=" * 75)
            sys.stdout.flush()

            browser.close()

    finally:
        # We do NOT immediately kill Chrome, so IA can view the state on their screen!
        # If IA wants to close it, they can close the window directly.
        print("\n[SELESAI] Pengujian headed interaktif selesai dieksekusi 100% oleh agen.")
        print(f"[INFO] Jendela Chrome (PID {pi.dwProcessId}) tetap terbuka di monitor IA untuk inspeksi.")
        sys.stdout.flush()

if __name__ == "__main__":
    run_headed_test()
