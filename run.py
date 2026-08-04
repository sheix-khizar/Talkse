import subprocess
import sys
import os
import time

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "Talkse-backend", "Talkse-backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 50)
    print("🚀 Starting Talkse Voice Platform")
    print("=" * 50)

    # 1. Start Backend
    print("[*] Starting FastAPI Backend...")
    # Using python -m uvicorn ensures it picks up the active virtual environment
    backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--workers", "1"]
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir
    )

    # Give the backend a couple of seconds to spin up
    time.sleep(2)

    # 2. Start Frontend
    print("[*] Starting React/Vite Frontend...")
    # shell=True is useful on Windows to resolve npm.cmd automatically
    frontend_process = subprocess.Popen(
        "npm run dev",
        cwd=frontend_dir,
        shell=True
    )

    print("\n[+] Both servers are launching!")
    print("    Backend: http://127.0.0.1:8000")
    print("    Frontend: http://localhost:5173")
    print("[!] Press Ctrl+C in this terminal to stop both servers.\n")

    try:
        # Keep the script running while the child processes are alive
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n[*] Caught KeyboardInterrupt. Shutting down servers gracefully...")
        
        # Terminate both processes
        backend_process.terminate()
        # Note: shell=True on Windows spawns a cmd.exe wrapper. Terminating the process object 
        # may only kill the cmd wrapper. But this is usually sufficient to signal intent,
        # or the user can just kill the terminal.
        frontend_process.terminate()
        
        backend_process.wait()
        frontend_process.wait()
        print("[+] All servers stopped.")

if __name__ == "__main__":
    main()
