import asyncio
import logging
import signal
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import time
import random

from config import (
    CDP_URL,
    CHATGPT_URL,
    TARGET_YOUTUBE_URL,
    YOUTUBE_PROFILES,
    PROFILE_SYSTEM_PROMPTS,
    DEFAULT_SYSTEM_PROMPT,
    ENABLE_SILENCE_BREAKER,
    SILENCE_BREAKER_MIN,
    SILENCE_BREAKER_MAX,
)
from coordinator import coordinator
from chatgpt_bot import ChatGPTBot
from youtube_bot import YouTubeChatBot

# ──────────────────────────────────────────────────────────────────────────────
#  Logging sozlash
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  │  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Main")

shutdown_event = asyncio.Event()


def _handle_signal():
    logger.info("To'xtatish signali qabul qilindi...")
    shutdown_event.set()


async def _silence_breaker_loop(gpt_bot: ChatGPTBot, active_bots: list[YouTubeChatBot]):
    if not ENABLE_SILENCE_BREAKER:
        return
    logger.info(f"Silence Breaker (Jitter: {SILENCE_BREAKER_MIN}-{SILENCE_BREAKER_MAX}s) faollashtirildi 🔥")

    while not shutdown_event.is_set():
        wait_interval = random.uniform(SILENCE_BREAKER_MIN, SILENCE_BREAKER_MAX)
        await asyncio.sleep(wait_interval)

        now = time.time()
        if now - coordinator.last_activity_time >= SILENCE_BREAKER_MIN:
            coordinator.touch_activity()

            live_bots = [b for b in active_bots if not b._closed]
            if not live_bots:
                continue

            bot_a = random.choice(live_bots)
            stream_title = await bot_a.get_stream_title()

            logger.info(
                f"[SilenceBreaker] Chat idle ({wait_interval:.1f}s jitter) -> [{bot_a.profile_id}] mavzu yuzasidan suhbat ochmoqda... ('{stream_title[:35]}')"
            )

            prompt_a = (
                f"{bot_a.system_prompt}\n"
                f"Hozirgi YouTube jonli efir mavzusi: '{stream_title}'.\n"
                f"Chatda suhbatni jonlantirish uchun shu efir va mavzu haqida 1 ta qisqa (3-8 so'z) tabiiy savol yoki munosabat yoz. "
                f"UMUMAN 'choy', 'sokin', 'jimjit chat' iboralarini ishlatma! Har safar turlicha bo'lsin."
            )

            reply_a = await gpt_bot.ask(prompt_a, "Jonli Efir", f"Mavzu: {stream_title}")
            if reply_a and not bot_a._closed:
                await bot_a._post_reply(reply_a)
                coordinator.touch_activity()

                # ── Bot-to-Bot muloqot zanjiri (Uzaro gaplashish) ──────────────
                other_bots = [b for b in live_bots if b.profile_id != bot_a.profile_id and not b._closed]
                if other_bots:
                    bot_b = random.choice(other_bots)
                    inter_delay = random.uniform(7.0, 14.0)
                    logger.info(
                        f"[SilenceBreaker] [{bot_b.profile_id}] {inter_delay:.1f}s dan so'ng [{bot_a.profile_id}] ga javob yozadi..."
                    )
                    await asyncio.sleep(inter_delay)
                    if not bot_b._closed:
                        prompt_b = (
                            f"{bot_b.system_prompt}\n"
                            f"Jonli efir mavzusi: '{stream_title}'.\n"
                            f"Chatda faol tomoshabin '{bot_a.bot_channel_name or bot_a.profile_id}' shunday yozdi: '{reply_a}'.\n"
                            f"Unga mos, 1-2 gapda do'stona, insoniy javob qaytar (emojilar ishlatish mumkin)."
                        )
                        reply_b = await gpt_bot.ask(prompt_b, bot_a.bot_channel_name or "Tomoshabin", reply_a)
                        if reply_b and not bot_b._closed:
                            await bot_b._post_reply(reply_b)
                            coordinator.touch_activity()


# ──────────────────────────────────────────────────────────────────────────────
#  Yordamchi funksiyalar

# ──────────────────────────────────────────────────────────────────────────────

def _all_pages(browser: Browser) -> list[Page]:
    """Brauzerning barcha kontekst va sahifalarini yig'ish"""
    pages = []
    for ctx in browser.contexts:
        pages.extend(ctx.pages)
    return pages


def _find_chatgpt_page(pages: list[Page]) -> Page | None:
    """ChatGPT sahifasini topish"""
    for page in pages:
        url = page.url.lower()
        if "chatgpt.com" in url or "chat.openai.com" in url:
            return page
    return None


def _find_youtube_pages(pages: list[Page]) -> list[Page]:
    """YouTube sahifalarini topish"""
    return [p for p in pages if "youtube.com" in p.url.lower()]


async def _open_chatgpt_if_missing(ctx: BrowserContext) -> Page:
    """ChatGPT sahifasi topilmasa yangi tab ochish"""
    logger.warning("ChatGPT tab topilmadi — yangi tab ochilmoqda...")
    page = await ctx.new_page()
    await page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    logger.info(f"ChatGPT sahifasi ochildi: {page.url}")
    return page


# ──────────────────────────────────────────────────────────────────────────────
#  Asosiy funksiya
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    # Signal handlerlari
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    print("\n" + "=" * 60)
    print("   YOUTUBE MULTI-CHAT + CHATGPT AVTOMATIZATSIYASI")
    print("=" * 60 + "\n")

    async with async_playwright() as p:

        # ── 1. Chrome ga CDP orqali ulanish ──────────────────────────────────
        logger.info(f"Chrome ga ulanilmoqda: {CDP_URL}")
        try:
            browser: Browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            logger.error(f"Chrome ga ulanib bo'lmadi: {e}")
            logger.error("Iltimos, run.sh ni avval ishga tushiring!")
            return

        all_pages = _all_pages(browser)
        logger.info(f"Jami ochiq tablar: {len(all_pages)}")

        for i, pg in enumerate(all_pages):
            logger.info(f"  Tab {i+1}: {pg.url[:80]}")

        # ── 2. ChatGPT sahifasini topish ─────────────────────────────────────
        gpt_page = _find_chatgpt_page(all_pages)
        if not gpt_page:
            if browser.contexts:
                gpt_page = await _open_chatgpt_if_missing(browser.contexts[0])
            else:
                logger.error("Brauzerda hech qanday kontekst yo'q!")
                return

        logger.info(f"ChatGPT tab: {gpt_page.url}")

        # ── 3. ChatGPT botini tayyor qilish ──────────────────────────────────
        gpt_bot = ChatGPTBot(gpt_page)
        await gpt_bot.start()

        # ── 4. YouTube sahifalarini topish ────────────────────────────────────
        yt_pages = _find_youtube_pages(_all_pages(browser))
        logger.info(f"Topilgan YouTube tablari: {len(yt_pages)}")

        if not yt_pages:
            logger.warning(
                f"YouTube tab topilmadi — avtomatik tarzda ochilmoqda: {TARGET_YOUTUBE_URL}"
            )
            for ctx in browser.contexts:
                try:
                    p_new = await ctx.new_page()
                    await p_new.goto(TARGET_YOUTUBE_URL, wait_until="domcontentloaded")
                    yt_pages.append(p_new)
                except Exception as e:
                    logger.error(f"Tab ochishda xato: {e}")

        # ── 5. Har bir YouTube sahifasi uchun bot yaratish ───────────────────
        active_bots: list[YouTubeChatBot] = []

        for i, yt_page in enumerate(yt_pages, start=1):
            # Sahifa qaysi profilda ekanini aniqlash
            profile_name = f"Profile_{i}"
            yt_url_lower = yt_page.url.lower()

            # Profil nomini Chrome kontekst metadata dan aniqlashga urinish
            # (to'g'ridan-to'g'ri Playwright'da profil nomini olish mumkin emas,
            #  shuning uchun tartib bo'yicha YOUTUBE_PROFILES ga moslashtirish)
            if i - 1 < len(YOUTUBE_PROFILES):
                profile_name = YOUTUBE_PROFILES[i - 1]

            # System prompt
            system_prompt = PROFILE_SYSTEM_PROMPTS.get(profile_name, DEFAULT_SYSTEM_PROMPT)

            logger.info(
                f"Bot yaratilyapti: [{profile_name}] → {yt_page.url[:60]}"
            )

            bot = YouTubeChatBot(
                profile_id=profile_name,
                page=yt_page,
                gpt_bot=gpt_bot,
                system_prompt=system_prompt,
            )
            await bot.start()
            active_bots.append(bot)

        # ── 6. Silence Breaker (Chatni faol tutish fonda) ────────────────────
        asyncio.create_task(_silence_breaker_loop(gpt_bot, active_bots))

        # ── 7. Tayyor xabari ─────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"  ✓ OPTIMALLASHGAN TIZIM TAYYOR!")
        print(f"  ✓ {len(active_bots)} ta YouTube profil kuzatilmoqda va o'zaro suhbatda")
        print(f"  ✓ Efir mavzusi DOM'dan dinamik o'qilmoqda")
        print(f"  ✓ Human Jitter & Continuous Reaksiya/Emoji bosish FAOL")
        print(f"  To'xtatish uchun: Ctrl+C")
        print("=" * 60 + "\n")

        # ── 7. Dastur to'xtatilguncha kutish ─────────────────────────────────
        await shutdown_event.wait()
        logger.info("Botlar to'xtatildi. Xayr!")


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDastur to'xtatildi.")
