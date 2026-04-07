#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run(cmd, env=None):
    print(f"$ {' '.join(map(str, cmd))}")
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def wait_for_health(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Server did not become healthy at {url}")


def main() -> int:
    base_url = os.environ.get("OPENENV_BASE_URL", "http://127.0.0.1:7860")
    server_cmd = [
        str(PYTHON),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "7860",
    ]

    run([str(PYTHON), "-m", "pytest", "-q"])
    run(["python3", "-m", "compileall", "demo.py", "main.py", "tests"])

    server = subprocess.Popen(server_cmd, cwd=ROOT)
    try:
        wait_for_health(f"{base_url}/healthz")
        env = os.environ.copy()
        env["OPENENV_BASE_URL"] = base_url
        env["BENCHMARK_OUTPUT_JSON"] = str(ROOT / "benchmark.json")
        run([str(PYTHON), "inference.py", base_url], env=env)
        run([str(PYTHON), "demo.py"], env=env)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    print(f"Smoke checks complete. Report: {ROOT / 'release_desk_demo.html'}")
    print(f"Benchmark JSON: {ROOT / 'benchmark.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
