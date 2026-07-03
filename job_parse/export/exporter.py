from pathlib import Path
from typing import Optional

import pandas as pd

from job_parse.storage.db import Database
from job_parse.analytics.stats import StatsAnalyzer
from job_parse.analytics.salary import SalaryAnalyzer


class Exporter:
    def __init__(self, db: Database):
        self.db = db
        self.stats = StatsAnalyzer(db)
        self.salary = SalaryAnalyzer(db)

    def to_csv(self, output_path: Path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        vacancies = self.db.get_all_vacancies()
        if not vacancies:
            raise ValueError("Нет данных для экспорта")

        rows = [v.to_dict() for v in vacancies]
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path

    def to_excel(self, output_path: Path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        vacancies = self.db.get_all_vacancies()
        if not vacancies:
            raise ValueError("Нет данных для экспорта")

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            rows = [v.to_dict() for v in vacancies]
            df_vacancies = pd.DataFrame(rows)
            df_vacancies.to_excel(writer, sheet_name="Вакансии", index=False)

            df_skills = self.stats.skills_dataframe(top_n=50)
            if not df_skills.empty:
                df_skills.to_excel(writer, sheet_name="Топ навыков", index=False)

            df_city_salary = self.salary.salary_by_city()
            if not df_city_salary.empty:
                df_city_salary.to_excel(writer, sheet_name="ЗП по городам", index=False)

            df_overview = self.salary.salary_overview()
            if not df_overview.empty:
                df_overview.to_excel(writer, sheet_name="Общая статистика", index=False)

        return output_path

    def export_skills_csv(self, output_path: Path, top_n: int = 50):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df = self.stats.skills_dataframe(top_n=top_n)
        if df.empty:
            raise ValueError("Нет данных о навыках")
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path
