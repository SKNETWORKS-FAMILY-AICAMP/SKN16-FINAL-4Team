#!/usr/bin/env bash
# Create a Python 3.11 virtual environment in .venv and install requirements
set -euo pipefail

PYTHON=${PYTHON:-python3.11}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Error: $PYTHON not found. Install Python 3.11 or set PYTHON env to a python3.11 binary." >&2
  exit 2
fi

echo "Creating venv with $PYTHON"
$PYTHON -m venv .venv

# Activate and upgrade pip
source .venv/bin/activate
python -m pip install --upgrade pip

# Install requirements if present
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

echo "Virtualenv created at .venv using $PYTHON"
echo "Activate with: source .venv/bin/activate"
