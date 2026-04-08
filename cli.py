#!/usr/bin/env python3
"""
Release Desk CLI: One-command interface for running the entire environment.

Usage:
  python cli.py run          # Start API, run inference, open report
  python cli.py doctor       # Pre-flight environment checks
  python cli.py serve        # Start the FastAPI server only
  python cli.py demo         # Run inference + open report (requires API running)
"""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

from api_key_utils import get_api_key_env


ROOT = Path(__file__).resolve().parent


def _resolve_python_bin() -> Path:
    for env_name in (".venv", "venv"):
        candidate = ROOT / env_name / "bin" / "python"
        if candidate.exists():
            return candidate
    return Path(sys.executable)


PYTHON = _resolve_python_bin()
REPORT_FILE = ROOT / "release_desk_demo.html"
API_URL = "http://127.0.0.1:7860"
API_HEALTH_URL = f"{API_URL}/healthz"


def run_cmd(cmd, env=None, check=True):
    """Run command and return exit code."""
    print(f"$ {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd, cwd=ROOT, env=env or os.environ.copy())
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}")
    return result.returncode


def doctor():
    """Pre-flight checks: Python, venv, dependencies, config."""
    print("\n🔍 Release Desk Pre-flight Doctor\n")
    
    checks = []
    
    # Python version
    v = sys.version_info
    py_ok = v >= (3, 10)
    checks.append(("Python 3.10+", py_ok, f"Using {v.major}.{v.minor}.{v.micro}"))
    
    # venv active
    venv_ok = PYTHON.exists() and hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    checks.append(("venv active", venv_ok, sys.prefix))
    
    # Import core modules
    core_imports = ["fastapi", "pydantic", "spacy", "pandas", "requests", "openai"]
    imports_ok = True
    missing = []
    for mod in core_imports:
        try:
            __import__(mod)
        except ImportError:
            imports_ok = False
            missing.append(mod)
    checks.append(("Dependencies installed", imports_ok, f"Missing: {', '.join(missing)}" if missing else "All OK"))
    
    # spaCy model
    spacy_model_ok = False
    try:
        import spacy
        spacy.load("en_core_web_sm")
        spacy_model_ok = True
    except:
        pass
    checks.append(("spaCy model en_core_web_sm", spacy_model_ok, "Not installed" if not spacy_model_ok else "OK"))
    
    # .env config
    env_file = ROOT / ".env"
    env_ok = env_file.exists()
    api_key_ok = False
    api_key_name = None
    if env_ok:
        api_key_env = get_api_key_env()
        api_key_ok = api_key_env is not None
        api_key_name = api_key_env[0] if api_key_env else None
    checks.append((".env exists", env_ok, "Not found" if not env_ok else "OK"))
    if env_ok:
        checks.append(("API key set", api_key_ok, api_key_name or "Not found"))
    
    # Port 7860 availability
    import socket
    port_ok = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", 7860))
        port_ok = result != 0
        s.close()
    except:
        pass
    checks.append(("Port 7860 available", port_ok, "In use" if not port_ok else "Available"))
    
    # Print results
    for name, ok, detail in checks:
        symbol = "✅" if ok else "❌"
        print(f"{symbol} {name.ljust(30)} {detail}")
    
    print()
    all_ok = all(ok for _, ok, _ in checks)
    if all_ok:
        print("✨ All checks passed! Ready to run.\n")
        return 0
    else:
        print("⚠️  Some checks failed. Fix above issues before running.\n")
        return 1


def wait_for_health(timeout: float = 30.0) -> bool:
    """Wait for API to become healthy."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(API_HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def serve():
    """Start the FastAPI server."""
    print(f"\n🚀 Starting Release Desk API on {API_URL}\n")
    cmd = [str(PYTHON), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "7860"]
    return run_cmd(cmd, check=False)


def demo():
    """Run inference + demo. Requires API to be running."""
    print(f"\n📊 Running inference and generating demo report...\n")
    
    env = os.environ.copy()
    env["OPENENV_BASE_URL"] = API_URL
    
    # Run inference
    cmd = [str(PYTHON), "inference.py", API_URL]
    run_cmd(cmd, env=env)
    
    # Run demo
    cmd = [str(PYTHON), "demo.py"]
    run_cmd(cmd, env=env)
    
    # Open report
    if REPORT_FILE.exists():
        print(f"\n📂 Opening report: {REPORT_FILE}\n")
        webbrowser.open(f"file://{REPORT_FILE}")
    
    return 0


def run_all():
    """Full orchestration: start API (bg), run demo, cleanup."""
    print("\n🎯 Release Desk: Full Run\n")
    
    # Pre-flight
    if doctor() != 0:
        print("Cannot proceed. Fix issues above.\n")
        return 1
    
    # Start API in background
    print(f"\n🔧 Starting API in background...\n")
    server_cmd = [str(PYTHON), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "7860"]
    server = subprocess.Popen(server_cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    try:
        # Wait for health
        print("⏳ Waiting for API to become healthy...")
        if not wait_for_health(timeout=30):
            print("❌ API failed to start. Check logs.\n")
            return 1
        print("✅ API is healthy\n")
        
        # Run demo
        env = os.environ.copy()
        env["OPENENV_BASE_URL"] = API_URL
        
        print("📊 Running inference and generating report...\n")
        cmd = [str(PYTHON), "inference.py", API_URL]
        run_cmd(cmd, env=env)
        
        cmd = [str(PYTHON), "demo.py"]
        run_cmd(cmd, env=env)
        
        # Open report
        if REPORT_FILE.exists():
            print(f"\n✨ Report ready: {REPORT_FILE}\n")
            print("📂 Opening in browser...\n")
            webbrowser.open(f"file://{REPORT_FILE}")
        
        return 0
    
    finally:
        print("\n🧹 Cleaning up...\n")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        print("✅ Done.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Release Desk CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py run        # Full automation
  python cli.py doctor     # Pre-flight checks
  python cli.py serve      # Start API only
  python cli.py demo       # Run evaluation + report (API must be running)
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "doctor", "serve", "demo"],
        help="Command to run (default: run)"
    )
    
    args = parser.parse_args()
    
    if args.command == "doctor":
        return doctor()
    elif args.command == "serve":
        return serve()
    elif args.command == "demo":
        return demo()
    else:  # run
        return run_all()


if __name__ == "__main__":
    sys.exit(main())
