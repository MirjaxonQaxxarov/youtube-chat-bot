import asyncio
import logging
import random
from urllib.parse import urlparse
import urllib.request
from config import ENABLE_PROXIES, USE_FREE_PROXIES, CUSTOM_PROXIES

logger = logging.getLogger("ProxyManager")


class ProxyManager:
    """
    Bepul HTTP/SOCKS proksilarni avtomatik yuklash,
    ularni test qilish va har bir bot profiliga biriktirish bo'yicha menejer.
    """

    FREE_PROXY_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    ]

    def __init__(self):
        self.working_proxies: list[str] = list(CUSTOM_PROXIES)
        self.profile_proxies: dict[str, str] = {}

    async def initialize(self):
        if not ENABLE_PROXIES:
            return

        if CUSTOM_PROXIES:
            logger.info(f"Shaxsiy proksilar yuklandi: {len(CUSTOM_PROXIES)} ta")

        if USE_FREE_PROXIES and not self.working_proxies:
            logger.info("Bepul proksilar olinmoqda va test qilinmoqda...")
            fetched = await self._fetch_free_proxies()
            logger.info(f"Jami topilgan bepul proksilar: {len(fetched)} ta. Tekshirilmoqda...")
            valid = await self._validate_proxies(fetched[:40])
            self.working_proxies.extend(valid)
            logger.info(f"✓ {len(self.working_proxies)} ta ishchi proksi tayyor!")

    async def _fetch_free_proxies(self) -> list[str]:
        proxies = set()
        loop = asyncio.get_running_loop()

        for url in self.FREE_PROXY_SOURCES:
            try:
                def _req(target_url):
                    req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return response.read().decode("utf-8", errors="ignore")

                content = await loop.run_in_executor(None, _req, url)
                for line in content.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        parts = line.split(":")
                        if len(parts) == 2 and parts[1].isdigit():
                            proxies.add(f"http://{line}")
            except Exception:
                continue

        return list(proxies)

    async def _validate_proxies(self, proxy_list: list[str]) -> list[str]:
        valid = []
        tasks = [self._test_single_proxy(p) for p in proxy_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for p, ok in zip(proxy_list, results):
            if isinstance(ok, bool) and ok:
                valid.append(p)
                if len(valid) >= 10:  # Etarli proksi yig'ilgach to'xtash
                    break
        return valid

    async def _test_single_proxy(self, proxy_url: str) -> bool:
        loop = asyncio.get_running_loop()

        def _check():
            try:
                proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
                opener = urllib.request.build_opener(proxy_handler)
                opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
                with opener.open('http://httpbin.org/ip', timeout=3) as resp:
                    return resp.status == 200
            except Exception:
                return False

        try:
            return await loop.run_in_executor(None, _check)
        except Exception:
            return False

    def assign_proxy(self, profile_id: str) -> str:
        """Profil uchun ishchi proksilardan birini ajratish"""
        if not ENABLE_PROXIES or not self.working_proxies:
            return ""

        if profile_id not in self.profile_proxies:
            selected = random.choice(self.working_proxies)
            self.profile_proxies[profile_id] = selected
            logger.info(f"[{profile_id}] Proksi biriktirildi: {selected}")

        return self.profile_proxies[profile_id]


proxy_manager = ProxyManager()
