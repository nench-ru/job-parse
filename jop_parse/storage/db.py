import sqlite3
import json
from pathlib import Path
from typing import Optional

from jop_parse.config.settings import DB_PATH
from jop_parse.models.vacancy import Vacancy


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        self._init_db()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source          TEXT    NOT NULL,
                url             TEXT    UNIQUE NOT NULL,
                title           TEXT,
                company         TEXT,
                city            TEXT,
                salary_min      INTEGER,
                salary_max      INTEGER,
                salary_currency TEXT,
                description     TEXT,
                skills          TEXT,
                parsed_at       TEXT
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vacancies_source
            ON vacancies(source)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vacancies_city
            ON vacancies(city)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vacancies_url
            ON vacancies(url)
        """)
        self.conn.commit()

    def url_exists(self, url: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM vacancies WHERE url = ? LIMIT 1", (url,)
        )
        return cursor.fetchone() is not None

    def insert_vacancy(self, vacancy: Vacancy) -> bool:
        if self.url_exists(vacancy.url):
            return False
        skills_json = json.dumps(vacancy.skills, ensure_ascii=False)
        self.conn.execute("""
            INSERT INTO vacancies (source, url, title, company, city,
                                   salary_min, salary_max, salary_currency,
                                   description, skills, parsed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy.source, vacancy.url, vacancy.title, vacancy.company,
            vacancy.city, vacancy.salary_min, vacancy.salary_max,
            vacancy.salary_currency, vacancy.description, skills_json,
            vacancy.parsed_at,
        ))
        self.conn.commit()
        return True

    def get_all_vacancies(self) -> list[Vacancy]:
        cursor = self.conn.execute("SELECT * FROM vacancies ORDER BY parsed_at DESC")
        return [self._row_to_vacancy(row) for row in cursor.fetchall()]

    def get_vacancies_by_source(self, source: str) -> list[Vacancy]:
        cursor = self.conn.execute(
            "SELECT * FROM vacancies WHERE source = ? ORDER BY parsed_at DESC",
            (source,),
        )
        return [self._row_to_vacancy(row) for row in cursor.fetchall()]

    def get_vacancies_count(self) -> dict[str, int]:
        total = self.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        by_source = self.conn.execute(
            "SELECT source, COUNT(*) FROM vacancies GROUP BY source"
        ).fetchall()
        return {
            "total": total,
            **{row["source"]: row["COUNT(*)"] for row in by_source},
        }

    def _row_to_vacancy(self, row: sqlite3.Row) -> Vacancy:
        skills_raw = row["skills"]
        if skills_raw:
            try:
                skills = json.loads(skills_raw)
            except (json.JSONDecodeError, TypeError):
                skills = []
        else:
            skills = []
        return Vacancy(
            source=row["source"],
            url=row["url"],
            title=row["title"] or "",
            company=row["company"] or "",
            city=row["city"] or "",
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_currency=row["salary_currency"],
            description=row["description"] or "",
            skills=skills,
            parsed_at=row["parsed_at"] or "",
        )
