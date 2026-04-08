#!/bin/bash
# Quick-start script: sets up environment and runs Release Desk

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo ""
echo "Release Desk Quick-Start"
echo "============================"
echo ""

# Prefer .venv (used by local dev); fall back to venv for compatibility.
ENV_DIR=".venv"
if [ ! -d "$ENV_DIR" ] && [ -d "venv" ]; then
    ENV_DIR="venv"
fi

# Create env if neither exists.
if [ ! -d "$ENV_DIR" ]; then
    echo "Creating virtual environment at .venv..."
    python3 -m venv .venv
    ENV_DIR=".venv"
    echo "venv created"
    echo ""
fi

# Activate venv
echo "Activating venv..."
source "$ENV_DIR/bin/activate"
echo "venv activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "Dependencies installed"
echo ""

# Install project metadata and validation dependency set.
echo "Installing project package..."
pip install -q -e .
echo "Project package installed"
echo ""

# Run CLI
echo "Starting Release Desk..."
echo ""
python cli.py run
