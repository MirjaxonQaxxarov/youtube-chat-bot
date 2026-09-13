import sys
import os
import json
import logging
import asyncio
import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

# Local imports
from profile_scanner import scan_chrome_profiles
from presets_manager import presets_manager, DEFAULT_PROXYSCRAPE_URL
import config

# Set CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Custom Logging Handler to push logs into GUI text box safely
class CTkLogHandler(logging.Handler):
    def __init__(self, text_widget: ctk.CTkTextbox):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append_text():
            try:
                self.text_widget.configure(state="normal")
                # Add color accents based on log level
                if record.levelno >= logging.ERROR:
                    self.text_widget.insert("end", f"[ERROR] {msg}\n", "error")
                elif record.levelno >= logging.WARNING:
                    self.text_widget.insert("end", f"[WARN]  {msg}\n", "warning")
                else:
                    self.text_widget.insert("end", f"[INFO]  {msg}\n")
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
            except Exception:
                pass
        
        # Schedule update on main UI thread
        if self.text_widget.winfo_exists():
            self.text_widget.after(0, append_text)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Multi-Profile Chat Bot v2.5 — Desktop Control Panel")
        self.geometry("1100x820")
        self.minsize(950, 700)

        self.bot_thread = None
        self.loop = None
        self.is_running = False

        # Scan Chrome Profiles
        self.available_profiles = scan_chrome_profiles()
        self.profile_checkboxes = {}

        self._create_layout()
        self._load_preset_to_ui("default")

    def _create_layout(self):
        # Configure Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── HEADER ────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=10)
        header_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame, 
            text="🤖 YOUTUBE MULTI-PROFILE BOT CONTROL PANEL", 
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
            padx=12,
            pady=6
        )
        self.status_badge.pack(side="right", padx=20, pady=10)

        # ── MAIN CONTENT (LEFT & RIGHT PANELS) ────────────────────────────────
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # ── LEFT PANEL: CONFIG & PRESETS ─────────────────────────────────────
        left_panel = ctk.CTkFrame(content_frame, fg_color="#1E1E2E", corner_radius=10)
        left_panel.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        # 1. Preset Management
        preset_title = ctk.CTkLabel(left_panel, text="📁 Presets (Sozlamalar)", font=ctk.CTkFont(size=15, weight="bold"))
        preset_title.pack(anchor="w", padx=15, pady=(12, 5))

        preset_box = ctk.CTkFrame(left_panel, fg_color="#252538", corner_radius=8)
        preset_box.pack(fill="x", padx=15, pady=5)

        self.preset_menu = ctk.CTkOptionMenu(
            preset_box,
            values=presets_manager.list_presets(),
            command=self._on_preset_selected
        )
        self.preset_menu.pack(side="left", padx=10, pady=8, expand=True, fill="x")

        self.btn_load = ctk.CTkButton(preset_box, text="Yuklash", width=70, command=self._cmd_load_preset)
        self.btn_load.pack(side="left", padx=4, pady=8)

        self.btn_save = ctk.CTkButton(preset_box, text="Saqlash", width=70, fg_color="#A6E3A1", text_color="#11111B", hover_color="#94E2D5", command=self._cmd_save_preset)
        self.btn_save.pack(side="left", padx=4, pady=8)

        # 2. Live Stream & Channel Target
        url_title = ctk.CTkLabel(left_panel, text="📺 YouTube Kanal & Efir Manzili", font=ctk.CTkFont(size=15, weight="bold"))
        url_title.pack(anchor="w", padx=15, pady=(12, 5))

        self.ent_channel_url = ctk.CTkEntry(left_panel, placeholder_text="Kanal Linki (masalan: https://www.youtube.com/@tazkion)")
        self.ent_channel_url.pack(fill="x", padx=15, pady=4)

        self.var_auto_resolve = ctk.CTkCheckBox(left_panel, text="Kanal linkidan avtomatik liveni topish")
        self.var_auto_resolve.pack(anchor="w", padx=15, pady=4)

        self.ent_stream_url = ctk.CTkEntry(left_panel, placeholder_text="To'g'ridan-to'g'ri Live URL (https://www.youtube.com/watch?v=...)")
        self.ent_stream_url.pack(fill="x", padx=15, pady=4)

        # 3. Proxy Settings
        proxy_title = ctk.CTkLabel(left_panel, text="🌐 Proxy Scrape & Beqarorlik Himoyasi", font=ctk.CTkFont(size=15, weight="bold"))
        proxy_title.pack(anchor="w", padx=15, pady=(12, 5))

        self.var_enable_proxies = ctk.CTkCheckBox(left_panel, text="Bepul Proxylarni yoqish (ProxyScrape v4)")
        self.var_enable_proxies.pack(anchor="w", padx=15, pady=4)

        self.ent_proxy_url = ctk.CTkEntry(left_panel, placeholder_text="ProxyScrape API URL...")
        self.ent_proxy_url.pack(fill="x", padx=15, pady=4)

        # ── RIGHT PANEL: PROFILES & PROMPTS ──────────────────────────────────
        right_panel = ctk.CTkFrame(content_frame, fg_color="#1E1E2E", corner_radius=10)
        right_panel.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")

        prof_title = ctk.CTkLabel(right_panel, text="👥 Chrome Profillari va AI System Promptlar", font=ctk.CTkFont(size=15, weight="bold"))
        prof_title.pack(anchor="w", padx=15, pady=(12, 5))

        # Profile checkboxes list frame
        prof_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="#252538", height=150, corner_radius=8)
        prof_scroll.pack(fill="x", padx=15, pady=5)

        for pinfo in self.available_profiles:
            pid = pinfo["id"]
            pname = pinfo["name"]
            var = ctk.BooleanVar(value=(pid in config.YOUTUBE_PROFILES))
            chk = ctk.CTkCheckBox(prof_scroll, text=f"{pid} — {pname}", variable=var)
            chk.pack(anchor="w", padx=10, pady=4)
            self.profile_checkboxes[pid] = var

        # System Prompt Editor
        prompt_label = ctk.CTkLabel(right_panel, text="📝 Tanlangan Profil System Prompti:", font=ctk.CTkFont(size=13, weight="bold"))
        prompt_label.pack(anchor="w", padx=15, pady=(8, 2))

        self.prompt_profile_menu = ctk.CTkOptionMenu(
            right_panel,
            values=[p["id"] for p in self.available_profiles],
            command=self._on_prompt_profile_changed
        )
        self.prompt_profile_menu.pack(anchor="w", padx=15, pady=4)

        self.txt_prompt = ctk.CTkTextbox(right_panel, height=90, corner_radius=8, fg_color="#252538")
        self.txt_prompt.pack(fill="x", padx=15, pady=5)

        # Optimizations & Toggles
        opt_title = ctk.CTkLabel(right_panel, text="⚡ Optimallashtirish va Rejimlar", font=ctk.CTkFont(size=14, weight="bold"))
        opt_title.pack(anchor="w", padx=15, pady=(8, 2))

        opt_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        opt_frame.pack(fill="x", padx=15, pady=2)

        self.var_block_video = ctk.CTkCheckBox(opt_frame, text="RAM/CPU 80% Tejash (Videoni to'xtatish)")
        self.var_block_video.pack(anchor="w", pady=2)

        self.var_silence_breaker = ctk.CTkCheckBox(opt_frame, text="Silence Breaker (Suhbatni jonlantirish)")
        self.var_silence_breaker.pack(anchor="w", pady=2)

        self.var_reactions = ctk.CTkCheckBox(opt_frame, text="Auto Reaction/Emojis (Jonli emojilar)")
        self.var_reactions.pack(anchor="w", pady=2)

        # ── BOTTOM PANEL: ACTION BUTTONS & CONSOLE LOG ────────────────────────
        bottom_frame = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=10)
        bottom_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="nsew")
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_rowconfigure(1, weight=1)

        # Start / Stop Buttons
        btn_box = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_box.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        self.btn_start = ctk.CTkButton(
            btn_box, 
            text="▶ BARCHA BOTLARNI ISHGA TUSHIRISH", 
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#A6E3A1", 
            text_color="#11111B", 
            hover_color="#94E2D5", 
            height=42,
            command=self.start_bot
        )
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_box, 
            text="⏹ TO'XTATISH", 
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#F38BA8", 
            text_color="#11111B", 
            hover_color="#EBA0AC", 
            height=42,
            state="disabled",
            command=self.stop_bot
        )
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=(10, 0))

        # Real-time Console Widget
        self.txt_console = ctk.CTkTextbox(
            bottom_frame, 
            fg_color="#11111B", 
            text_color="#CDD6F4",
            font=ctk.CTkFont(family="Courier", size=12),
            corner_radius=8
        )
        self.txt_console.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")

        # Setup Logging redirection to GUI
        gui_handler = CTkLogHandler(self.txt_console)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s │ %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)

        logging.info("Desktop GUI Interfeysi tayyorlandi ✅")

    # ── PRESET LOGIC ──────────────────────────────────────────────────────────
    def _on_preset_selected(self, preset_name: str):
        self._load_preset_to_ui(preset_name)

    def _cmd_load_preset(self):
        name = self.preset_menu.get()
        self._load_preset_to_ui(name)
        logging.info(f"Preset '{name}' muvaffaqiyatli yuklandi.")

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
            if pid in selected_profs:
                chk_var.set(True)
            else:
                chk_var.set(False)

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
        
        # Save active prompt before gathering
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
            "profile_prompts": self.current_prompts
        }

    # ── BOT CONTROL LOGIC ─────────────────────────────────────────────────────
    def start_bot(self):
        if self.is_running:
            return

        ui_data = self._gather_ui_config()

        # Update config.py values dynamically
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

        if not config.YOUTUBE_PROFILES:
            logging.error("Kamida 1 ta Chrome profili tanlanishi shart!")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_badge.configure(text="STATUS: RUNNING 🟢", text_color="#A6E3A1")

        logging.info(f"Botlar ishga tushirilmoqda... Tanlangan profillar: {config.YOUTUBE_PROFILES}")

        # Run main() in a background asyncio thread
        self.bot_thread = threading.Thread(target=self._run_async_bot, daemon=True)
        self.bot_thread.start()

    def _run_async_bot(self):
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
