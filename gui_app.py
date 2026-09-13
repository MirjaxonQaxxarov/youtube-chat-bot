import sys
import os
import json
import logging
import asyncio
import threading
import time
from pathlib import Path

import customtkinter as ctk
from PIL import Image

# Local imports
from profile_scanner import scan_chrome_profiles
from presets_manager import presets_manager, DEFAULT_PROXYSCRAPE_URL
from chrome_launcher import launch_chrome_profiles, is_cdp_active
from proxy_manager import proxy_manager
from stream_resolver import check_channel_live_status
import config

# Set CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Thread-safe Logging Handler to redirect logs to GUI console
class CTkLogHandler(logging.Handler):
    def __init__(self, text_widget: ctk.CTkTextbox):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append_text():
            try:
                if not self.text_widget.winfo_exists():
                    return
                self.text_widget.configure(state="normal")
                if record.levelno >= logging.ERROR:
                    self.text_widget.insert("end", f"❌ {msg}\n")
                elif record.levelno >= logging.WARNING:
                    self.text_widget.insert("end", f"⚠️ {msg}\n")
                else:
                    self.text_widget.insert("end", f"ℹ️ {msg}\n")
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self.text_widget, "after") and self.text_widget.winfo_exists():
            self.text_widget.after(0, append_text)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Multi-Profile AI Chat Bot v3.0 — Professional Control Panel")
        self.geometry("1150x860")
        self.minsize(1000, 750)

        self.bot_thread = None
        self.loop = None
        self.is_running = False

        # Scan Chrome Profiles
        self.available_profiles = scan_chrome_profiles()
        self.profile_checkboxes = {}
        self.bot_cards = {}
        self.current_prompts = {}

        self._create_layout()
        self._load_preset_to_ui("default")

    def _create_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── HEADER ────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="#181825", corner_radius=10)
        header_frame.grid(row=0, column=0, padx=15, pady=(12, 6), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="🚀 YOUTUBE MULTI-PROFILE BOT CONTROL PANEL v3.0",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#89B4FA"
        )
        title_label.pack(side="left", padx=20, pady=12)

        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="STATUS: STOPPED 🔴",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#F38BA8",
            fg_color="#313244",
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.status_badge.pack(side="right", padx=20, pady=10)

        # ── TABVIEW (MAIN CONTROLS) ───────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self, corner_radius=10, fg_color="#1E1E2E")
        self.tabview.grid(row=1, column=0, padx=15, pady=6, sticky="nsew")

        self.tab_dashboard = self.tabview.add("🎮 Boshqaruv & Dashboard")
        self.tab_profiles = self.tabview.add("👥 Chrome Profillari")
        self.tab_proxies = self.tabview.add("🌐 Proxy Scrape & Tarmoq")
        self.tab_jitter = self.tabview.add("⚙️ Jitter & Optimallash")
        self.tab_presets = self.tabview.add("📁 Presets (Retseptlar)")

        self._build_tab_dashboard()
        self._build_tab_profiles()
        self._build_tab_proxies()
        self._build_tab_jitter()
        self._build_tab_presets()

        # ── FOOTER: CONSOLE LOG WIDGET ────────────────────────────────────────
        console_frame = ctk.CTkFrame(self, fg_color="#181825", corner_radius=10)
        console_frame.grid(row=2, column=0, padx=15, pady=(6, 12), sticky="ew")
        console_frame.grid_columnconfigure(0, weight=1)

        c_title = ctk.CTkLabel(console_frame, text="💻 Real-Vaqt Konsol Loglari:", font=ctk.CTkFont(size=13, weight="bold"))
        c_title.pack(anchor="w", padx=15, pady=(8, 2))

        self.txt_console = ctk.CTkTextbox(
            console_frame,
            height=140,
            fg_color="#11111B",
            text_color="#CDD6F4",
            font=ctk.CTkFont(family="Courier", size=12),
            corner_radius=8
        )
        self.txt_console.pack(fill="x", padx=15, pady=(0, 10))

        # Setup Logging redirection to GUI
        gui_handler = CTkLogHandler(self.txt_console)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s │ %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)

        logging.info("Professional Desktop GUI Interfeysi tayyorlandi ✅")

    # ── TAB 1: DASHBOARD & MAIN CONTROLS ──────────────────────────────────────
    def _build_tab_dashboard(self):
        tab = self.tab_dashboard
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        # Left Column: Action Buttons & Stream target
        left_col = ctk.CTkFrame(tab, fg_color="transparent")
        left_col.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Main Action Buttons Frame
        act_box = ctk.CTkFrame(left_col, fg_color="#252538", corner_radius=10)
        act_box.pack(fill="x", pady=(0, 10))

        act_title = ctk.CTkLabel(act_box, text="🚀 Asosiy Boshqaruv Tugmalari", font=ctk.CTkFont(size=15, weight="bold"))
        act_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.btn_start = ctk.CTkButton(
            act_box,
            text="▶ BARCHA BOTLARNI ISHGA TUSHIRISH",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#A6E3A1",
            text_color="#11111B",
            hover_color="#94E2D5",
            height=45,
            command=self.start_bot
        )
        self.btn_start.pack(fill="x", padx=15, pady=6)

        self.btn_stop = ctk.CTkButton(
            act_box,
            text="⏹ TO'XTATISH",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#F38BA8",
            text_color="#11111B",
            hover_color="#EBA0AC",
            height=40,
            state="disabled",
            command=self.stop_bot
        )
        self.btn_stop.pack(fill="x", padx=15, pady=6)

        # YouTube Live Target Section
        target_box = ctk.CTkFrame(left_col, fg_color="#252538", corner_radius=10)
        target_box.pack(fill="x", pady=5)

        t_title = ctk.CTkLabel(target_box, text="📺 YouTube Kanal & Jonli Efir Manzili", font=ctk.CTkFont(size=15, weight="bold"))
        t_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.ent_channel_url = ctk.CTkEntry(target_box, placeholder_text="Kanal Linki (masalan: https://www.youtube.com/@tazkion)")
        self.ent_channel_url.pack(fill="x", padx=15, pady=4)

        self.var_auto_resolve = ctk.CTkCheckBox(target_box, text="Kanal linkidan avtomatik liveni topish")
        self.var_auto_resolve.pack(anchor="w", padx=15, pady=4)

        self.ent_stream_url = ctk.CTkEntry(target_box, placeholder_text="To'g'ridan-to'g'ri Live URL (https://www.youtube.com/watch?v=...)")
        self.ent_stream_url.pack(fill="x", padx=15, pady=4)

        # Right Column: Active Bot Cards Grid
        right_col = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        right_col.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        b_title = ctk.CTkLabel(right_col, text="🤖 Faol Bot Profillari Holati", font=ctk.CTkFont(size=15, weight="bold"))
        b_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.cards_scroll = ctk.CTkScrollableFrame(right_col, fg_color="transparent", height=280)
        self.cards_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh_bot_cards()

    def _refresh_bot_cards(self):
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()
        self.bot_cards.clear()

        for pinfo in self.available_profiles:
            pid = pinfo["id"]
            pname = pinfo["name"]
            
            card = ctk.CTkFrame(self.cards_scroll, fg_color="#1E1E2E", corner_radius=8)
            card.pack(fill="x", padx=5, pady=4)

            lbl_name = ctk.CTkLabel(card, text=f"👤 {pid} ({pname[:25]})", font=ctk.CTkFont(size=13, weight="bold"))
            lbl_name.pack(side="left", padx=12, pady=8)

            lbl_status = ctk.CTkLabel(card, text="Kutmoqda ⏸", text_color="#FAB387", font=ctk.CTkFont(size=12))
            lbl_status.pack(side="right", padx=12, pady=8)
            
            self.bot_cards[pid] = lbl_status

    # ── TAB 2: PROFILES & PROMPTS ─────────────────────────────────────────────
    def _build_tab_profiles(self):
        tab = self.tab_profiles
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        # Left Column: Profile Checkboxes
        left_box = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        left_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        title = ctk.CTkLabel(left_box, text="👥 Ishga tushadigan Chrome Profillarini Tanlang", font=ctk.CTkFont(size=15, weight="bold"))
        title.pack(anchor="w", padx=15, pady=(10, 5))

        prof_scroll = ctk.CTkScrollableFrame(left_box, fg_color="transparent")
        prof_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        for pinfo in self.available_profiles:
            pid = pinfo["id"]
            pname = pinfo["name"]
            var = ctk.BooleanVar(value=(pid in config.YOUTUBE_PROFILES))
            chk = ctk.CTkCheckBox(prof_scroll, text=f"{pid} — {pname}", variable=var)
            chk.pack(anchor="w", padx=10, pady=5)
            self.profile_checkboxes[pid] = var

        # Right Column: System Prompt Editor
        right_box = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        right_box.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        p_title = ctk.CTkLabel(right_box, text="📝 Profil AI Personal va System Prompti", font=ctk.CTkFont(size=15, weight="bold"))
        p_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.prompt_profile_menu = ctk.CTkOptionMenu(
            right_box,
            values=[p["id"] for p in self.available_profiles],
            command=self._on_prompt_profile_changed
        )
        self.prompt_profile_menu.pack(anchor="w", padx=15, pady=4)

        self.txt_prompt = ctk.CTkTextbox(right_box, height=180, corner_radius=8, fg_color="#1E1E2E")
        self.txt_prompt.pack(fill="both", expand=True, padx=15, pady=8)

        # Quick Preset Prompt Generator Helpers
        tpl_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        tpl_frame.pack(fill="x", padx=15, pady=(0, 10))

        lbl_tpl = ctk.CTkLabel(tpl_frame, text="⚡ Shablondan yuklash:", font=ctk.CTkFont(size=12))
        lbl_tpl.pack(side="left", padx=5)

        btn_tpl1 = ctk.CTkButton(tpl_frame, text="Quvnoq", width=65, command=lambda: self._set_prompt_template(1))
        btn_tpl1.pack(side="left", padx=3)

        btn_tpl2 = ctk.CTkButton(tpl_frame, text="Qiziquvchan", width=75, command=lambda: self._set_prompt_template(2))
        btn_tpl2.pack(side="left", padx=3)

        btn_tpl3 = ctk.CTkButton(tpl_frame, text="Hazilkash", width=70, command=lambda: self._set_prompt_template(3))
        btn_tpl3.pack(side="left", padx=3)

    def _set_prompt_template(self, tpl_id: int):
        templates = {
            1: "Sen YouTube jonli efirida quvnoq tomoshabinsan. Samimiy, qisqa (3-8 so'z) o'zbekcha yoz. Emojilar ishlat.",
            2: "Sen jonli efirni diqqat bilan kuzatayotgan qiziquvchan tomoshabinsan. Mavzu bo'yicha qisqa savollar ber.",
            3: "Sen efir chatida do'stona va hazilkash tomoshabinsan. Suhbatdoshlarga samimiy munosabat bildir."
        }
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", templates.get(tpl_id, ""))

    # ── TAB 3: PROXY SCRAPE & NETWORK ────────────────────────────────────────
    def _build_tab_proxies(self):
        tab = self.tab_proxies

        box = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        box.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(box, text="🌐 Proxy Scrape & Tarmoq Sozlamalari", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(15, 10))

        self.var_enable_proxies = ctk.CTkCheckBox(box, text="Bepul Proxy (ProxyScrape v4) xizmatini yoqish")
        self.var_enable_proxies.pack(anchor="w", padx=20, pady=5)

        lbl_url = ctk.CTkLabel(box, text="ProxyScrape API URL Endpoint:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_url.pack(anchor="w", padx=20, pady=(10, 2))

        self.ent_proxy_url = ctk.CTkEntry(box, placeholder_text="ProxyScrape API URL...")
        self.ent_proxy_url.pack(fill="x", padx=20, pady=5)

        self.btn_test_proxies = ctk.CTkButton(
            box,
            text="⚡ Proxylarni Yuklash va Sinab Ko'rish",
            fg_color="#89B4FA",
            text_color="#11111B",
            command=self._cmd_test_proxies
        )
        self.btn_test_proxies.pack(anchor="w", padx=20, pady=10)

        lbl_custom = ctk.CTkLabel(box, text="Shaxsiy Proksilar (manual format: http://user:pass@ip:port):", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_custom.pack(anchor="w", padx=20, pady=(10, 2))

        self.txt_custom_proxies = ctk.CTkTextbox(box, height=120, fg_color="#1E1E2E")
        self.txt_custom_proxies.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def _cmd_test_proxies(self):
        logging.info("ProxyScrape v4 manzilidan proxylar o'qilmoqda...")
        url = self.ent_proxy_url.get().strip()
        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(proxy_manager.initialize())
            proxies = proxy_manager.proxies
            logging.info(f"✓ Sinov yakunlandi. Tayyor proxylar: {len(proxies)} ta")
        threading.Thread(target=_run, daemon=True).start()

    # ── TAB 4: JITTER & OPTIMIZATION ──────────────────────────────────────────
    def _build_tab_jitter(self):
        tab = self.tab_jitter

        box = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        box.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(box, text="⚡ Human Jitter & Resurs Optimallash", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(15, 10))

        # Toggles
        self.var_block_video = ctk.CTkCheckBox(box, text="RAM/CPU 80% Tejash (googlevideo.com ni bloklash)")
        self.var_block_video.pack(anchor="w", padx=20, pady=6)

        self.var_silence_breaker = ctk.CTkCheckBox(box, text="Silence Breaker (Chat jimjit bo'lganda suhbatni jonlantirish)")
        self.var_silence_breaker.pack(anchor="w", padx=20, pady=6)

        self.var_reactions = ctk.CTkCheckBox(box, text="Auto Reaction/Emojis (Efirga emojilar bosib turish)")
        self.var_reactions.pack(anchor="w", padx=20, pady=6)

        # Jitter Sliders
        lbl_j1 = ctk.CTkLabel(box, text="⏱ Minimum Javob Kutish Kechikishi (Sekund):", font=ctk.CTkFont(size=13))
        lbl_j1.pack(anchor="w", padx=20, pady=(12, 2))
        self.slider_min_delay = ctk.CTkSlider(box, from_=3, to=30, number_of_steps=27)
        self.slider_min_delay.pack(fill="x", padx=20, pady=4)
        self.slider_min_delay.set(7)

        lbl_j2 = ctk.CTkLabel(box, text="⏱ Maksimum Javob Kutish Kechikishi (Sekund):", font=ctk.CTkFont(size=13))
        lbl_j2.pack(anchor="w", padx=20, pady=(10, 2))
        self.slider_max_delay = ctk.CTkSlider(box, from_=10, to=60, number_of_steps=50)
        self.slider_max_delay.pack(fill="x", padx=20, pady=4)
        self.slider_max_delay.set(16)

    # ── TAB 5: PRESETS ────────────────────────────────────────────────────────
    def _build_tab_presets(self):
        tab = self.tab_presets

        box = ctk.CTkFrame(tab, fg_color="#252538", corner_radius=10)
        box.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(box, text="📁 Presets — Sozlamalarni Saqlash va Boshqarish", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(15, 10))

        p_frame = ctk.CTkFrame(box, fg_color="transparent")
        p_frame.pack(fill="x", padx=20, pady=10)

        self.preset_menu = ctk.CTkOptionMenu(
            p_frame,
            values=presets_manager.list_presets(),
            command=self._on_preset_selected
        )
        self.preset_menu.pack(side="left", padx=(0, 10), fill="x", expand=True)

        btn_load = ctk.CTkButton(p_frame, text="📂 Yuklash", width=90, command=self._cmd_load_preset)
        btn_load.pack(side="left", padx=4)

        btn_save = ctk.CTkButton(p_frame, text="💾 Saqlash", width=90, fg_color="#A6E3A1", text_color="#11111B", command=self._cmd_save_preset)
        btn_save.pack(side="left", padx=4)

    # ── PRESET LOGIC ──────────────────────────────────────────────────────────
    def _on_preset_selected(self, preset_name: str):
        self._load_preset_to_ui(preset_name)

    def _cmd_load_preset(self):
        name = self.preset_menu.get()
        self._load_preset_to_ui(name)
        logging.info(f"Preset '{name}' yuklandi.")

    def _cmd_save_preset(self):
        name = self.preset_menu.get()
        data = self._gather_ui_config()
        data["preset_name"] = name
        if presets_manager.save_preset(name, data):
            logging.info(f"Preset '{name}' saqlandi!")
            self.preset_menu.configure(values=presets_manager.list_presets())

    def _load_preset_to_ui(self, name: str):
        data = presets_manager.load_preset(name)

        self.ent_channel_url.delete(0, "end")
        self.ent_channel_url.insert(0, data.get("target_channel_url", ""))

        if data.get("auto_resolve_channel_live", True):
            self.var_auto_resolve.select()
        else:
            self.var_auto_resolve.deselect()

        self.ent_stream_url.delete(0, "end")
        self.ent_stream_url.insert(0, data.get("target_youtube_url", ""))

        if data.get("enable_proxies", False):
            self.var_enable_proxies.select()
        else:
            self.var_enable_proxies.deselect()

        self.ent_proxy_url.delete(0, "end")
        self.ent_proxy_url.insert(0, data.get("proxy_api_url", DEFAULT_PROXYSCRAPE_URL))

        # Profiles
        selected_profs = data.get("selected_profiles", ["Profile 1", "Profile 2"])
        for pid, chk_var in self.profile_checkboxes.items():
            chk_var.set(pid in selected_profs)

        # Toggles
        if data.get("block_video_streams", True):
            self.var_block_video.select()
        else:
            self.var_block_video.deselect()

        if data.get("enable_silence_breaker", True):
            self.var_silence_breaker.select()
        else:
            self.var_silence_breaker.deselect()

        if data.get("enable_auto_reactions", True):
            self.var_reactions.select()
        else:
            self.var_reactions.deselect()

        # System Prompts
        self.current_prompts = data.get("profile_prompts", {})
        self._on_prompt_profile_changed(self.prompt_profile_menu.get())

    def _on_prompt_profile_changed(self, pid: str):
        prompt = self.current_prompts.get(pid, config.DEFAULT_SYSTEM_PROMPT)
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", prompt)

    def _gather_ui_config(self) -> dict:
        selected_profiles = [pid for pid, var in self.profile_checkboxes.items() if var.get()]
        active_pid = self.prompt_profile_menu.get()
        if active_pid:
            self.current_prompts[active_pid] = self.txt_prompt.get("1.0", "end-1c")

        return {
            "target_channel_url": self.ent_channel_url.get().strip(),
            "auto_resolve_channel_live": bool(self.var_auto_resolve.get()),
            "target_youtube_url": self.ent_stream_url.get().strip(),
            "enable_proxies": bool(self.var_enable_proxies.get()),
            "proxy_api_url": self.ent_proxy_url.get().strip(),
            "selected_profiles": selected_profiles,
            "block_video_streams": bool(self.var_block_video.get()),
            "enable_silence_breaker": bool(self.var_silence_breaker.get()),
            "enable_auto_reactions": bool(self.var_reactions.get()),
            "profile_prompts": self.current_prompts,
            "min_reply_delay": int(self.slider_min_delay.get()),
            "max_reply_delay": int(self.slider_max_delay.get())
        }

    # ── BOT CONTROL LOGIC ─────────────────────────────────────────────────────
    def start_bot(self):
        if self.is_running:
            return

        ui_data = self._gather_ui_config()

        # Config.py qiymatlarini yangilash
        config.TARGET_CHANNEL_URL = ui_data["target_channel_url"]
        config.AUTO_RESOLVE_CHANNEL_LIVE = ui_data["auto_resolve_channel_live"]
        if ui_data["target_youtube_url"]:
            config.TARGET_YOUTUBE_URL = ui_data["target_youtube_url"]
        config.ENABLE_PROXIES = ui_data["enable_proxies"]
        config.YOUTUBE_PROFILES = ui_data["selected_profiles"]
        config.BLOCK_VIDEO_STREAMS = ui_data["block_video_streams"]
        config.ENABLE_SILENCE_BREAKER = ui_data["enable_silence_breaker"]
        config.ENABLE_AUTO_REACTIONS = ui_data["enable_auto_reactions"]
        config.PROFILE_SYSTEM_PROMPTS = ui_data["profile_prompts"]
        config.MIN_REPLY_DELAY = ui_data["min_reply_delay"]
        config.MAX_REPLY_DELAY = ui_data["max_reply_delay"]

        if not config.YOUTUBE_PROFILES:
            logging.error("Kamida 1 ta Chrome profili tanlanishi shart!")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_badge.configure(text="STATUS: RUNNING 🟢", text_color="#A6E3A1")

        logging.info(f"Botlar ishga tushirilmoqda... Tanlangan profillar: {config.YOUTUBE_PROFILES}")

        # Dynamic Chrome launch upon GUI Start click
        self.bot_thread = threading.Thread(target=self._run_async_bot, daemon=True)
        self.bot_thread.start()

    def _run_async_bot(self):
        logging.info("Chrome brauzer CDP port 9333 va tanlangan profillar ishga tushirilmoqda...")
        success = launch_chrome_profiles(config.YOUTUBE_PROFILES, port=9333)
        if not success:
            logging.error("Chrome ni ishga tushirishda xato yuz berdi!")
            self.after(0, self._on_bot_stopped)
            return

        from main import main, shutdown_event
        shutdown_event.clear()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(main())
        except Exception as e:
            logging.error(f"Bot jarayonida xato: {e}")
        finally:
            self.is_running = False
            self.after(0, self._on_bot_stopped)

    def stop_bot(self):
        if not self.is_running:
            return

        logging.info("Botlarni to'xtatish so'rovi yuborildi...")
        from main import shutdown_event
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(shutdown_event.set)

    def _on_bot_stopped(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_badge.configure(text="STATUS: STOPPED 🔴", text_color="#F38BA8")
        logging.info("Botlar to'liq to'xtatildi. 🛑")

if __name__ == "__main__":
    app = App()
    app.mainloop()
