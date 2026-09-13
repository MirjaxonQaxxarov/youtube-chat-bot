import os
from pathlib import Path

# ──────────────────────────────────────────────
#  Chrome CDP ulanish sozlamalari
# ──────────────────────────────────────────────
CDP_PORT = 9333
CDP_URL  = f"http://127.0.0.1:{CDP_PORT}"

# ──────────────────────────────────────────────
#  URL va Kanal manzillari
# ──────────────────────────────────────────────
CHATGPT_URL               = "https://chatgpt.com"
TARGET_YOUTUBE_URL        = "https://www.youtube.com/watch?v=NtkK22Rtyco"
TARGET_CHANNEL_URL        = "https://www.youtube.com/@tazkion" # Kanal havolasi
AUTO_RESOLVE_CHANNEL_LIVE = True                              # Kanal linkidan avtomatik liveni topish

# ──────────────────────────────────────────────
#  Resurs va Media optimallashtirish (RAM / CPU)
# ──────────────────────────────────────────────
BLOCK_VIDEO_STREAMS = True   # Video oqimlarini (googlevideo.com) bloklab, CPU/RAMni 80% tejash
BLOCK_IMAGES        = False  # Rasm elementlarini bloklash (ixtiyoriy)

# ──────────────────────────────────────────────
#  Proksi (Proxy) Sozlamalari
# ──────────────────────────────────────────────
ENABLE_PROXIES      = True   # Har bir profil uchun alohida Proksi ishlatish
USE_FREE_PROXIES    = True   # Bepul proksilarni avtomatik yuklash
CUSTOM_PROXIES      = []     # Shaxsiy proksilar ro'yxati (masalan: ["http://ip:port", ...])

# ──────────────────────────────────────────────
#  Akkauntlar Rotatsiyasi
# ──────────────────────────────────────────────
ENABLE_ACCOUNT_ROTATION = True  # Profillarni navbatma-navbat almashib ishlatish
ROTATION_INTERVAL_MINS = 25    # Har 25 daqiqada profillar navbati almashadi

# ──────────────────────────────────────────────
#  Profil sozlamalari
# ──────────────────────────────────────────────
CHATGPT_PROFILE = "Default"

YOUTUBE_PROFILES = [
    "Profile 1",
    "Profile 2",
    "Profile 5",
    "Profile 6",
]

# ──────────────────────────────────────────────
#  Xabar va Jitter (Insoniy kechikishlar) sozlamalari
# ──────────────────────────────────────────────
MAX_MESSAGE_LENGTH   = 180   # YouTube chat chegarasi
MIN_REPLY_DELAY      = 7     # Minimum javob kutish (sekund)
MAX_REPLY_DELAY      = 16    # Maksimum javob kutish (sekund)
COOLDOWN_PER_BOT     = 10    # Bitta botning ketma-ket javoblar oralig'i (sekund)
REPLY_PROBABILITY    = 0.90  # 90% xabarlarga javob berish

# ──────────────────────────────────────────────
#  Silence Breaker (Chatni faol tutish) Jitter sozlamalari
# ──────────────────────────────────────────────
ENABLE_SILENCE_BREAKER  = True
SILENCE_BREAKER_MIN     = 15   # Minimum jimjitlik kutish (sekund)
SILENCE_BREAKER_MAX     = 35   # Maksimum jimjitlik kutish (sekund)

# ──────────────────────────────────────────────
#  Reaksiya/Emoji bosish Jitter sozlamalari
# ──────────────────────────────────────────────
ENABLE_AUTO_REACTIONS   = True
REACTION_INTERVAL_MIN   = 10   # Reaksiya bosish min oralig'i (sekund)
REACTION_INTERVAL_MAX   = 25   # Reaksiya bosish max oralig'i (sekund)

# ──────────────────────────────────────────────
#  Har bir profil uchun alohida system prompt
# ──────────────────────────────────────────────
PROFILE_SYSTEM_PROMPTS = {
    "Profile 1": (
        "Sen YouTube jonli efirida oddiy, quvnoq tomoshabinsan (o'zingni BOT yoki AI deb atama!). "
        "Efir mavzusiga mos, o'zbek tilida juda qisqa (3-10 so'z), samimiy va jonli xabarlar yoz. "
        "Bir xil va zerikarli iboralarni ('choy bilan', 'sokin efir', 'jimjit chat') UMUMAN ISHLATMA! "
        "Har safar turlicha, emojilar va jonli iboralar bilan yoz."
    ),
    "Profile 2": (
        "Sen efirni qiziqish bilan kuzatayotgan faol tomoshabinsan (o'zingni BOT yoki AI deb atama!). "
        "Mavzudan kelib chiqib savollar ber, munosabat bildir. Qisqa va do'stona bo'l. "
        "'Choy', 'jimjitlik' degan qolip so'zlardan qoch, insoniy real suhbat qur."
    ),
    "Profile 5": (
        "Sen jonli efir chatida suhbatlashayotgan qiziqarli insonsan. "
        "Mavzuga mos hazilkash, samimiy va qisqa tarzda o'zbekcha yoz. "
        "Bot ekaningni sezdirma, turli xil emojilar va jonli iboralardan foydalan."
    ),
    "Profile 6": (
        "Sen efirdagi samimiy va bilimdon tomoshabinsan. "
        "Chatdagi gaplarga va efir mazmuniga qisqa, aniq va insoniy munosabat bildir."
    ),
}

DEFAULT_SYSTEM_PROMPT = (
    "Sen YouTube jonli efiridagi oddiy va do'stona tomoshabinsan. "
    "O'zingni bot yoki AI deb aytma. Efir mavzusiga mos o'zbek tilida qisqa va tabiiy yoz."
)

PROFILE_BOT_NAMES = {}



