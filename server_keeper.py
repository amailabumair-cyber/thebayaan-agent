"""
Self-healing Persistent Server Daemon for Agent AM
Automatically restarts main.py if it ever stops, ensuring 24/7 uptime.
"""
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = BASE_DIR / "venv" / "Scripts" / "python.exe"

def run_server():
    print(f"Starting resilient Agent AM Server via {PYTHON_EXE}...")
    sys.stdout.flush()
    while True:
        try:
            env = dict(**subprocess.os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            
            proc = subprocess.Popen(
                [str(PYTHON_EXE), "main.py"],
                cwd=str(BASE_DIR),
                env=env
            )
            proc.wait()
            ret = proc.returncode
            print(f"Agent AM server exited with code {ret}. Auto-restarting in 2 seconds...")
            sys.stdout.flush()
        except Exception as e:
            print(f"Server keeper exception: {e}. Retrying in 2 seconds...")
            sys.stdout.flush()
        time.sleep(2)

if __name__ == "__main__":
    run_server()
