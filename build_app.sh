#!/usr/bin/env bash
# One-command build script — produces dist/MouseDebounce.app
# Run this once on your Mac; the resulting .app is fully standalone.
set -euo pipefail

APP_NAME="MouseDebounce"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"

echo "======================================"
echo " Mouse Debounce Controller — Build"
echo "======================================"
echo ""

# ── Check Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found."
    echo "Install Python 3.8+ from https://www.python.org/downloads/macos/"
    exit 1
fi

PY_OK=$(python3 -c "import sys; print(sys.version_info >= (3, 8))")
if [[ "$PY_OK" != "True" ]]; then
    echo "Error: Python 3.8 or newer is required (you have $(python3 --version))."
    exit 1
fi

echo "Python: $(python3 --version)  ✓"

# ── Virtual environment ──────────────────────────────────────────────────────
if [[ ! -d .venv ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# ── Dependencies ─────────────────────────────────────────────────────────────
echo "Installing build dependencies..."
pip install --quiet --upgrade pip
pip install --quiet hid pyinstaller

# ── Build ────────────────────────────────────────────────────────────────────
echo ""
echo "Building $APP_NAME.app (this takes ~30 seconds)..."
pyinstaller mouse_debounce.spec --clean --noconfirm

# ── Result ───────────────────────────────────────────────────────────────────
if [[ -d "$APP_PATH" ]]; then
    echo ""
    echo "======================================"
    echo " Build successful!"
    echo "======================================"
    echo ""
    echo "App location:  $(pwd)/$APP_PATH"
    echo ""
    echo "To use it:"
    echo "  1. Open Finder → go to  $(pwd)/dist/"
    echo "  2. Double-click MouseDebounce.app"
    echo ""
    echo "  OR copy it to Applications:"
    echo "    cp -r dist/MouseDebounce.app /Applications/"
    echo "    open /Applications/MouseDebounce.app"
    echo ""
    echo "Note: on first launch macOS may show 'unidentified developer'."
    echo "  Right-click the app → Open → Open  (only needed once)."
    echo ""
    echo "If the app says 'no mouse found', try:"
    echo "  System Settings → Privacy & Security → Input Monitoring"
    echo "  → add MouseDebounce (or Terminal if running from CLI)"
else
    echo "Build failed — check the PyInstaller output above."
    exit 1
fi
