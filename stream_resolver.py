import asyncio
import re
import logging
from playwright.async_api import Page, BrowserContext
import config

logger = logging.getLogger("StreamResolver")


async def resolve_live_stream_url(context: BrowserContext) -> str:
    """
    Kanal havolasidan (masalan: https://www.youtube.com/@tazkion)
    avtomatik faol jonli efir sahifasini (watch?v=...) aniqlash.
    """
    channel_url = config.TARGET_CHANNEL_URL or "https://www.youtube.com/@tazkion"
    channel_base = channel_url.rstrip("/")
    if not channel_base.endswith("/live"):
        live_target_url = f"{channel_base}/live"
    else:
        live_target_url = channel_base

    logger.info(f"[StreamResolver] Kanal jonli efir manzili tekshirilmoqda: {live_target_url}")

    page = await context.new_page()

    for attempt in range(5):
        try:
            await page.goto(live_target_url, wait_until="domcontentloaded", timeout=25_000)
            await asyncio.sleep(3.0)

            current_url = page.url
            logger.info(f"[StreamResolver] (Urinish {attempt+1}) Brauzer URL: {current_url}")

            # 1. Avtomatik watch?v= ga yo'naltirilgan bo'lsa
            if "watch?v=" in current_url:
                logger.info(f"[StreamResolver] ✓ Faol jonli efir URL orqali topildi! -> {current_url}")
                await page.close()
                return current_url

            # 2. Page HTML tarkibidan canonical meta va videoId ni izlash (Regex)
            content = await page.content()
            
            # Canonical meta link
            canonical_match = re.search(r'<link\s+rel="canonical"\s+href="(https://www\.youtube\.com/watch\?v=[^"]+)"', content)
            if canonical_match:
                found_url = canonical_match.group(1)
                logger.info(f"[StreamResolver] ✓ Canonical meta orqali topildi! -> {found_url}")
                await page.close()
                return found_url

            # og:url meta
            og_match = re.search(r'<meta\s+property="og:url"\s+content="(https://www\.youtube\.com/watch\?v=[^"]+)"', content)
            if og_match:
                found_url = og_match.group(1)
                logger.info(f"[StreamResolver] ✓ Meta og:url orqali topildi! -> {found_url}")
                await page.close()
                return found_url

            # Direct videoId match from YouTube initial JSON data
            video_ids = re.findall(r'"watchEndpoint":\s*\{\s*"videoId":\s*"([a-zA-Z0-9_-]{11})"', content)
            if video_ids:
                found_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                logger.info(f"[StreamResolver] ✓ YouTube JSON metadata orqali topildi! -> {found_url}")
                await page.close()
                return found_url

            # 3. Sahifada efir kartalari HTML elementlarini izlash
            selectors = [
                "a#thumbnail[href*='/watch?v=']",
                "a[href*='/watch?v=']",
                "ytd-grid-video-renderer a[href*='/watch?v=']"
            ]
            for sel in selectors:
                badge = await page.query_selector(sel)
                if badge:
                    href = await badge.get_attribute("href")
                    if href and "/watch?v=" in href:
                        full_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
                        logger.info(f"[StreamResolver] ✓ DOM kartasi orqali topildi! -> {full_url}")
                        await page.close()
                        return full_url

            logger.warning(f"[StreamResolver] (Urinish {attempt+1}) Kanalda faol jonli efir topilmadi. Qayta tekshirilmoqda...")

        except Exception as e:
            logger.error(f"[StreamResolver] Tekshirishda xato: {e}")

        await asyncio.sleep(4.0)

    await page.close()
    fallback_url = config.TARGET_YOUTUBE_URL or "https://www.youtube.com"
    logger.warning(f"[StreamResolver] Jonli efir topilmadi, standart URL ishlatiladi: {fallback_url}")
    return fallback_url


async def check_channel_live_status(page: Page, channel_url: str) -> str | None:
    """Yakkalangan sahifa orqali tezkor tekshiruv"""
    try:
        url = channel_url.rstrip("/") + "/live"
        await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        await asyncio.sleep(2.5)
        if "watch?v=" in page.url:
            return page.url
        content = await page.content()
        m = re.search(r'href="(https://www\.youtube\.com/watch\?v=[^"]+)"', content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None
