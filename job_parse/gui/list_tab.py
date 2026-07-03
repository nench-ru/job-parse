import threading

import customtkinter as ctk

from job_parse.config.settings import DB_PATH
from job_parse.storage.db import Database
from job_parse.gui.settings_store import save_config


SOURCE_CHOICES = ["all", "hh", "habr", "superjob", "geekjob", "rabota", "trudvsem"]


class ListTab(ctk.CTkFrame):
    def __init__(self, master: any, config: dict):
        super().__init__(master)
        self.config = config
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="База данных вакансий", font=("", 16, "bold")).grid(
            row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w"
        )

        row = 1
        controls = ctk.CTkFrame(self)
        controls.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls, text="Источник:").grid(row=0, column=0, padx=5, pady=5)
        self.source_var = ctk.StringVar(value=self.config.get("list_source", "all"))
        source_menu = ctk.CTkOptionMenu(controls, values=SOURCE_CHOICES, variable=self.source_var)
        source_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(controls, text="Лимит:").grid(row=0, column=2, padx=5, pady=5)
        self.limit_var = ctk.StringVar(value=str(self.config.get("list_limit", 20)))
        limit_entry = ctk.CTkEntry(controls, textvariable=self.limit_var, width=60)
        limit_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.refresh_btn = ctk.CTkButton(controls, text="🔄 Обновить", command=self._refresh)
        self.refresh_btn.grid(row=0, column=4, padx=10, pady=5)

        self.info_label = ctk.CTkLabel(controls, text="")
        self.info_label.grid(row=0, column=5, padx=5, pady=5)

        row += 1
        ctk.CTkLabel(self, text="Таблица:", anchor="w").grid(
            row=row, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="w"
        )

        row += 1
        self.table_text = ctk.CTkTextbox(self, wrap="none")
        self.table_text.grid(row=row, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

        self._refresh()

    def _refresh(self):
        self.config["list_source"] = self.source_var.get()
        self.config["list_limit"] = int(self.limit_var.get() or 20)
        save_config(self.config)

        self.refresh_btn.configure(state="disabled")
        self.table_text.delete("0.0", "end")
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            with Database(DB_PATH) as db:
                source = self.source_var.get()
                limit = int(self.limit_var.get() or 20)

                if source == "all":
                    vacancies = db.get_all_vacancies()
                else:
                    vacancies = db.get_vacancies_by_source(source)

                count = len(vacancies)
                vacancies = vacancies[:limit]

                if not vacancies:
                    self._show_data("Нет вакансий в базе. Выполните парсинг.", count)
                    return

                header = f"{'#':<4} {'Источник':<10} {'Должность':<40} {'Компания':<25} {'Город':<20} {'Зарплата':<20} Навыки"
                sep = "-" * len(header)
                lines = [header, sep]

                for i, v in enumerate(vacancies, 1):
                    salary = ""
                    if v.salary_min and v.salary_max:
                        salary = f"{v.salary_min:,}-{v.salary_max:,}₽"
                    elif v.salary_min:
                        salary = f"от {v.salary_min:,}₽"
                    elif v.salary_max:
                        salary = f"до {v.salary_max:,}₽"
                    else:
                        salary = "н/у"

                    skills = ", ".join(v.skills[:3]) if v.skills else ""
                    if len(v.skills) > 3:
                        skills += "..."

                    lines.append(
                        f"{i:<4} {v.source:<10} {v.title[:38]:<40} {v.company[:23]:<25} "
                        f"{v.city[:18]:<20} {salary:<20} {skills[:30]}"
                    )

                self._show_data("\n".join(lines), count)

        except Exception as e:
            self._show_data(f"Ошибка загрузки данных: {e}", 0)

    def _show_data(self, text: str, count: int = 0):
        def update():
            self.table_text.delete("0.0", "end")
            self.table_text.insert("0.0", text)
            self.info_label.configure(text=f"Всего: {count}")
            self.refresh_btn.configure(state="normal")
        self.after(0, update)
