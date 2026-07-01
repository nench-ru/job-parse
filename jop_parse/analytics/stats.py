from collections import Counter
from typing import Optional

import pandas as pd

from jop_parse.storage.db import Database


class StatsAnalyzer:
    def __init__(self, db: Database):
        self.db = db

    def top_skills(self, top_n: int = 20) -> list[tuple[str, int]]:
        vacancies = self.db.get_all_vacancies()
        skill_counter: Counter = Counter()
        for v in vacancies:
            for skill in v.skills:
                skill_counter[skill] += 1
        return skill_counter.most_common(top_n)

    def skills_by_source(self, top_n: int = 20) -> dict[str, list[tuple[str, int]]]:
        result = {}
        for source in ("hh", "habr"):
            vacancies = self.db.get_vacancies_by_source(source)
            skill_counter: Counter = Counter()
            for v in vacancies:
                for skill in v.skills:
                    skill_counter[skill] += 1
            result[source] = skill_counter.most_common(top_n)
        return result

    def city_distribution(self) -> list[tuple[str, int]]:
        vacancies = self.db.get_all_vacancies()
        city_counter: Counter = Counter()
        for v in vacancies:
            if v.city:
                city_counter[v.city] += 1
        return city_counter.most_common()

    def source_distribution(self) -> dict[str, int]:
        return self.db.get_vacancies_count()

    def skills_dataframe(self, top_n: int = 20) -> pd.DataFrame:
        top = self.top_skills(top_n)
        df = pd.DataFrame(top, columns=["skill", "count"])
        df["frequency"] = (df["count"] / df["count"].sum() * 100).round(1)
        return df

    def vacancies_by_skill(self, skill: str) -> list:
        vacancies = self.db.get_all_vacancies()
        return [v for v in vacancies if skill in v.skills]
