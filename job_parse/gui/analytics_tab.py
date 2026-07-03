import threading

import customtkinter as ctk
from loguru import logger

from job_parse.config.settings import DB_PATH
from job_parse.storage.db import Database
from job_parse.analytics.stats import StatsAnalyzer
from job_parse.analytics.salary import SalaryAnalyzer
from job_parse.gui.log_console import LogRedirector


class AnalyticsTab(ctk.CTkFrame):
    def __init__(self, master: any, config: dict):
        super().__init__(master)
        self.config = config
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text="Аналитика", font=("", 16, "bold")).grid(
            row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w"
        )

        row = 1
        frame = ctk.CTkFrame(self)
        frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)

        ctk.CTkButton(frame, text="📊 Топ навыков (20)", command=lambda: self._run_stats("skills", 20)).grid(
            row=0, column=0, padx=5, pady=5
        )
        ctk.CTkButton(frame, text="📊 Топ навыков (50)", command=lambda: self._run_stats("skills", 50)).grid(
            row=0, column=1, padx=5, pady=5
        )
        ctk.CTkButton(frame, text="💰 Общая ЗП", command=lambda: self._run_stats("salary_overview")).grid(
            row=0, column=2, padx=5, pady=5
        )
        ctk.CTkButton(frame, text="🏙 ЗП по городам", command=lambda: self._run_stats("salary_city")).grid(
            row=0, column=3, padx=5, pady=5
        )

        row += 1
        skill_frame = ctk.CTkFrame(self)
        skill_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        skill_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(skill_frame, text="Навык:").grid(row=0, column=0, padx=5, pady=5)
        self.skill_entry = ctk.CTkEntry(skill_frame, placeholder_text="Например: Python")
        self.skill_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(skill_frame, text="🔍 Анализ навыка", command=lambda: self._run_stats("skill_detail")).grid(
            row=0, column=2, padx=5, pady=5
        )
        ctk.CTkButton(skill_frame, text="💰 ЗП по навыку", command=lambda: self._run_stats("salary_skill")).grid(
            row=0, column=3, padx=5, pady=5
        )

        row += 1
        ctk.CTkLabel(self, text="Результат:", anchor="w").grid(
            row=row, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="w"
        )

        row += 1
        self.result_text = ctk.CTkTextbox(self, wrap="word")
        self.result_text.grid(row=row, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

    def _run_stats(self, action: str, top_n: int = 20):
        self.result_text.delete("0.0", "end")
        threading.Thread(target=self._do_stats, args=(action, top_n), daemon=True).start()

    def _do_stats(self, action: str, top_n: int):
        try:
            with Database(DB_PATH) as db:
                stats = StatsAnalyzer(db)
                salary = SalaryAnalyzer(db)

                if action == "skills":
                    items = stats.top_skills(top_n)
                    if not items:
                        self._show_result("Нет данных о навыках.")
                        return
                    lines = [f"Топ-{top_n} навыков:\n"]
                    total = sum(c for _, c in items)
                    for i, (skill, count) in enumerate(items, 1):
                        pct = count / total * 100 if total else 0
                        lines.append(f"  {i:2d}. {skill:20s}  {count:4d}  ({pct:.1f}%)")
                    self._show_result("\n".join(lines))

                elif action == "salary_overview":
                    df = salary.salary_overview()
                    if df.empty:
                        self._show_result("Нет данных о зарплатах.")
                        return
                    lines = ["Общая статистика зарплат:\n"]
                    for col in df.columns:
                        val = df.iloc[0][col]
                        if isinstance(val, (int, float)):
                            lines.append(f"  {col}: {val:,.0f}")
                        else:
                            lines.append(f"  {col}: {val}")
                    self._show_result("\n".join(lines))

                elif action == "salary_city":
                    df = salary.salary_by_city()
                    if df.empty:
                        self._show_result("Нет данных о зарплатах по городам.")
                        return
                    lines = ["Зарплаты по городам:\n"]
                    for _, row in df.iterrows():
                        lines.append(
                            f"  {row['city']:20s}  n={row['count']:3d}  "
                            f"средняя={row['avg']:>8,}  мед={row['median']:>8,}"
                        )
                    self._show_result("\n".join(lines))

                elif action == "skill_detail":
                    skill = self.skill_entry.get().strip()
                    if not skill:
                        self._show_result("Введите название навыка.")
                        return
                    items = stats.top_skills(200)
                    found = [(s, c) for s, c in items if skill.lower() in s.lower()]
                    if not found:
                        self._show_result(f"Навык '{skill}' не найден.")
                        return
                    lines = [f"Навыки по запросу '{skill}':\n"]
                    for s, c in found:
                        lines.append(f"  {s}: {c}")
                    self._show_result("\n".join(lines))

                elif action == "salary_skill":
                    skill = self.skill_entry.get().strip()
                    if not skill:
                        self._show_result("Введите название навыка.")
                        return
                    data = salary.salary_by_skill(skill)
                    if data["count"] == 0:
                        self._show_result(f"Нет данных о зарплате для навыка '{skill}'.")
                        return
                    lines = [f"Зарплата для навыка '{skill}':\n"]
                    lines.append(f"  Вакансий с ЗП: {data['count']}")
                    lines.append(f"  Средняя:       {data['avg']:>10,} ₽" if data['avg'] else "  Средняя:       —")
                    lines.append(f"  Медианная:     {data['median']:>10,} ₽" if data['median'] else "  Медианная:     —")
                    lines.append(f"  Мин:           {data['min']:>10,} ₽" if data['min'] else "  Мин:           —")
                    lines.append(f"  Макс:          {data['max']:>10,} ₽" if data['max'] else "  Макс:          —")
                    self._show_result("\n".join(lines))

        except Exception as e:
            self._show_result(f"Ошибка: {e}")

    def _show_result(self, text: str):
        def update():
            self.result_text.delete("0.0", "end")
            self.result_text.insert("0.0", text)
        self.after(0, update)
