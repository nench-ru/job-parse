import sys
import os

import customtkinter as ctk

from job_parse.gui.settings_store import load_config, save_config
from job_parse.gui.parse_tab import ParseTab
from job_parse.gui.analytics_tab import AnalyticsTab
from job_parse.gui.export_tab import ExportTab
from job_parse.gui.list_tab import ListTab


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = load_config()

        self.title("job_parse — Парсер вакансий")
        geometry = self.config.get("window_geometry", "1200x800")
        self.geometry(geometry)
        self.minsize(900, 600)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)

        self.parse_tab = self.tab_view.add("Парсинг")
        self.analytics_tab = self.tab_view.add("Аналитика")
        self.export_tab = self.tab_view.add("Экспорт")
        self.db_tab = self.tab_view.add("База данных")

        self.parse_frame = ParseTab(self.parse_tab, self.config)
        self.parse_frame.pack(fill="both", expand=True)

        self.analytics_frame = AnalyticsTab(self.analytics_tab, self.config)
        self.analytics_frame.pack(fill="both", expand=True)

        self.export_frame = ExportTab(self.export_tab, self.config)
        self.export_frame.pack(fill="both", expand=True)

        self.list_frame = ListTab(self.db_tab, self.config)
        self.list_frame.pack(fill="both", expand=True)

    def _on_close(self):
        geometry = self.geometry()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.winfo_x()
        y = self.winfo_y()
        self.config["window_geometry"] = f"{width}x{height}+{x}+{y}"
        save_config(self.config)
        self.destroy()


def run_gui():
    app = App()
    app.mainloop()
