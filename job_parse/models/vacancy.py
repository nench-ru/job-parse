from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Vacancy:
    source: str
    url: str
    title: str = ""
    company: str = ""
    city: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    description: str = ""
    skills: list[str] = field(default_factory=list)
    parsed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        data = asdict(self)
        data["skills"] = ",".join(self.skills) if self.skills else ""
        return data

    @staticmethod
    def from_dict(data: dict) -> "Vacancy":
        skills_raw = data.get("skills", "")
        if isinstance(skills_raw, str):
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        else:
            skills = skills_raw or []
        return Vacancy(
            source=data.get("source", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            city=data.get("city", ""),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            salary_currency=data.get("salary_currency"),
            description=data.get("description", ""),
            skills=skills,
            parsed_at=data.get("parsed_at", datetime.now().isoformat()),
        )
