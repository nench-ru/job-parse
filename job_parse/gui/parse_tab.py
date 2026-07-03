import threading
import argparse
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from job_parse.config.settings import CITIES
from job_parse.cli.app import cmd_parse
from job_parse.gui.settings_store import save_config
from job_parse.gui.log_console import LogConsole, LogRedirector
from loguru import logger


SITE_CHOICES = ["all", "hh", "habr", "superjob", "geekjob", "rabota", "trudvsem"]


class ParseTab(ctk.CTkFrame):
    def __init__(self, master: any, config: dict):
        super().__init__(master)
        self.config = config
        self.worker_thread: threading.Thread | None = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        row = 0
        ctk.CTkLabel(self, text="Сайт:", anchor="w").grid(row=row, column=0, padx=10, pady=(10, 2), sticky="w")
        self.site_var = ctk.StringVar(value=self.config.get("site", "all"))
        site_menu = ctk.CTkOptionMenu(self, values=SITE_CHOICES, variable=self.site_var)
        site_menu.grid(row=row, column=1, padx=10, pady=(10, 2), sticky="ew")

        row += 1
        ctk.CTkLabel(self, text="Запрос:", anchor="w").grid(row=row, column=0, padx=10, pady=2, sticky="w")
        self.query_entry = ctk.CTkEntry(self, placeholder_text="Например: Python разработчик")
        self.query_entry.insert(0, self.config.get("query", ""))
        self.query_entry.grid(row=row, column=1, padx=10, pady=2, sticky="ew")

        row += 1
        ctk.CTkLabel(self, text="Город:", anchor="w").grid(row=row, column=0, padx=10, pady=2, sticky="w")
        self.city_var = ctk.StringVar(value=self.config.get("city", ""))
        city_menu = ctk.CTkOptionMenu(self, values=[""] + CITIES, variable=self.city_var)
        city_menu.grid(row=row, column=1, padx=10, pady=2, sticky="ew")

        row += 1
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)
        settings_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(settings_frame, text="Страниц:").grid(row=0, column=0, padx=5, pady=2)
        self.pages_var = ctk.StringVar(value=str(self.config.get("pages", 3)))
        ctk.CTkEntry(settings_frame, textvariable=self.pages_var, width=60).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(settings_frame, text="Лимит:").grid(row=0, column=2, padx=5, pady=2)
        self.limit_var = ctk.StringVar(value=str(self.config.get("limit", 0)))
        ctk.CTkEntry(settings_frame, textvariable=self.limit_var, width=60).grid(row=0, column=3, padx=5, pady=2, sticky="w")

        row += 1
        cb_frame = ctk.CTkFrame(self)
        cb_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=2, sticky="ew")

        self.headless_var = ctk.BooleanVar(value=self.config.get("headless", False))
        ctk.CTkCheckBox(cb_frame, text="Headless (без GUI)", variable=self.headless_var).pack(side="left", padx=5)

        self.no_captcha_var = ctk.BooleanVar(value=self.config.get("no_captcha_check", False))
        ctk.CTkCheckBox(cb_frame, text="Без проверки капчи", variable=self.no_captcha_var).pack(side="left", padx=5)

        row += 1
        proxy_frame = ctk.CTkFrame(self)
        proxy_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        proxy_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(proxy_frame, text="Файл прокси:").grid(row=0, column=0, padx=5, pady=2)
        self.proxy_var = ctk.StringVar(value=self.config.get("proxy_file", ""))
        self.proxy_entry = ctk.CTkEntry(proxy_frame, textvariable=self.proxy_var)
        self.proxy_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(proxy_frame, text="Обзор", width=70, command=self._browse_proxy).grid(row=0, column=2, padx=5, pady=2)

        row += 1
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ Старт", command=self._start_parse)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(btn_frame, text="■ Стоп", command=self._stop_parse, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(btn_frame, text="✕ Очистить лог", command=self._clear_log)
        self.clear_btn.pack(side="right", padx=5)

        row += 1
        ctk.CTkLabel(self, text="Лог:", anchor="w").grid(row=row, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="w")

        row += 1
        self.console = LogConsole(self, wrap="word")
        self.console.grid(row=row, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

    def _browse_proxy(self):
        path = filedialog.askopenfilename(title="Выберите файл с прокси")
        if path:
            self.proxy_var.set(path)

    def _save_config(self):
        self.config["site"] = self.site_var.get()
        self.config["query"] = self.query_entry.get()
        self.config["city"] = self.city_var.get()
        self.config["pages"] = int(self.pages_var.get() or 3)
        self.config["limit"] = int(self.limit_var.get() or 0)
        self.config["headless"] = self.headless_var.get()
        self.config["no_captcha_check"] = self.no_captcha_var.get()
        self.config["proxy_file"] = self.proxy_var.get()
        save_config(self.config)

    def _toggle_ui(self, running: bool):
        state = "disabled" if running else "normal"
        for w in (
            self.site_var, self.query_entry, self.city_var,
            self.pages_var, self.limit_var,
            self.headless_var, self.no_captcha_var, self.proxy_var,
            self.start_btn, self.clear_btn,
        ):
            try:
                if hasattr(w, "configure"):
                    w.configure(state=state)
            except Exception:
                pass
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")

    def _start_parse(self):
        self._save_config()
        self.console.clear()
        self._toggle_ui(True)

        redirector = LogRedirector(self.console)
        logger.add(redirector.emit, level="INFO", format="{message}")

        self.worker_thread = threading.Thread(target=self._run_parse, daemon=True)
        self.worker_thread.start()
        self._monitor_thread()

    def _monitor_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.after(200, self._monitor_thread)
        else:
            self._on_parse_done()

    def _run_parse(self):
        try:
            args = argparse.Namespace(
                site=self.site_var.get(),
                query=self.query_entry.get(),
                city=self.city_var.get(),
                pages=int(self.pages_var.get() or 3),
                limit=int(self.limit_var.get() or 0),
                headless=self.headless_var.get(),
                no_captcha_check=self.no_captcha_var.get(),
                proxy_file=self.proxy_var.get() or None,
                verbose=False,
            )
            cmd_parse(args)
        except SystemExit:
            pass
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}\n{traceback.format_exc()}")

    def _on_parse_done(self):
        self._toggle_ui(False)
        logger.info("✓ Парсинг завершён")

    def _stop_parse(self):
        logger.warning("Парсинг прерван пользователем")
        self.worker_thread = None
        self._on_parse_done()

    def _clear_log(self):
        self.console.clear()
