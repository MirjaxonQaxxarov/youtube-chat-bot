#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#  YOUTUBE MULTI-PROFILE BOT — DESKTOP GUI LAUNCHER v3.0
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "   🚀 YOUTUBE CHAT BOT DESKTOP GUI APPLICATION LAUNCHING..."
echo "============================================================"

# Python venv borligini tekshirish
if [ ! -d "venv" ]; then
    echo "⚠️ Python virtual muhiti topilmadi. Avtomatik yaratilmoqda..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
fi

# Zarruriy kutubxonalar o'rnatilganligini tekshirish
if ! ./venv/bin/python3 -c "import customtkinter, playwright, requests, PIL" &>/dev/null; then
    echo "📦 Zarruriy kutubxonalar o'rnatilmoqda..."
    ./venv/bin/pip install -r requirements.txt customtkinter pillow requests
    ./venv/bin/playwright install chromium
fi

echo "✨ Desktop GUI Dasturi ochilmoqda..."
./venv/bin/python3 gui_app.py
