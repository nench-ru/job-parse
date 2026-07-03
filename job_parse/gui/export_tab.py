import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from job_parse.config.settings import DB_PATH
from job_parse.storage.db import Database
from job_parse.export.exporter import Exporter
from job_parse.gui.settings_store import save_config


class ExportTab(ctk.CTkFrame):
    def __init__(self, master: any, config: dict):
        super().__init__(master)
        self.config = config
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=0)

        ctk.CTkLabel(self, text="Экспорт данных", font=("", 16, "bold")).grid(
            row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w"
        )

        row = 1
        format_frame = ctk.CTkFrame(self)
        format_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        format_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(format_frame, text="Формат:").grid(row=0, column=0, padx=5, pady=5)
        self.format_var = ctk.StringVar(value=self.config.get("export_format", "excel"))
        ctk.CTkRadioButton(format_frame, text="Excel (.xlsx)", variable=self.format_var, value="excel").grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )
        ctk.CTkRadioButton(format_frame, text="CSV (.csv)", variable=self.format_var, value="csv").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )

        row += 1
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(path_frame, text="Файл:").grid(row=0, column=0, padx=5, pady=5)
        self.path_var = ctk.StringVar(value=self.config.get("export_path", "report.xlsx"))
        self.path_entry = ctk.CTkEntry(path_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(path_frame, text="Обзор", width=70, command=self._browse_path).grid(
            row=0, column=2, padx=5, pady=5
        )

        row += 1
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        self.export_btn = ctk.CTkButton(status_frame, text="📥 Экспорт", command=self._start_export)
        self.export_btn.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(status_frame, text="")
        self.status_label.pack(side="left", padx=10)

        row += 1
        ctk.CTkLabel(self, text="Последний экспорт:", anchor="w").grid(
            row=row, column=0, columnspan=3, padx=10, pady=(10, 0), sticky="w"
        )

        row += 1
        self.log_text = ctk.CTkTextbox(self, wrap="word", height=200)
        self.log_text.grid(row=row, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

    def _browse_path(self):
        fmt = self.format_var.get()
        if fmt == "excel":
            default_ext = ".xlsx"
            filetypes = [("Excel files", "*.xlsx")]
        else:
            default_ext = ".csv"
            filetypes = [("CSV files", "*.csv")]

        path = filedialog.asksaveasfilename(
            title="Сохранить как",
            defaultextension=default_ext,
            filetypes=filetypes,
        )
        if path:
            self.path_var.set(path)

    def _start_export(self):
        self.config["export_format"] = self.format_var.get()
        self.config["export_path"] = self.path_var.get()
        save_config(self.config)

        self.export_btn.configure(state="disabled")
        self.status_label.configure(text="Экспорт...")
        self.log_text.delete("0.0", "end")
        threading.Thread(target=self._do_export, daemon=True).start()

    def _do_export(self):
        try:
            fmt = self.format_var.get()
            path = Path(self.path_var.get())

            with Database(DB_PATH) as db:
                exporter = Exporter(db)
                vacancies = db.get_all_vacancies()
                if not vacancies:
                    self._log("Нет данных для экспорта. Сначала выполните парсинг.")
                    self._finish(False)
                    return

                if fmt == "csv":
                    result = exporter.to_csv(path)
                    self._log(f"CSV экспорт завершён: {result}")
                else:
                    result = exporter.to_excel(path)
                    self._log(f"Excel экспорт завершён: {result}")

                self._log(f"Всего вакансий: {len(vacancies)}")
                self._finish(True)

        except Exception as e:
            self._log(f"Ошибка экспорта: {e}")
            self._finish(False)

    def _log(self, msg: str):
        def update():
            self.log_text.insert("end", f"{msg}\n")
            self.log_text.see("end")
        self.after(0, update)

    def _finish(self, success: bool):
        def update():
            self.export_btn.configure(state="normal")
            self.status_label.configure(text="Готово ✓" if success else "Ошибка ✗")
        self.after(0, update)
