import asyncio
import logging
from playwright.async_api import Page
from config import MAX_MESSAGE_LENGTH

logger = logging.getLogger("ChatGPTBot")


class ChatGPTBot:
    """
    Bitta ChatGPT tab bilan ishlaydi.
    Barcha YouTube profillaridan kelgan so'rovlarni
    navbat (asyncio.Queue) orqali TARTIBLI qayta ishlaydi.
    Har bir so'rov uchun:
      - system_prompt (profil konteksti)
      - author (xabar muallifi)
      - message (xabar matni)
    qabul qilinadi va ChatGPT javobini qaytaradi.
    """

    # ChatGPT prompt input selektorlari (yangi va eski UI uchun)
    PROMPT_SELECTORS = [
        "#prompt-textarea",
        "div[id='prompt-textarea']",
        "textarea[data-id='prompt-textarea']",
        "div[contenteditable='true'][data-lexical-editor='true']",
        "div[contenteditable='true'].ProseMirror",
        "textarea[placeholder]",
    ]

    # ChatGPT javob elementlari
    RESPONSE_SELECTOR = "div[data-message-author-role='assistant']"

    # Yuborish tugmasi
    SEND_BTN_SELECTOR = "button[data-testid='send-button'], button[aria-label='Send prompt']"

    # Stop tugmasi (javob yozilayotganda ko'rsatiladi)
    STOP_BTN_SELECTOR = (
        "button[data-testid='stop-button'], "
        "button[aria-label*='Stop'], "
        "button[aria-label*='stop']"
    )

    def __init__(self, page: Page):
        self.page = page
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task = None
        self._ready = False
        self.last_reply_text: str = ""

    async def start(self):
        """Worker vazifasini fonda ishga tushirish"""
        await self._wait_for_ready()
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("ChatGPTBot tayyor — navbatni kutmoqda...")

    async def _wait_for_ready(self, timeout: int = 30):
        """ChatGPT sahifasi to'liq yuklanishini kutish"""
        for selector in self.PROMPT_SELECTORS:
            try:
                await self.page.wait_for_selector(selector, timeout=timeout * 1000, state="visible")
                logger.info(f"ChatGPT input topildi: {selector}")
                self._ready = True
                return
            except Exception:
                continue
        logger.warning("ChatGPT input topilmadi — keyinroq urinib ko'riladi")

    async def ask(self, system_prompt: str, author: str, message: str) -> str:
        """
        YouTube botidan so'rov qabul qilish.
        Bu metod o'z navbati kelguncha bloklaydi.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        await self.queue.put((system_prompt, author, message, future))
        try:
            return await future
        except Exception as e:
            logger.error(f"ask() xatosi: {e}")
            return ""

    async def _worker(self):
        """Navbatdagi vazifalarni ketma-ket qayta ishlash"""
        while True:
            system_prompt, author, message, future = await self.queue.get()
            try:
                logger.info(f"Yangi vazifa: [{author}] → '{message[:50]}...' " if len(message) > 50 else f"Yangi vazifa: [{author}] → '{message}'")
                reply = await self._send_to_chatgpt(system_prompt, author, message)
                if not future.done():
                    future.set_result(reply)
            except Exception as e:
                logger.error(f"ChatGPT xatolik: {e}")
                if not future.done():
                    future.set_result("")
            finally:
                self.queue.task_done()
                await asyncio.sleep(1)  # ChatGPT rate-limit himoyasi

    async def _find_prompt_box(self):
        """Prompt input maydonini topish"""
        for selector in self.PROMPT_SELECTORS:
            try:
                el = self.page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    return el
            except Exception:
                continue
        return None

    async def _send_to_chatgpt(self, system_prompt: str, author: str, message: str) -> str:
        """ChatGPT veb interfeysiga yozish va javobni olish"""

        full_prompt = (
            f"{system_prompt}\n\n"
            f"YouTube live chat da '{author}' shunday dedi: \"{message}\"\n\n"
            f"Faqat javob matnini yoz (maksimum {MAX_MESSAGE_LENGTH} belgi, 1 gap)."
            f"DIQQAT: Oldingi javoblaringni takrorlama, har safar YANGI va noyob fikr bildir!"
        )

        # ── 0. Boshlang'ich javoblar sonini saqlash ─────────────────
        initial_response_count = 0
        try:
            initial_response_count = await self.page.locator(self.RESPONSE_SELECTOR).count()
        except Exception:
            pass

        # ── 1. Prompt maydonini topish ─────────────────────────────
        prompt_box = await self._find_prompt_box()
        if not prompt_box:
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            prompt_box = await self._find_prompt_box()
            if not prompt_box:
                logger.error("Prompt maydoni topilmadi!")
                return ""

        # ── 2. Matnni yozish va Lexical event yuborish ──────────────
        try:
            await prompt_box.click()
            await asyncio.sleep(0.2)

            await prompt_box.evaluate("""
            (el, text) => {
                el.focus();
                el.innerHTML = '';
                if (el.value !== undefined) el.value = '';
                document.execCommand('insertText', false, text);
                el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, data: text }));
            }
            """, full_prompt)
            await asyncio.sleep(0.4)
        except Exception as e:
            logger.warning(f"Lexical fill warning: {e}")
            await prompt_box.fill(full_prompt)

        # ── 3. Yuborish ───────────────────────────────────────────
        sent = False
        try:
            send_btn = self.page.locator(self.SEND_BTN_SELECTOR).first
            if await send_btn.count() > 0 and await send_btn.is_visible() and await send_btn.is_enabled():
                await send_btn.click()
                sent = True
        except Exception:
            pass

        if not sent:
            await prompt_box.press("Enter")

        # ── 4. Yangi javob tugunining paydo bo'lishini kutish ─────────
        new_response_found = False
        for _ in range(25):  # max 12.5 soniya yangi javob blokini kutish
            current_count = await self.page.locator(self.RESPONSE_SELECTOR).count()
            if current_count > initial_response_count:
                new_response_found = True
                break
            await asyncio.sleep(0.5)

        if not new_response_found:
            logger.warning("ChatGPT yangi javob bermadi (so'rov yuborilmadi yoki band)")
            return ""

        # Stop tugmasi paydo bo'lib, yo'qolguncha kutish
        try:
            stop_btn = self.page.locator(self.STOP_BTN_SELECTOR).first
            await stop_btn.wait_for(state="visible", timeout=4000)
            await stop_btn.wait_for(state="hidden", timeout=40000)
        except Exception:
            await asyncio.sleep(2)

        # ── 5. Oxirgi yangi javobni olish ───────────────────────────
        try:
            last_response = self.page.locator(self.RESPONSE_SELECTOR).last
            reply = await last_response.inner_text()
        except Exception as e:
            logger.error(f"Javobni o'qishda xato: {e}")
            return ""

        clean = reply.strip().replace("\n", " ")
        if len(clean) > MAX_MESSAGE_LENGTH:
            clean = clean[:MAX_MESSAGE_LENGTH].rsplit(" ", 1)[0] + "..."

        # Dublikat tekshiruvi
        if clean == self.last_reply_text:
            logger.warning(f"ChatGPT bir xil dublikat javob berdi, o'tkazib yuborildi: '{clean}'")
            return ""

        self.last_reply_text = clean
        logger.info(f"Javob: '{clean}'")
        return clean
