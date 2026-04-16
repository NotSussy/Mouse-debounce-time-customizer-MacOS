#!/usr/bin/env bash
# Sets up a Python virtual environment and installs dependencies.
set -euo pipefail

echo "=== Mouse Debounce Time Customizer — Setup ==="
echo ""

# Require Python 3.8+
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install Python 3.8+ from https://python.org" >&2
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(sys.version_info >= (3, 8))")
if [[ "$PY_VER" != "True" ]]; then
    echo "Error: Python 3.8 or newer is required." >&2
    exit 1
fi

# Create virtual environment
if [[ ! -d .venv ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install
source .venv/bin/activate
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Run the GUI:"
echo "  source .venv/bin/activate && python main.py"
echo ""
echo "Set debounce via CLI (e.g. 4 ms):"
echo "  source .venv/bin/activate && python main.py --set 4"
echo ""
echo "If permission is denied, prefix with sudo:"
echo "  source .venv/bin/activate && sudo python main.py --set 4"
