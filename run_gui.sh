#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#  YOUTUBE MULTI-PROFILE BOT — DESKTOP GUI LAUNCHER
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

# Talab qilinadigan kutubxonalarni o'rnatish
if ! ./venv/bin/python3 -c "import customtkinter, playwright" &>/dev/null; then
    echo "📦 Zarruriy kutubxonalar (customtkinter, playwright, pillow) o'rnatilmoqda..."
    ./venv/bin/pip install -r requirements.txt customtkinter pillow
    ./venv/bin/playwright install chromium
fi

# Chrome CDP port 9333 ochiqligini tekshirish
if ! nc -z 127.0.0.1 9333 &>/dev/null; then
    echo "🌐 Chrome CDP brauzeri ishga tushirilmoqda..."
    bash ./run.sh --bg &
    sleep 3
fi

echo "✨ Desktop GUI Dasturi ochilmoqda..."
./venv/bin/python3 gui_app.py
