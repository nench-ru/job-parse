from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from loguru import logger

from jop_parse.config.settings import HABR_SEARCH_URL, CONSECUTIVE_ERROR_LIMIT
from jop_parse.models.vacancy import Vacancy
from jop_parse.parsers.base import BaseParser
from jop_parse.storage.db import Database


class HabrParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = "habr"
        self.db: Optional[Database] = None

    def set_db(self, db: Database):
        self.db = db

    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        parsed_count = 0
        params = f"?q={query}&type=all"
        if city:
            params += f"&city={city}"

        for page in range(pages):
            url = f"{HABR_SEARCH_URL}{params}&page={page + 1}"
            logger.info(f"Парсинг страницы {page + 1}/{pages}: {url}")

            try:
                self.driver.get(url)
                self.random_delay(3, 6)

                if self.handle_captcha():
                    continue

                if self.consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                    logger.warning("Слишком много ошибок, перезапуск драйвера...")
                    self.restart_driver()
                    self.driver.get(url)
                    self.random_delay(3, 5)

                soup = BeautifulSoup(self.driver.page_source, "lxml")
                cards = self._extract_cards_from_search(soup)

                if not cards:
                    logger.warning(f"Нет вакансий на странице {page + 1}")
                    break

                for card in cards:
                    try:
                        if self._parse_card(card):
                            parsed_count += 1
                        self.random_delay(2, 5)
                    except Exception as e:
                        logger.error(f"Ошибка парсинга карточки: {e}")
                        self.consecutive_errors += 1

                    if limit > 0 and parsed_count >= limit:
                        logger.info(f"Достигнут лимит {limit} вакансий")
                        break

                self.consecutive_errors = 0
                if limit > 0 and parsed_count >= limit:
                    break

            except TimeoutException:
                logger.error(f"Таймаут загрузки страницы {page + 1} (>60 сек)")
                self.consecutive_errors += 1
                if self.consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                    logger.error("Слишком много таймаутов подряд. Завершение парсинга.")
                    break
                continue
            except Exception as e:
                logger.error(f"Ошибка на странице {page + 1}: {e}")
                self.consecutive_errors += 1
                continue

        logger.info(f"Парсинг Habr завершён. Добавлено вакансий: {parsed_count}")
        return parsed_count

    def _extract_cards_from_search(self, soup: BeautifulSoup) -> list[dict]:
        cards = []

        selectors = [
            'div.vacancy-card',
            'div[class*="vacancy"]',
            'div.section-group',
            'article',
        ]

        elements = []
        for sel in selectors:
            elements = soup.select(sel)
            if elements:
                break

        if not elements:
            logger.warning("Не найдены карточки вакансий на странице поиска Habr")
            return []

        for el in elements:
            link_tag = el.select_one('a[class*="title"]') or el.select_one('a[class*="vacancy"]') or el.select_one('a[href*="/vacancies/"]')
            if not link_tag:
                continue

            url = link_tag.get("href", "")
            if url and not url.startswith("http"):
                url = f"https://career.habr.com{url}"

            title = link_tag.get_text(strip=True)

            company_tag = el.select_one('div[class*="company"]') or el.select_one('a[class*="company"]')
            company = company_tag.get_text(strip=True) if company_tag else ""

            city_tag = el.select_one('div[class*="location"]') or el.select_one('span[class*="city"]')
            city_text = city_tag.get_text(strip=True) if city_tag else ""

            salary_tag = el.select_one('div[class*="salary"]') or el.select_one('span[class*="salary"]') or el.select_one('div[class*="price"]')
            salary_text = salary_tag.get_text(strip=True) if salary_tag else ""

            salary_min, salary_max, salary_currency = self.parse_salary(salary_text)

            cards.append({
                "url": url,
                "title": title,
                "company": company,
                "city": city_text,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "salary_text": salary_text,
            })

        logger.info(f"Найдено {len(cards)} карточек на странице Habr")
        return cards

    def _parse_card(self, card: dict) -> bool:
        if not card["url"]:
            return False

        if self.db and self.db.url_exists(card["url"]):
            logger.debug(f"Вакансия уже есть в БД: {card['title']}")
            return False

        detail = self.parse_vacancy_detail(card["url"])
        if not detail:
            return False

        vacancy = Vacancy(
            source=self.source,
            url=card["url"],
            title=card["title"],
            company=card["company"],
            city=card["city"],
            salary_min=card["salary_min"],
            salary_max=card["salary_max"],
            salary_currency=card["salary_currency"],
            description=detail.get("description", ""),
            skills=detail.get("skills", []),
        )

        if self.db:
            self.db.insert_vacancy(vacancy)
            logger.info(f"Добавлена вакансия: {vacancy.title} ({vacancy.company})")
            return True

        return False

    def parse_vacancy_detail(self, url: str) -> Optional[dict]:
        try:
            self.driver.get(url)
            self.random_delay(2, 4)

            if self.handle_captcha():
                return None

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            soup = BeautifulSoup(self.driver.page_source, "lxml")

            desc_selectors = [
                'div[class*="description"]',
                'div.vacancy-description',
                'div[class*="vacancy"] section',
                'div.section',
            ]
            description = ""
            for sel in desc_selectors:
                desc_tag = soup.select_one(sel)
                if desc_tag:
                    description = desc_tag.get_text(separator="\n", strip=True)
                    break

            skills_container = soup.select_one('div[class*="skills"]') or soup.select_one('div.tags')
            skills = []
            if skills_container:
                skill_tags = skills_container.select('span[class*="tag"]') or skills_container.select('a[class*="tag"]')
                skills = [st.get_text(strip=True).lower() for st in skill_tags if st.get_text(strip=True)]

            text_skills = self.extract_skills(description) if description else []
            all_skills = list(set(skills + text_skills))

            return {
                "description": description,
                "skills": all_skills,
            }

        except TimeoutException:
            logger.warning(f"Таймаут загрузки вакансии Habr: {url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки вакансии Habr {url}: {e}")
            return None
