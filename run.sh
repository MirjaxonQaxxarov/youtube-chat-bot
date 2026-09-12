#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  YouTube Multi-Profile + ChatGPT Bot Launcher
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Ranglar ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[✓]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[!]${NC}    $*"; }
err()   { echo -e "${RED}[✗]${NC}    $*"; }
step()  { echo -e "\n${BOLD}$*${NC}"; }

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   YouTube Multi-Profile + ChatGPT Bot Launcher  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── 0. Tizim bog'liqliklarini avtomatik o'rnatish ────────────────────────────
install_sys_deps() {
    local missing=()
    command -v python3 &>/dev/null || missing+=("python3")
    command -v curl &>/dev/null || missing+=("curl")

    if command -v python3 &>/dev/null; then
        python3 -m venv --help &>/dev/null || missing+=("python3-venv")
    fi

    local chrome_exists=0
    for c in /opt/google/chrome/chrome google-chrome google-chrome-stable chromium-browser chromium; do
        if command -v "$c" &>/dev/null || [ -x "$c" ]; then
            chrome_exists=1
            break
        fi
    done

    if [ ${#missing[@]} -eq 0 ] && [ "$chrome_exists" -eq 1 ]; then
        return 0
    fi

    step "[0/3] Tizim dasturlari (Python, Chrome, Curl) tekshirilmoqda va o'rnatilmoqda..."

    SUDO=""
    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
        command -v sudo &>/dev/null && SUDO="sudo"
    fi

    if command -v apt-get &>/dev/null; then
        info "Debian/Ubuntu paket menejeri orqali dasturlar o'rnatilmoqda..."
        $SUDO apt-get update -qq || true

        if [ ${#missing[@]} -gt 0 ]; then
            info "Yetishmayotgan tizim paketlari: ${missing[*]}"
            $SUDO apt-get install -y -qq python3 python3-venv python3-pip curl || true
        fi

        if [ "$chrome_exists" -eq 0 ]; then
            info "Google Chrome brauzeri o'rnatilmoqda..."
            curl -fsSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb
            $SUDO apt-get install -y -qq /tmp/chrome.deb || $SUDO apt-get install -y -qq chromium-browser || true
            rm -f /tmp/chrome.deb
        fi

    elif command -v dnf &>/dev/null; then
        info "Fedora/RHEL paket menejeri orqali dasturlar o'rnatilmoqda..."
        $SUDO dnf install -y python3 curl google-chrome-stable || true

    elif command -v pacman &>/dev/null; then
        info "Arch Linux paket menejeri orqali dasturlar o'rnatilmoqda..."
        $SUDO pacman -Sy --noconfirm python curl chromium || true

    elif command -v brew &>/dev/null; then
        info "macOS Homebrew orqali dasturlar o'rnatilmoqda..."
        brew install python curl google-chrome || true
    fi

    ok "Tizim dasturlari tayyor!"
}

install_sys_deps

# ─── 1. Virtual muhit ─────────────────────────────────────────────────────────
step "[1/3] Virtual muhit tekshirilmoqda..."
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    warn "venv topilmadi. Avtomatik yaratilmoqda va kutubxonalar o'rnatilmoqda..."
    python3 -m venv "$SCRIPT_DIR/venv"
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install --upgrade pip
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        pip install playwright
    fi
    python3 -m playwright install chromium
fi
source "$SCRIPT_DIR/venv/bin/activate"
ok "Virtual muhit faol"

# ─── 2. Chrome debug portini tekshirish ───────────────────────────────────────
step "[2/3] Chrome debug porti tekshirilmoqda (9333)..."

check_port() {
    curl -s -f http://127.0.0.1:9333/json/version >/dev/null 2>&1
}

CHROME_BIN=""
for c in /opt/google/chrome/chrome google-chrome google-chrome-stable chromium-browser chromium; do
    if command -v "$c" &>/dev/null || [ -x "$c" ]; then
        CHROME_BIN="$c"
        break
    fi
done
[ -z "$CHROME_BIN" ] && CHROME_BIN="/opt/google/chrome/chrome"

BOT_DATA_DIR="$SCRIPT_DIR/bot_chrome_data"
CHROME_ORIG_DIR="$HOME/.config/google-chrome"
YT_URL="https://www.youtube.com/watch?v=R4j4n5EAE0s"
CHATGPT_URL="https://chatgpt.com"

if check_port; then
    ok "Chrome debug porti 9333 allaqachon faol!"
else
    warn "Port 9333 faol emas. Chrome avtomatik ishga tushirilmoqda..."
    
    info "Mavjud Chrome jarayonlari to'xtatilmoqda..."
    pkill -9 -f "/opt/google/chrome/chrome" 2>/dev/null || true
    pkill -9 -f "google-chrome" 2>/dev/null || true
    sleep 2

    info "Singleton lock fayllar tozalanmoqda..."
    rm -f "$BOT_DATA_DIR/Singleton"* 2>/dev/null || true
    rm -f "$CHROME_ORIG_DIR/Singleton"* 2>/dev/null || true

    mkdir -p "$BOT_DATA_DIR"
    [ -f "$CHROME_ORIG_DIR/Local State" ] && cp -f "$CHROME_ORIG_DIR/Local State" "$BOT_DATA_DIR/Local State" 2>/dev/null || true

    if [ -d "$CHROME_ORIG_DIR/Default" ]; then
        mkdir -p "$BOT_DATA_DIR/Default"
        for f in "Cookies" "Login Data" "Login Data-journal" "Web Data" "Preferences" "Secure Preferences" "Extension Cookies"; do
            [ -f "$CHROME_ORIG_DIR/Default/$f" ] && cp -f "$CHROME_ORIG_DIR/Default/$f" "$BOT_DATA_DIR/Default/$f" 2>/dev/null || true
        done
        [ -d "$CHROME_ORIG_DIR/Default/Extensions" ] && ln -snf "$CHROME_ORIG_DIR/Default/Extensions" "$BOT_DATA_DIR/Default/Extensions" 2>/dev/null || true
    fi

    for prof in "Profile 1" "Profile 2" "Profile 5" "Profile 6"; do
        if [ -d "$CHROME_ORIG_DIR/$prof" ]; then
            ln -snf "$CHROME_ORIG_DIR/$prof" "$BOT_DATA_DIR/$prof" 2>/dev/null || true
            rm -f "$CHROME_ORIG_DIR/$prof/Singleton"* 2>/dev/null || true
        fi
    done

    CHROME_LOG="/tmp/yt_bot_chrome.log"
    info "Chrome Default (ChatGPT) profilida ochilmoqda..."
    "$CHROME_BIN" \
        --user-data-dir="$BOT_DATA_DIR" \
        --remote-debugging-port=9333 \
        --remote-allow-origins="*" \
        --profile-directory="Default" \
        --no-first-run \
        --no-default-browser-check \
        "$CHATGPT_URL" >"$CHROME_LOG" 2>&1 &

    CHROME_PID=$!
    info "Chrome ishga tushdi (PID=$CHROME_PID). Port 9333 kutilmoqda..."

    PORT_OK=0
    for i in $(seq 1 20); do
        sleep 1
        if check_port &>/dev/null; then
            PORT_OK=1
            ok "Port 9333 tayyor! ($i soniyada)"
            break
        fi
    done

    if [ "$PORT_OK" -eq 0 ]; then
        err "20 soniya ichida port 9333 ochilmadi."
        exit 1
    fi
fi

# YouTube profillarini alohida oynada ochish
info "YouTube profillari ochilmoqda..."
for prof in "Profile 1" "Profile 2" "Profile 5" "Profile 6"; do
    if [ -d "$CHROME_ORIG_DIR/$prof" ]; then
        info "  ▶ $prof ochilmoqda..."
        "$CHROME_BIN" \
            --user-data-dir="$BOT_DATA_DIR" \
            --profile-directory="$prof" \
            --no-first-run \
            --no-default-browser-check \
            "$YT_URL" >/dev/null 2>&1 &
        sleep 1.5
    fi
done
sleep 3

# ─── 3. Python bot ────────────────────────────────────────────────────────────
step "[3/3] Python bot ishga tushmoqda..."
echo ""

cleanup() {
    echo ""
    warn "Bot to'xtatildi."
    exit 0
}
trap cleanup SIGINT SIGTERM

python3 "$SCRIPT_DIR/main.py"
