import asyncio
import logging
from playwright.async_api import Page, BrowserContext
from config import TARGET_YOUTUBE_URL, TARGET_CHANNEL_URL, AUTO_RESOLVE_CHANNEL_LIVE

logger = logging.getLogger("StreamResolver")


async def resolve_live_stream_url(context: BrowserContext) -> str:
    """
    Kanal havolasidan (masalan: https://www.youtube.com/@tazkion)
    avtomatik faol jonli efir sahifasini (watch?v=...) aniqlash.
    Agar efir hali boshlanmagan bo'lsa, efir boshlangunicha periodik tekshirib turadi.
    """
    if not AUTO_RESOLVE_CHANNEL_LIVE or not TARGET_CHANNEL_URL:
        return TARGET_YOUTUBE_URL

    channel_base = TARGET_CHANNEL_URL.rstrip("/")
    if not channel_base.endswith("/live"):
        live_target_url = f"{channel_base}/live"
    else:
        live_target_url = channel_base

    logger.info(f"[StreamResolver] Kanal jonli efir manzili tekshirilmoqda: {live_target_url}")

    page = await context.new_page()

    while True:
        try:
            await page.goto(live_target_url, wait_until="domcontentloaded", timeout=25_000)
            await asyncio.sleep(2.5)

            current_url = page.url
            logger.info(f"[StreamResolver] Brauzer yo'naltirilgan URL: {current_url}")

            # 1. Agar avtomatik watch?v= ga yo'naltirilgan bo'lsa
            if "watch?v=" in current_url:
                logger.info(f"[StreamResolver] ✓ Faol jonli efir topildi! -> {current_url}")
                await page.close()
                return current_url

            # 2. Agar sahifada jonli efir kartasi bo'lsa
            live_badge = await page.query_selector("a[href*='/watch?v=']")
            if live_badge:
                href = await live_badge.get_attribute("href")
                if href and "/watch?v=" in href:
                    full_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
                    logger.info(f"[StreamResolver] ✓ Efir kartasi orqali topildi! -> {full_url}")
                    await page.close()
                    return full_url

            logger.warning(
                f"[StreamResolver] Kanalda ('{TARGET_CHANNEL_URL}') faol jonli efir topilmadi. 20s dan keyin qayta tekshiriladi..."
            )

        except Exception as e:
            logger.error(f"[StreamResolver] Tekshirishda xato: {e}")

        await asyncio.sleep(20)


async def check_channel_live_status(page: Page, channel_url: str) -> str | None:
    """Yakkalangan sahifa orqali tezkor tekshiruv"""
    try:
        url = channel_url.rstrip("/") + "/live"
        await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        await asyncio.sleep(2)
        if "watch?v=" in page.url:
            return page.url
    except Exception:
        pass
    return None
