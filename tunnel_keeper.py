"""
Tunnel Keeper daemon for Agent AM
Ensures localtunnel stays permanently connected with automatic recovery.
"""
import subprocess
import time
import sys

def run_tunnel():
    cmd = [r"C:\Program Files\nodejs\npx.cmd", "--yes", "localtunnel", "--port", "8000", "--subdomain", "thebayaan-agent"]
    print(f"Starting tunnel: {' '.join(cmd)}")
    sys.stdout.flush()
    while True:
        try:
            proc = subprocess.Popen(cmd)
            proc.wait()
        except Exception as e:
            print(f"Tunnel process exception: {e}")
            sys.stdout.flush()
        print("Tunnel exited. Reconnecting in 3 seconds...")
        sys.stdout.flush()
        time.sleep(3)

if __name__ == "__main__":
    run_tunnel()
