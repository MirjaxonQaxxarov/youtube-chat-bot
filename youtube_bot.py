import asyncio
import logging
import random
import time
from playwright.async_api import Page
from config import (
    MIN_REPLY_DELAY,
    MAX_REPLY_DELAY,
    COOLDOWN_PER_BOT,
    REPLY_PROBABILITY,
    MAX_MESSAGE_LENGTH,
    PROFILE_BOT_NAMES,
    ENABLE_AUTO_REACTIONS,
    REACTION_INTERVAL_MIN,
    REACTION_INTERVAL_MAX,
)
from coordinator import coordinator

logger = logging.getLogger("YouTubeBot")

# ─── Iframe ichidagi to'g'ri selektorlar ──────────────────────────────────────
CHAT_ITEMS_SELECTOR  = "yt-live-chat-item-list-renderer #items"
CHAT_MSG_TAG         = "yt-live-chat-text-message-renderer"
CHAT_INPUT_SELECTOR  = "yt-live-chat-text-input-field-renderer #input"
SEND_BTN_SELECTOR    = "#send-button yt-button-shape button, #send-button button"


class YouTubeChatBot:
    """
    Har bir YouTube jonli efir sahifasi uchun alohida bot.
    MutationObserver iframe ICHIGA to'g'ridan-to'g'ri ulanadi.
    Avtomatik reaksiya/emoji bosish va efir mavzusini aniqlash imkoniyati mavjud.
    """

    def __init__(self, profile_id: str, page: Page, gpt_bot, system_prompt: str = ""):
        self.profile_id    = profile_id
        self.page          = page
        self.gpt_bot       = gpt_bot
        self.system_prompt = system_prompt

        self.seen_messages: set[str] = set()
        self.bot_channel_name: str = PROFILE_BOT_NAMES.get(profile_id, "").strip().lower()
        self.last_reply_time: float = 0.0

        # Chat joylashgan joy: Page yoki Frame
        self._chat_frame = None   # playwright Frame ob'ekti
        self._is_iframe  = False
        self._closed     = False  # tab yopilganda True ga o'tadi
        self.stream_title: str = ""

        # Unique callback nomi
        safe = profile_id.replace(" ", "_").replace("-", "_")
        self._cb = f"__ytbot_{safe}__"

    # ─────────────────────────────────────────────────────────────────────────

    async def start(self):
        logger.info(f"[{self.profile_id}] Sozlanmoqda...")

        # Tab yopilganda handler
        self.page.on("close", self._on_page_closed)

        # 1. Chat frame ni topish
        await self._find_chat_frame()

        # 2. Bot kanal nomini va Efir mavzusini aniqlash
        if not self.bot_channel_name:
            await self._detect_bot_name()
        self.stream_title = await self.get_stream_title()

        # 3. Python callbackni brauzerga ulash
        if self._closed:
            return
        try:
            await self.page.expose_function(self._cb, self._on_msg_sync)
        except Exception:
            pass  # allaqachon ro'yxatga olingan

        # 4. Observer ni IFRAME ichiga yuklash
        await self._inject_observer()

        # 5. Coordinator ga ro'yxatga qo'shish
        coordinator.register_bot(self.profile_id, self.bot_channel_name)

        # 6. Fonda uzluksiz reaksiya/emoji bosish davrasini boshlash
        if ENABLE_AUTO_REACTIONS:
            asyncio.create_task(self._reactions_loop())

        logger.info(
            f"[{self.profile_id}] ✓ Kuzatuv va Reaksiyalar faol! Bot: '{self.bot_channel_name or 'aniqlanmagan'}' | Efir: '{self.stream_title[:40]}'"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Stream mavzusi / sarlavhasini olish
    # ─────────────────────────────────────────────────────────────────────────

    async def get_stream_title(self) -> str:
        """Asosiy YouTube sahifasidan efir sarlavhasi/mavzusini olish"""
        if self._closed:
            return "Jonli Efir"
        try:
            title_el = await self.page.query_selector(
                "h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string, ytd-watch-metadata h1"
            )
            if title_el:
                txt = (await title_el.inner_text()).strip()
                if txt:
                    return txt
            # Fallback
            doc_title = await self.page.title()
            doc_title = doc_title.replace("- YouTube", "").strip()
            if doc_title:
                return doc_title
        except Exception:
            pass
        return "Jonli Efir"

    # ─────────────────────────────────────────────────────────────────────────
    # Uzluksiz Reaksiya/Emoji bosish
    # ─────────────────────────────────────────────────────────────────────────

    async def _reactions_loop(self):
        """Fonda uzluksiz reaksiyalar/emojilar bosib turish (Human Jitter bilan)"""
        while not self._closed:
            wait_sec = random.uniform(REACTION_INTERVAL_MIN, REACTION_INTERVAL_MAX)
            await asyncio.sleep(wait_sec)
            if self._closed or not self._chat_frame:
                continue

            try:
                res = await self._chat_frame.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll(
                        '#reaction-control-panel button, yt-live-chat-reactions-control-panel-renderer button, #reactions button, #reaction-buttons button'
                    )).filter(b => b.offsetWidth > 0 && b.offsetHeight > 0);

                    if (btns.length > 0) {
                        const idx = Math.floor(Math.random() * btns.length);
                        btns[idx].click();
                        return { ok: true, clicked: idx, total: btns.length };
                    }
                    return { ok: false, reason: 'reaksiya tugmalari topilmadi' };
                }
                """)
                if res and res.get("ok"):
                    logger.debug(f"[{self.profile_id}] ❤️ Reaksiya bosildi")
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Chat frame topish
    # ─────────────────────────────────────────────────────────────────────────

    async def _find_chat_frame(self):
        """Playwright Frame ob'ektini topish"""
        try:
            await self.page.wait_for_selector("iframe#chatframe", timeout=20_000)
        except Exception:
            logger.warning(f"[{self.profile_id}] iframe#chatframe kutishda timeout")

        frame = self.page.frame(name="chatframe")
        if frame:
            try:
                await frame.wait_for_selector(CHAT_ITEMS_SELECTOR, timeout=15_000)
            except Exception:
                pass
            self._chat_frame = frame
            self._is_iframe  = True
            logger.info(f"[{self.profile_id}] Chat iframe topildi ✓")
            return

        logger.warning(f"[{self.profile_id}] iframe topilmadi, asosiy sahifada qidirilmoqda")
        self._chat_frame = self.page.main_frame
        self._is_iframe  = False

    # ─────────────────────────────────────────────────────────────────────────
    # Bot nomini aniqlash
    # ─────────────────────────────────────────────────────────────────────────

    async def _detect_bot_name(self):
        """Iframe ichidagi muallif nomini DOM dan o'qish"""
        if not self._chat_frame:
            return
        try:
            el = await self._chat_frame.query_selector(
                "yt-live-chat-message-input-renderer #author-name"
            )
            if el:
                name = (await el.inner_text()).strip()
                if name and name.lower() not in ("меню аккаунта", "account menu", ""):
                    self.bot_channel_name = name.lower()
                    coordinator.register_bot(self.profile_id, name)
                    logger.info(f"[{self.profile_id}] Bot nomi (chat): {name}")
                    return
        except Exception:
            pass

        try:
            btn = await self.page.query_selector("button#avatar-btn")
            if btn:
                label = await btn.get_attribute("aria-label") or ""
                if label and label.lower() not in ("меню аккаунта", "account menu", ""):
                    self.bot_channel_name = label.lower()
                    coordinator.register_bot(self.profile_id, label)
                    logger.info(f"[{self.profile_id}] Bot nomi (avatar): {label}")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # MutationObserver — to'g'ridan-to'g'ri IFRAME ichiga
    # ─────────────────────────────────────────────────────────────────────────

    async def _inject_observer(self):
        if not self._chat_frame:
            return

        js = f"""
        () => {{
            const CB   = {self._cb!r};
            const SEL  = {CHAT_ITEMS_SELECTOR!r};
            const TAG  = {CHAT_MSG_TAG!r};

            function attach() {{
                const container = document.querySelector(SEL);
                if (!container) return false;
                if (container.__ytbotAttached) return true;
                container.__ytbotAttached = true;

                const observer = new MutationObserver(mutations => {{
                    for (const m of mutations) {{
                        for (const node of m.addedNodes) {{
                            if (node.nodeType !== 1) continue;
                            if (node.tagName.toLowerCase() !== TAG) continue;

                            const authorEl = node.querySelector('#author-name');
                            const msgEl    = node.querySelector('#message');
                            const author   = authorEl ? authorEl.innerText.trim() : '';
                            const text     = msgEl    ? msgEl.innerText.trim()    : '';
                            const id       = node.id  || (author + '|' + text);

                            if (!text) continue;

                            if (window[CB]) {{
                                window[CB]({{ id, author, text }});
                            }}
                        }}
                    }}
                }});

                observer.observe(container, {{ childList: true }});
                return true;
            }}

            if (!attach()) {{
                const t = setInterval(() => {{ if (attach()) clearInterval(t); }}, 1000);
            }}
        }}
        """

        try:
            await self._chat_frame.evaluate(js)
            logger.info(f"[{self.profile_id}] Observer iframe ichiga ulandi ✓")
        except Exception as e:
            logger.error(f"[{self.profile_id}] Observer xatosi: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Xabar qabul qilish
    # ─────────────────────────────────────────────────────────────────────────

    def _on_msg_sync(self, data: dict):
        if not self._closed:
            asyncio.ensure_future(self._handle(data))

    def _on_page_closed(self):
        self._closed = True
        coordinator.unregister_bot(self.profile_id)
        logger.warning(f"[{self.profile_id}] ⚠️ Tab yopildi — bu profil kuzatuvi to'xtatildi.")

    async def _handle(self, data: dict):
        if self._closed:
            return

        msg_id = str(data.get("id", ""))
        author = data.get("author", "").strip()
        text   = data.get("text",   "").strip()

        if not text:
            return

        # 1. O'zimizning botlarimiz xabarlarini o'tkazib yuborish (Bot-to-Bot cheksiz sikl oldini olish)
        if coordinator.is_our_bot(author):
            return

        coordinator.touch_activity()

        # 2. Cooldown tekshiruvi
        now = time.time()
        if now - self.last_reply_time < COOLDOWN_PER_BOT:
            return

        # 3. Xabarni egallash (Faqat bitta bot javob beradi)
        if msg_id:
            claimed = await coordinator.claim_message(msg_id, self.profile_id)
            if not claimed:
                return

        # 4. Insoniy kechikish (Human Jitter)
        delay = random.uniform(MIN_REPLY_DELAY, MAX_REPLY_DELAY)
        logger.info(f"[{self.profile_id}] 📨 {author}: '{text}' (Tabiiy kutish: {delay:.1f}s)")

        await asyncio.sleep(delay)
        if self._closed:
            return

        # Efir mavzusini olish va Prompt yaratish
        title = await self.get_stream_title()
        full_prompt = (
            f"{self.system_prompt}\n"
            f"Jonli efir sarlavhasi / mavzusi: '{title}'.\n"
            f"Chatda muallif '{author}' shunday yozdi: '{text}'.\n"
            f"Unga va efir mavzusiga mos, o'zbek tilida 1 ta qisqa va samimiy insoniy javob qaytar."
        )

        reply = await self.gpt_bot.ask(full_prompt, author, text)

        if reply and not self._closed:
            await self._post_reply(reply)

    # ─────────────────────────────────────────────────────────────────────────
    # Chatga yozish
    # ─────────────────────────────────────────────────────────────────────────

    async def _post_reply(self, text: str):
        if self._closed:
            return

        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH].rsplit(" ", 1)[0] + "..."

        if not self._chat_frame:
            await self._find_chat_frame()
            if not self._chat_frame:
                logger.error(f"[{self.profile_id}] Chat frame yo'q!")
                return

        try:
            result = await self._chat_frame.evaluate("""
            async (replyText) => {
                let input = document.querySelector(
                    'yt-live-chat-text-input-field-renderer #input, div#input[contenteditable="true"], #input.yt-live-chat-text-input-field-renderer'
                );

                if (!input) {
                    const container = document.querySelector('yt-live-chat-message-input-renderer');
                    if (container && typeof container.click === 'function') {
                        container.click();
                        await new Promise(r => setTimeout(r, 400));
                        input = document.querySelector('yt-live-chat-text-input-field-renderer #input, div#input[contenteditable="true"]');
                    }
                }

                if (!input) {
                    input = document.querySelector('#input');
                }

                if (!input) return {ok: false, error: 'input topilmadi'};

                if (typeof input.focus === 'function') input.focus();
                if (typeof input.click === 'function') input.click();

                try {
                    input.innerText = replyText;
                } catch(e) {}
                try {
                    input.textContent = replyText;
                } catch(e) {}

                // Event dispatch - YouTube Web Component event model
                input.dispatchEvent(new InputEvent('input', {
                    bubbles: true, cancelable: true, inputType: 'insertText', data: replyText
                }));
                input.dispatchEvent(new Event('change', { bubbles: true }));

                await new Promise(r => setTimeout(r, 500));

                // Yuborish tugmasi
                const btn = document.querySelector(
                    '#send-button yt-button-shape button, #send-button button'
                );
                if (btn && !btn.disabled && typeof btn.click === 'function') {
                    btn.click();
                    return {ok: true, method: 'button'};
                }

                // Enter klavishi (fallback)
                ['keydown','keypress','keyup'].forEach(type => {
                    input.dispatchEvent(new KeyboardEvent(type, {
                        key: 'Enter', code: 'Enter', keyCode: 13,
                        which: 13, bubbles: true
                    }));
                });
                return {ok: true, method: 'enter'};
            }
            """, text)

            if result and result.get("ok"):
                self.last_reply_time = time.time()
                logger.info(f"[{self.profile_id}] ✅ Javob [{result.get('method')}]: '{text[:60]}'")
            else:
                logger.warning(f"[{self.profile_id}] ⚠️ Yuborishda muammo: {result}")

        except Exception as e:
            logger.error(f"[{self.profile_id}] Javob yuborishda xato: {e}")


