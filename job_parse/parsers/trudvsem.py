import json
from typing import Optional

import httpx
from loguru import logger

from job_parse.config.settings import TRUDVSEM_API_URL, TRUDVSEM_CITY_OKATO
from job_parse.models.vacancy import Vacancy
from job_parse.storage.db import Database


class TrudvsemParser:
    def __init__(self, **kwargs):
        self.source = "trudvsem"
        self.db: Optional[Database] = None

    def set_db(self, db: Database):
        self.db = db

    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        parsed_count = 0
        client = httpx.Client(timeout=30, verify=False)

        params = {
            "text": query,
            "limit": min(100, limit if limit > 0 else 100),
            "offset": 0,
        }

        if city and city in TRUDVSEM_CITY_OKATO:
            params["region"] = TRUDVSEM_CITY_OKATO[city]

        try:
            logger.info(f"Запрос к Trudvsem API: {params}")
            resp = client.get(TRUDVSEM_API_URL, params=params)
            resp.raise_for_status()

            data = resp.json()
            vacancies_data = self._extract_vacancies(data)

            if not vacancies_data:
                logger.warning("Нет вакансий от Trudvsem API")
                return 0

            for item in vacancies_data:
                if limit > 0 and parsed_count >= limit:
                    break

                try:
                    if self._process_vacancy(item):
                        parsed_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обработки вакансии Trudvsem: {e}")
                    continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP {e.response.status_code} от Trudvsem API")
        except httpx.RequestError as e:
            logger.error(f"Ошибка запроса к Trudvsem API: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON Trudvsem: {e}")
        finally:
            client.close()

        logger.info(f"Парсинг Trudvsem завершён. Добавлено вакансий: {parsed_count}")
        return parsed_count

    def _extract_vacancies(self, data: dict) -> list[dict]:
        results = []
        try:
            meta = data.get("meta", {})
            if not meta.get("total", 0):
                return results

            results_raw = data.get("results", {}).get("vacancies", [])
            if isinstance(results_raw, dict):
                results_raw = [results_raw]

            for item in results_raw:
                vacancy_data = item.get("vacancy", item)
                if vacancy_data.get("id") or vacancy_data.get("url"):
                    results.append(vacancy_data)
        except Exception as e:
            logger.error(f"Ошибка извлечения данных Trudvsem: {e}")

        return results

    def _process_vacancy(self, item: dict) -> bool:
        url = item.get("url", "") or item.get("vac_url", "")
        if not url:
            return False

        if self.db and self.db.url_exists(url):
            logger.debug(f"Вакансия уже есть в БД: {url}")
            return False

        title = item.get("title", "") or item.get("job-name", "") or item.get("name", "")
        company = item.get("company", {})
        if isinstance(company, dict):
            company_name = company.get("name", "")
        else:
            company_name = str(company) if company else ""

        city = ""
        location = item.get("location", {})
        if isinstance(location, dict):
            city = location.get("address", "") or location.get("city", "") or location.get("region", "")
        elif isinstance(location, str):
            city = location

        salary_str = item.get("salary", "")
        salary_min, salary_max, salary_currency = None, None, None
        if salary_str:
            salary_min, salary_max, salary_currency = self._parse_api_salary(salary_str)
        if salary_min is None and salary_max is None:
            salary_min = item.get("salary_min") or item.get("salaryFrom")
            salary_max = item.get("salary_max") or item.get("salaryTo")
            salary_currency = item.get("currency", "RUB")

        description = item.get("description", "") or item.get("vacancy", "") or ""
        requirements = item.get("requirements", "") or item.get("qualification", "") or ""
        full_text = f"{description}\n{requirements}"

        skills = self._extract_skills(full_text)

        vacancy = Vacancy(
            source=self.source,
            url=url,
            title=title,
            company=company_name,
            city=city,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            description=full_text,
            skills=skills,
        )

        if self.db:
            self.db.insert_vacancy(vacancy)
            logger.info(f"Добавлена вакансия: {vacancy.title} ({vacancy.company})")
            return True

        return False

    def _parse_api_salary(self, salary_str) -> tuple:
        if not salary_str:
            return None, None, None
        salary_str = str(salary_str).strip().lower()
        currency = "RUB"
        if "$" in salary_str or "usd" in salary_str:
            currency = "USD"
        elif "€" in salary_str or "eur" in salary_str:
            currency = "EUR"

        import re
        nums = re.findall(r'\d[\d\s]*', salary_str.replace(",", "").replace(".", ""))
        nums = [int(n.replace(" ", "")) for n in nums if n.strip()]

        if len(nums) >= 2:
            return nums[0], nums[1], currency
        elif len(nums) == 1:
            if "от" in salary_str or "from" in salary_str:
                return nums[0], None, currency
            elif "до" in salary_str or "to" in salary_str:
                return None, nums[0], currency
            return nums[0], None, currency

        return None, None, currency

    def _extract_skills(self, text: str) -> list[str]:
        if not text:
            return []
        from job_parse.parsers.base import BaseParser
        return BaseParser.extract_skills(self, text)

    def quit(self):
        pass
