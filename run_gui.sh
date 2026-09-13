#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#  YOUTUBE MULTI-PROFILE BOT — DESKTOP GUI LAUNCHER
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "   🚀 YOUTUBE CHAT BOT DESKTOP GUI APPLICATION LAUNCHING..."
echo "============================================================"

# Chrome CDP 9333 va profillarni orqa fonda tayyorlash
bash ./run.sh --chrome-only

echo "✨ Desktop GUI Dasturi ochilmoqda..."
./venv/bin/python3 gui_app.py
