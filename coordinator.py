import asyncio
import logging
import time

logger = logging.getLogger("BotCoordinator")


class BotCoordinator:
    """
    Tizimdagi barcha botlarni muvofiqlashtiruvchi markaziy boshqaruvchi.
    1. Barcha o'zimizning bot handles ro'yxatini tutadi (Bot-to-Bot siklini oldini olish uchun).
    2. Har bir xabarni tayyor bo'lgan birinchi botga xavfsiz va unikal biriktiradi.
    3. Chatdagi so'nggi harakat vaqtini tutadi (Silence Breaker uchun).
    """

    def __init__(self):
        self.known_bots: set[str] = set()
        self.handled_messages: set[str] = set()
        self.active_profiles: list[str] = []
        self.last_activity_time: float = time.time()
        self._lock = asyncio.Lock()

    def touch_activity(self):
        self.last_activity_time = time.time()

    def register_bot(self, profile_id: str, handle: str = ""):
        if profile_id and profile_id not in self.active_profiles:
            self.active_profiles.append(profile_id)
            logger.info(f"[Coordinator] Yangi profil birikdi: [{profile_id}] (Jami faol profillar: {len(self.active_profiles)})")

        if handle:
            clean = handle.lower().lstrip("@").strip()
            if clean and clean not in self.known_bots:
                self.known_bots.add(clean)
                logger.info(f"[Coordinator] Yangi bot handle ro'yxatga olindi: '@{clean}'")

    def unregister_bot(self, profile_id: str):
        if profile_id in self.active_profiles:
            self.active_profiles.remove(profile_id)
            logger.info(f"[Coordinator] Profil ajratildi: [{profile_id}] (Qolgan faol profillar: {len(self.active_profiles)})")

    def is_our_bot(self, author: str) -> bool:
        if not author:
            return False
        clean = author.lower().lstrip("@").strip()
        return clean in self.known_bots

    async def claim_message(self, msg_id: str, profile_id: str) -> bool:
        """
        Xabarga javob berish huquqini birinchi tayyor bo'lgan profilga ajratish.
        """
        if not msg_id or not profile_id:
            return False

        async with self._lock:
            # Agar xabar allaqachon biror bot tomonidan egallangan bo'lsa, rad etiladi
            if msg_id in self.handled_messages:
                return False

            # Xabarni ushbu profil egalladi
            self.handled_messages.add(msg_id)
            if len(self.handled_messages) > 10_000:
                self.handled_messages = set(list(self.handled_messages)[-4000:])

            logger.info(f"[Coordinator] Xabar [{profile_id}] tomonidan egallandi")
            return True


coordinator = BotCoordinator()
