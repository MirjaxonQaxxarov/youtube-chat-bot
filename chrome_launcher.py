import os
import shutil
import json
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


def sanitize_local_state(bot_data_dir: Path, selected_profiles: list[str]):
    """
    bot_chrome_data/Local State faylini tozalash:
    Faqat Default va selected_profiles ni saqlab qoladi.
    Shunda Chrome qayta ochilganda tanlanmagan eski profillarni o'z-o meʼrida tiklab yubormaydi.
    """
    local_state_path = bot_data_dir / "Local State"
    if not local_state_path.exists():
        return
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        profile_sec = data.get("profile", {})
        info_cache = profile_sec.get("info_cache", {})

        allowed = set(["Default"] + selected_profiles)

        # Tanlanmagan profillarni cache dan tozalaymiz
        new_info_cache = {k: v for k, v in info_cache.items() if k in allowed}
        profile_sec["info_cache"] = new_info_cache
        profile_sec["last_opened_profiles"] = list(allowed)
        profile_sec["last_active_profiles"] = list(allowed)
        data["profile"] = profile_sec

        with open(local_state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Local State tozalandi. Faol profillar: {list(allowed)}")

    except Exception as e:
        logger.error(f"Local State ni tozalashda xato: {e}")


def _clean_session_restore(profile_dir: Path):
    """Eski sessiya va qayta tiklash fayllarini o'chirish"""
    for sub in ["Sessions", "Current Tabs", "Current Session"]:
        p = profile_dir / sub
        if p.exists():
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            except Exception:
                pass

    # Preferences dagi crash_restore ni tozalash
    pref_path = profile_dir / "Preferences"
    if pref_path.exists():
        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                pref_data = json.load(f)
            if "profile" in pref_data and "exit_type" in pref_data["profile"]:
                pref_data["profile"]["exit_type"] = "Normal"
                pref_data["profile"]["exited_cleanly"] = True
                with open(pref_path, "w", encoding="utf-8") as f:
                    json.dump(pref_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _copy_profile_files(src_dir: Path, dst_dir: Path):
    """
    Profil fayllarini xavfsiz nusxalash (Symlink o'rniga fayllar ko'chiriladi).
    SingletonLock fayllariga umuman tegmaydi — shu sababli foydalanuvchining
    ochiq turgan Chrome oynalari yopilib ketmaydi.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    
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

    _clean_session_restore(dst_dir)


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

    bot_data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Bot papkasidagi eski symlinklar va TANLANGAN bo'lmagan profillarni o'chirish
    if bot_data_dir.exists():
        for item in bot_data_dir.iterdir():
            if item.is_symlink():
                try:
                    item.unlink()
                except Exception:
                    pass
            elif item.is_dir() and item.name.startswith("Profile "):
                if item.name not in selected_profiles:
                    try:
                        logger.info(f"Tanlanmagan profil tozalanmoqda: {item.name}")
                        shutil.rmtree(item)
                    except Exception:
                        pass

    # 2. Local State faylini ko'chirish va tozalash
    orig_state = chrome_orig_dir / "Local State"
    if orig_state.exists():
        try:
            shutil.copy2(orig_state, bot_data_dir / "Local State")
        except Exception:
            pass

    sanitize_local_state(bot_data_dir, selected_profiles)

    # 3. Default (ChatGPT) profilini nusxalash
    if (chrome_orig_dir / "Default").exists():
        _copy_profile_files(chrome_orig_dir / "Default", bot_data_dir / "Default")

    # 4. FAQAT TANLANGAN profillarni bot papkasiga xavfsiz nusxalash
    for prof in selected_profiles:
        src_prof = chrome_orig_dir / prof
        dst_prof = bot_data_dir / prof
        if src_prof.exists():
            _copy_profile_files(src_prof, dst_prof)

    # CDP 9333 faol bo'lsa
    if is_cdp_active(port):
        logger.info("Chrome CDP port 9333 allaqachon faol!")
        return True

    # 5. ChatGPT profilini CDP port (9333) bilan ishga tushirish
    cmd_default = [
        chrome_bin,
        f"--user-data-dir={bot_data_dir}",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
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
            "--disable-session-crashed-bubble",
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
