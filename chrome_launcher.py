import os
import shutil
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

def _copy_profile_files(src_dir: Path, dst_dir: Path):
    """
    Profil fayllarini xavfsiz nusxalash (Symlink ishlatilmaydi!).
    SingletonLock fayllariga umuman tegmaydi — shu sababli foydalanuvchining
    ochiq turgan Chrome oynalari yopilib ketmaydi.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # Muhim seans va login fayllari
    essential_files = [
        "Cookies", "Cookies-journal", 
        "Login Data", "Login Data-journal",
        "Web Data", "Web Data-journal",
        "Preferences", "Secure Preferences", 
        "Extension Cookies"
    ]

    for fname in essential_files:
        src_file = src_dir / fname
        dst_file = dst_dir / fname
        if src_file.exists():
            try:
                shutil.copy2(src_file, dst_file)
            except Exception:
                pass

    # Extensions va Storage papkalarini nusxalash
    for sub in ["Extensions", "Local Storage", "IndexedDB"]:
        src_sub = src_dir / sub
        dst_sub = dst_dir / sub
        if src_sub.exists() and not dst_sub.exists():
            try:
                if src_sub.is_dir():
                    shutil.copytree(src_sub, dst_sub, symlinks=False, ignore=shutil.ignore_patterns("Singleton*"))
            except Exception:
                pass

def launch_chrome_profiles(selected_profiles: list[str], port: int = 9333) -> bool:
    """
    GUI da tanlangan profillarnigina xavfsiz ochish.
    Foydalanuvchining ochiq brauzer oynalariga umuman ta'sir ko'rsatmaydi.
    """
    chrome_bin = find_chrome_binary()
    project_dir = Path(__file__).parent.resolve()
    bot_data_dir = project_dir / "bot_chrome_data"
    chrome_orig_dir = Path.home() / ".config" / "google-chrome"

    logger.info(f"Chrome isolatsiyalangan rejimda tayyorlanmoqda... Tanlangan: {selected_profiles}")

    # Port 9333 faol bo'lsa
    if is_cdp_active(port):
        logger.info("Chrome CDP port 9333 allaqachon faol!")
        return True

    bot_data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Eski symlink yoki tanlanmagan profillarni bot papkasidan tozalash
    for item in bot_data_dir.iterdir():
        if item.is_symlink():
            try:
                item.unlink()
            except Exception:
                pass
        elif item.is_dir() and item.name.startswith("Profile "):
            if item.name not in selected_profiles:
                try:
                    shutil.rmtree(item)
                except Exception:
                    pass

    # 2. Local State faylini nusxalash
    orig_state = chrome_orig_dir / "Local State"
    if orig_state.exists():
        try:
            shutil.copy2(orig_state, bot_data_dir / "Local State")
        except Exception:
            pass

    # 3. Default (ChatGPT) profilini ko'chirish
    if (chrome_orig_dir / "Default").exists():
        _copy_profile_files(chrome_orig_dir / "Default", bot_data_dir / "Default")

    # 4. FAQAT TANLANGAN profillarni bot papkasiga xavfsiz nusxalash
    for prof in selected_profiles:
        src_prof = chrome_orig_dir / prof
        dst_prof = bot_data_dir / prof
        if src_prof.exists():
            _copy_profile_files(src_prof, dst_prof)

    # 5. ChatGPT profilini CDP port (9333) bilan ishga tushirish
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
    
    logger.info("Chrome ChatGPT (Default) profili ochilmoqda...")
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

    # 6. FAQAT TANLANGAN YouTube profillarini alohida darchada ochish
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
