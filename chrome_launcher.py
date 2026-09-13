import os
import subprocess
import time
import urllib.request
import logging
from pathlib import Path

logger = logging.getLogger("ChromeLauncher")

def is_cdp_active(port: int = 9333) -> bool:
    """Chrome CDP porti faolligini tekshirish"""
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.urlopen(url, timeout=1.5)
        return req.status == 200
    except Exception:
        return False

def find_chrome_binary() -> str:
    """Tizimdagi Chrome brauzer ijro faylini topish"""
    candidates = [
        "/opt/google/chrome/chrome",
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium"
    ]
    for c in candidates:
        try:
            res = subprocess.run(["which", c], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return "/opt/google/chrome/chrome"

def launch_chrome_profiles(selected_profiles: list[str], port: int = 9333) -> bool:
    """
    GUI dan berilgan buyruq bo'yicha Chrome ni CDP va tanlangan profillar bilan ishga tushirish.
    """
    chrome_bin = find_chrome_binary()
    project_dir = Path(__file__).parent.resolve()
    bot_data_dir = project_dir / "bot_chrome_data"
    chrome_orig_dir = Path.home() / ".config" / "google-chrome"

    logger.info(f"Chrome ishga tushirilmoqda... Bin: {chrome_bin}")

    # Agar port 9333 faol bo'lsa, uni ishlatamiz
    if is_cdp_active(port):
        logger.info("Chrome CDP port 9333 allaqachon faol! Profillar tayyor.")
        return True

    # Eski Chrome jarayonlarini va lock fayllarni tozalaymiz
    try:
        subprocess.run(["pkill", "-9", "-f", chrome_bin], capture_output=True)
        time.sleep(1)
    except Exception:
        pass

    bot_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Singleton lock larni o'chirish
    for lock in bot_data_dir.glob("Singleton*"):
        try:
            lock.unlink()
        except Exception:
            pass

    # Local State nusxalash
    orig_state = chrome_orig_dir / "Local State"
    if orig_state.exists():
        try:
            with open(orig_state, "rb") as sf, open(bot_data_dir / "Local State", "wb") as df:
                df.write(sf.read())
        except Exception:
            pass

    # Default (ChatGPT) profilini tayyorlash
    if (chrome_orig_dir / "Default").exists():
        (bot_data_dir / "Default").mkdir(exist_ok=True)
        for fname in ["Cookies", "Login Data", "Web Data", "Preferences", "Secure Preferences"]:
            src = chrome_orig_dir / "Default" / fname
            dst = bot_data_dir / "Default" / fname
            if src.exists():
                try:
                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                except Exception:
                    pass

    # Tanlangan profillar uchun symlink yaratish
    for prof in selected_profiles:
        src_prof = chrome_orig_dir / prof
        dst_prof = bot_data_dir / prof
        if src_prof.exists() and not dst_prof.exists():
            try:
                dst_prof.symlink_to(src_prof)
            except Exception:
                pass

    # 1. Avval ChatGPT uchun Default profilni CDP port bilan ochish
    cmd_default = [
        chrome_bin,
        f"--user-data-dir={bot_data_dir}",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--mute-audio",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "https://chatgpt.com"
    ]
    
    logger.info("Chrome Default (ChatGPT) profili ochilmoqda...")
    subprocess.Popen(cmd_default, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Port ochilishini kutish
    port_ok = False
    for i in range(15):
        time.sleep(1)
        if is_cdp_active(port):
            port_ok = True
            logger.info(f"✓ Chrome CDP port {port} tayyor ({i+1}s)!")
            break

    if not port_ok:
        logger.error(f"Chrome CDP port {port} ochilmadi!")
        return False

    # 2. Tanlangan YouTube profillarini alohida darcha (window) da ochish
    for prof in selected_profiles:
        if prof == "Default":
            continue
        logger.info(f"▶ [{prof}] profili brauzer darchasida ochilmoqda...")
        cmd_prof = [
            chrome_bin,
            f"--user-data-dir={bot_data_dir}",
            f"--profile-directory={prof}",
            "--no-first-run",
            "--no-default-browser-check",
            "--mute-audio",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "https://www.youtube.com"
        ]
        subprocess.Popen(cmd_prof, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launch_chrome_profiles(["Profile 1", "Profile 2"])
