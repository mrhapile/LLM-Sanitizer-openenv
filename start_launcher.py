#!/usr/bin/env python3
import os
import subprocess
import sys


def ask(prompt):
    try:
        return input(f"{prompt} ").strip()
    except EOFError:
        return ""


def main():
    repo_dir = os.path.dirname(os.path.realpath(__file__))
    base_url = ask("OpenEnv base URL [http://localhost:7860]:") or "http://localhost:7860"

    env = os.environ.copy()
    venv_python = os.path.join(repo_dir, ".venv", "bin", "python")
    python_bin = venv_python if os.path.exists(venv_python) else sys.executable

    result = subprocess.run([python_bin, "inference.py", base_url], cwd=repo_dir, env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
