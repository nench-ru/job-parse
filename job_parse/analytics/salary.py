import statistics
from typing import Optional

import pandas as pd

from job_parse.storage.db import Database
from job_parse.models.vacancy import Vacancy


class SalaryAnalyzer:
    def __init__(self, db: Database):
        self.db = db

    def _vacancies_with_salary(self, vacancies: list[Vacancy]) -> list[Vacancy]:
        return [v for v in vacancies if v.salary_min is not None or v.salary_max is not None]

    def salary_by_skill(self, skill: str) -> dict:
        vacancies = self.db.get_all_vacancies()
        with_skill = [v for v in vacancies if skill in v.skills]
        with_salary = self._vacancies_with_salary(with_skill)

        salaries = []
        for v in with_salary:
            if v.salary_min and v.salary_max:
                salaries.append((v.salary_min + v.salary_max) / 2)
            elif v.salary_min:
                salaries.append(v.salary_min)
            elif v.salary_max:
                salaries.append(v.salary_max)

        if not salaries:
            return {"skill": skill, "count": 0, "avg": None, "median": None, "min": None, "max": None}

        return {
            "skill": skill,
            "count": len(salaries),
            "avg": round(statistics.mean(salaries)),
            "median": round(statistics.median(salaries)),
            "min": min(salaries),
            "max": max(salaries),
        }

    def salary_by_city(self) -> pd.DataFrame:
        vacancies = self.db.get_all_vacancies()
        with_salary = self._vacancies_with_salary(vacancies)

        city_data: dict[str, list[float]] = {}
        for v in with_salary:
            if not v.city:
                continue
            avg = 0
            if v.salary_min and v.salary_max:
                avg = (v.salary_min + v.salary_max) / 2
            elif v.salary_min:
                avg = v.salary_min
            elif v.salary_max:
                avg = v.salary_max
            city_data.setdefault(v.city, []).append(avg)

        rows = []
        for city, vals in city_data.items():
            rows.append({
                "city": city,
                "count": len(vals),
                "avg": round(statistics.mean(vals)),
                "median": round(statistics.median(vals)),
                "min": round(min(vals)),
                "max": round(max(vals)),
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("count", ascending=False).reset_index(drop=True)
        return df

    def salary_by_source(self) -> pd.DataFrame:
        data = []
        for source in ("hh", "habr"):
            vacancies = self.db.get_vacancies_by_source(source)
            with_salary = self._vacancies_with_salary(vacancies)
            salaries = []
            for v in with_salary:
                if v.salary_min and v.salary_max:
                    avg = (v.salary_min + v.salary_max) / 2
                elif v.salary_min:
                    avg = v.salary_min
                elif v.salary_max:
                    avg = v.salary_max
                else:
                    continue
                salaries.append(avg)

            if salaries:
                data.append({
                    "source": source,
                    "count": len(salaries),
                    "avg": round(statistics.mean(salaries)),
                    "median": round(statistics.median(salaries)),
                    "min": round(min(salaries)),
                    "max": round(max(salaries)),
                })
        return pd.DataFrame(data)

    def salary_overview(self) -> pd.DataFrame:
        vacancies = self.db.get_all_vacancies()
        with_salary = self._vacancies_with_salary(vacancies)

        salaries = []
        for v in with_salary:
            if v.salary_min and v.salary_max:
                salaries.append((v.salary_min + v.salary_max) / 2)
            elif v.salary_min:
                salaries.append(v.salary_min)
            elif v.salary_max:
                salaries.append(v.salary_max)

        if not salaries:
            return pd.DataFrame()

        return pd.DataFrame([{
            "total_vacancies": len(vacancies),
            "with_salary": len(salaries),
            "avg": round(statistics.mean(salaries)),
            "median": round(statistics.median(salaries)),
            "min": round(min(salaries)),
            "max": round(max(salaries)),
            "std": round(statistics.stdev(salaries)) if len(salaries) > 1 else 0,
        }])
