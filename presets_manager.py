import json
import os
from pathlib import Path

PRESETS_DIR = Path(__file__).parent / "presets"

DEFAULT_PROXYSCRAPE_URL = (
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=protocolipport&format=json&limit=15&skip=15"
)

DEFAULT_PRESET_DATA = {
    "preset_name": "Standart Sozlama",
    "target_channel_url": "https://www.youtube.com/@tazkion",
    "target_youtube_url": "",
    "auto_resolve_channel_live": True,
    "selected_profiles": ["Profile 1", "Profile 2", "Profile 5", "Profile 6"],
    "proxy_api_url": DEFAULT_PROXYSCRAPE_URL,
    "enable_proxies": False,
    "use_free_proxies": False,
    "custom_proxies": [],
    "block_video_streams": True,
    "enable_silence_breaker": True,
    "silence_breaker_min": 15,
    "silence_breaker_max": 35,
    "enable_auto_reactions": True,
    "profile_prompts": {
        "Profile 1": (
            "Sen YouTube jonli efirida oddiy, quvnoq tomoshabinsan (o'zingni BOT yoki AI deb atama!). "
            "Efir mavzusiga mos, o'zbek tilida juda qisqa (3-10 so'z), samimiy va jonli xabarlar yoz. "
            "Bir xil va zerikarli iboralarni ('choy bilan', 'sokin efir', 'jimjit chat') UMUMAN ISHLATMA! "
            "Har safar turlicha, emojilar va jonli iboralar bilan yoz."
        ),
        "Profile 2": (
            "Sen efirni qiziqish bilan kuzatayotgan faol tomoshabinsan (o'zingni BOT yoki AI deb atama!). "
            "Mavzudan kelib chiqib savollar ber, munosabat bildir. Qisqa va do'stona bo'l."
        ),
        "Profile 5": (
            "Sen jonli efir chatida suhbatlashayotgan qiziqarli insonsan. "
            "Mavzuga mos hazilkash, samimiy va qisqa tarzda o'zbekcha yoz."
        ),
        "Profile 6": (
            "Sen efirdagi samimiy va bilimdon tomoshabinsan. "
            "Chatdagi gaplarga va efir mazmuniga qisqa, aniq va insoniy munosabat bildir."
        )
    }
}

class PresetsManager:
    def __init__(self, presets_dir: Path = PRESETS_DIR):
        self.presets_dir = presets_dir
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_preset()

    def _ensure_default_preset(self):
        """Boshlang'ich default preset mavjudligini ta'minlash"""
        default_file = self.presets_dir / "default.json"
        if not default_file.exists():
            self.save_preset("default", DEFAULT_PRESET_DATA)

    def list_presets(self) -> list[str]:
        """Mavjud preset nomlarini ro'yxat shaklida qaytarish"""
        presets = []
        for file in self.presets_dir.glob("*.json"):
            presets.append(file.stem)
        return sorted(presets)

    def load_preset(self, name: str) -> dict:
        """Preset JSON faylidan ma'lumotlarni o'qish"""
        file_path = self.presets_dir / f"{name}.json"
        if not file_path.exists():
            return DEFAULT_PRESET_DATA.copy()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Standart kalitlar yetishmasa default lar bilan to'ldiramiz
                merged = DEFAULT_PRESET_DATA.copy()
                merged.update(data)
                return merged
        except Exception:
            return DEFAULT_PRESET_DATA.copy()

    def save_preset(self, name: str, data: dict) -> bool:
        """Preset ma'lumotlarini JSON faylga saqlash"""
        file_path = self.presets_dir / f"{name}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def delete_preset(self, name: str) -> bool:
        """Presetni o'chirish"""
        if name == "default":
            return False # Default preset o'chirilmaydi
        file_path = self.presets_dir / f"{name}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

presets_manager = PresetsManager()
