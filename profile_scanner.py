import os
import json
from pathlib import Path

def get_chrome_user_data_dir() -> Path:
    """Tizimdagi Chrome profil ma'lumotlari papkasini aniqlash"""
    system = os.name
    home = Path.home()
    
    # 1. Avval mahalliy bot_chrome_data ni tekshiramiz
    local_bot_dir = Path("./bot_chrome_data").resolve()
    if local_bot_dir.exists() and any(local_bot_dir.glob("Profile*")):
        return local_bot_dir

    # 2. Tizim Chrome papkalari
    if system == "posix":
        # Linux yoki macOS
        mac_path = home / "Library" / "Application Support" / "Google" / "Chrome"
        linux_path = home / ".config" / "google-chrome"
        if mac_path.exists():
            return mac_path
        if linux_path.exists():
            return linux_path
    elif system == "nt":
        # Windows
        win_path = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
        if win_path.exists():
            return win_path

    # Fallback Linux path
    return home / ".config" / "google-chrome"

def scan_chrome_profiles() -> list[dict]:
    """Chrome ichidagi barcha mavjud profillarni ro'yxat shaklida qaytarish"""
    user_data_dir = get_chrome_user_data_dir()
    profiles = []

    # Local State JSON dan profil nomlarini o'qishga urinish
    local_state_file = user_data_dir / "Local State"
    profile_info_cache = {}

    if local_state_file.exists():
        try:
            with open(local_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile_info_cache = data.get("profile", {}).get("info_cache", {})
        except Exception:
            pass

    # Target kataloglarni izlash
    possible_dirs = []
    if user_data_dir.exists():
        for item in user_data_dir.iterdir():
            if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile ")):
                possible_dirs.append(item)

    # Agar local Chrome da profillar topilmasa, default 6 ta profil taklif qilinadi
    if not possible_dirs:
        default_names = ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5", "Profile 6"]
        for name in default_names:
            profiles.append({
                "id": name,
                "name": name,
                "exists": False
            })
        return profiles

    # Topilgan papkalarni saralash (Default avval, keyin Profile 1, 2, ...)
    def sort_key(d: Path):
        if d.name == "Default":
            return (0, 0)
        try:
            num = int(d.name.replace("Profile ", ""))
            return (1, num)
        except ValueError:
            return (2, d.name)

    possible_dirs.sort(key=sort_key)

    for pdir in possible_dirs:
        dir_name = pdir.name
        info = profile_info_cache.get(dir_name, {})
        display_name = info.get("name", dir_name)
        user_name = info.get("user_name", "")
        
        full_label = display_name
        if user_name and user_name != display_name:
            full_label = f"{display_name} ({user_name})"

        profiles.append({
            "id": dir_name,
            "name": full_label,
            "path": str(pdir),
            "exists": True
        })

    return profiles

if __name__ == "__main__":
    profs = scan_chrome_profiles()
    print(f"Topilgan Chrome profillari ({len(profs)} ta):")
    for p in profs:
        print(f" - {p['id']}: {p['name']} (Path: {p.get('path', 'N/A')})")
