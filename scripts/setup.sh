#!/usr/bin/env bash
set -e

echo "========================================================"
echo "              DotaBlitz Setup Wizard (Linux/macOS)"
echo "========================================================"

cd "$(dirname "$0")/.."

if ! command -v python3 &> /dev/null; then
    echo "[!] python3 could not be found. Please install Python 3.11+."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment (venv)..."
    python3 -m venv venv
fi

echo "[*] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[*] Installing Dota 2 GSI configuration..."
python3 scripts/install_gsi.py

echo ""
echo "========================================================"
echo "[✓] Setup completed successfully!"
echo "To start DotaBlitz, run:"
echo "    source venv/bin/activate"
echo "    python run.py"
echo "========================================================"
