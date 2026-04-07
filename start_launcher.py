#!/usr/bin/env python3
import json
import os
import subprocess
import sys


def _escape_applescript(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def ask(prompt, secret=False):
    """Ask via native macOS dialog. Falls back to terminal input if unavailable."""
    prompt_escaped = _escape_applescript(prompt)
    hidden = " with hidden answer" if secret else ""
    script = (
        f'display dialog "{prompt_escaped}" default answer ""'
        f'{hidden} buttons {{"Cancel", "OK"}} default button "OK" with title "Start Inference"'
    )

    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None

        output = (proc.stdout or "").strip()
        marker = "text returned:"
        idx = output.find(marker)
        if idx == -1:
            return None
        return output[idx + len(marker):].strip()
    except FileNotFoundError:
        try:
            return input(f"{prompt} ").strip()
        except EOFError:
            return None


def ask_mode():
    """Return 'manual', 'file', or None if cancelled."""
    script = (
        'display dialog "Choose how to provide inference values:" '
        'buttons {"Cancel", "Use Config File", "Enter Manually"} '
        'default button "Enter Manually" with title "Start Inference"'
    )
    try:
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        output = (proc.stdout or "").strip().lower()
        if "button returned:use config file" in output:
            return "file"
        if "button returned:enter manually" in output:
            return "manual"
        return None
    except FileNotFoundError:
        choice = input("Use config file? (y/N): ").strip().lower()
        return "file" if choice in {"y", "yes"} else "manual"


def choose_config_file():
    """Open native file picker and return selected path or None."""
    script = (
        'set chosenFile to choose file with prompt "Select config file"\n'
        'POSIX path of chosenFile'
    )
    try:
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        return (proc.stdout or "").strip() or None
    except FileNotFoundError:
        path = input("Config file path: ").strip()
        return path or None


def load_config_file(config_path):
    """Load api_key/model_name/dataset from JSON or KEY=VALUE file."""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    parsed = {}

    # Try JSON first.
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            parsed = {str(k).strip().lower(): str(v).strip() for k, v in data.items() if v is not None}
    except json.JSONDecodeError:
        pass

    # Fallback: parse KEY=VALUE lines (.env style)
    if not parsed:
        for line in content.splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip().lower()
            value = value.strip().strip('"').strip("'")
            parsed[key] = value

    return {
        "api_key": parsed.get("api_key") or parsed.get("openai_api_key") or parsed.get("groq_api_key") or "",
        "model_name": parsed.get("model_name") or "",
        "dataset": parsed.get("dataset") or parsed.get("dataset_name") or "",
    }


def main():
    repo_dir = os.path.dirname(os.path.realpath(__file__))

    mode = ask_mode()
    if mode is None:
        print("Cancelled.")
        return 1

    config_path = None
    if mode == "file":
        config_path = choose_config_file()
        if not config_path:
            print("Cancelled: no config file selected.")
            return 1

    config = {"api_key": "", "model_name": "", "dataset": ""}
    if config_path:
        candidate = os.path.expanduser(config_path)
        if not os.path.isabs(candidate):
            candidate = os.path.join(repo_dir, candidate)
        if not os.path.exists(candidate):
            print(f"Config file not found: {candidate}")
            return 1
        try:
            config = load_config_file(candidate)
        except Exception as exc:
            print(f"Failed to read config file: {exc}")
            return 1

    api_key = config["api_key"] or ask("Enter API key:", secret=True)
    if not api_key:
        print("Cancelled: API key was not provided.")
        return 1

    model_name = config["model_name"] or ask("Enter model name:")
    if not model_name:
        print("Cancelled: Model name was not provided.")
        return 1

    dataset = config["dataset"] or ask("Enter dataset:")
    if not dataset:
        print("Cancelled: Dataset was not provided.")
        return 1

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    env["MODEL_NAME"] = model_name
    env["DATASET_NAME"] = dataset

    venv_python = os.path.join(repo_dir, ".venv", "bin", "python")
    python_bin = venv_python if os.path.exists(venv_python) else sys.executable

    result = subprocess.run(
        [python_bin, "inference.py", "run"],
        cwd=repo_dir,
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
