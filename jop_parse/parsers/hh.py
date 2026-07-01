import os
from datetime import datetime
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from loguru import logger

from jop_parse.config.settings import HH_SEARCH_URL, HH_CITY_IDS, CONSECUTIVE_ERROR_LIMIT, LOGS_DIR
from jop_parse.models.vacancy import Vacancy
from jop_parse.parsers.base import BaseParser
from jop_parse.storage.db import Database


class HHParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = "hh"
        self.db: Optional[Database] = None

    def set_db(self, db: Database):
        self.db = db

    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        parsed_count = 0
        params = f"?text={query}"

        if city and city in HH_CITY_IDS:
            params += f"&area={HH_CITY_IDS[city]}"
        else:
            params += "&area=113"

        for page in range(pages):
            url = f"{HH_SEARCH_URL}{params}&page={page}"
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
                    debug_path = LOGS_DIR / f"hh_debug_page{page + 1}.html"
                    try:
                        with open(debug_path, "w", encoding="utf-8") as f:
                            f.write(self.driver.page_source)
                        logger.info(f"Сохранён HTML страницы: {debug_path}")
                    except Exception:
                        pass
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

        logger.info(f"Парсинг HH завершён. Добавлено вакансий: {parsed_count}")
        return parsed_count

    def _find_vacancy_links(self, soup: BeautifulSoup) -> list[tuple]:
        results = []

        all_links = soup.select('a[href*="/vacancy/"]')
        seen = set()
        for link in all_links:
            href = link.get("href", "")
            if href in seen:
                continue
            seen.add(href)

            container = link
            for _ in range(6):
                parent = container.find_parent()
                if parent is None:
                    break
                container = parent
                if container.name in ("div", "article", "section"):
                    classes = container.get("class", [])
                    class_str = " ".join(classes)
                    if any(kw in class_str.lower() for kw in ["vacancy", "serp", "item", "card", "result"]):
                        break

            results.append((link, container))

        return results

    def _extract_cards_from_search(self, soup: BeautifulSoup) -> list[dict]:
        cards = []
        found_pairs = self._find_vacancy_links(soup)

        if not found_pairs:
            logger.warning("Не найдены ссылки на вакансии на странице поиска")
            return []

        for link_tag, container in found_pairs:
            url = link_tag.get("href", "")
            if not url:
                continue
            if url.startswith("/"):
                url = f"https://hh.ru{url}"

            title = link_tag.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            company = ""
            company_selectors = [
                'a[data-qa*="employer"]',
                'a[data-qa*="company"]',
                'span[data-qa*="company"]',
                'div[data-qa*="company"]',
                'span[class*="company"]',
                'div[class*="company"]',
                'a[class*="company"]',
            ]
            for sel in company_selectors:
                tag = container.select_one(sel) or soup.select_one(sel)
                if tag:
                    company = tag.get_text(strip=True)
                    break

            city = ""
            city_selectors = [
                'span[data-qa*="address"]',
                'span[data-qa*="location"]',
                'div[data-qa*="address"]',
                'div[data-qa*="location"]',
                'span[class*="metro"]',
                'span[class*="city"]',
                'div[class*="address"]',
                'div[class*="location"]',
            ]
            for sel in city_selectors:
                tag = container.select_one(sel) or soup.select_one(sel)
                if tag:
                    city = tag.get_text(strip=True)
                    break

            salary_text = ""
            salary_selectors = [
                'span[data-qa*="salary"]',
                'div[data-qa*="salary"]',
                'span[class*="salary"]',
                'div[class*="salary"]',
                'span[class*="compensation"]',
                'div[class*="compensation"]',
            ]
            for sel in salary_selectors:
                tag = container.select_one(sel) or soup.select_one(sel)
                if tag:
                    salary_text = tag.get_text(strip=True)
                    break

            salary_min, salary_max, salary_currency = self.parse_salary(salary_text)

            cards.append({
                "url": url,
                "title": title,
                "company": company,
                "city": city,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "salary_text": salary_text,
            })

        logger.info(f"Найдено {len(cards)} карточек на странице")
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

            description = ""
            desc_selectors = [
                'div[data-qa*="vacancy-description"]',
                'div[data-qa*="description"]',
                'div[class*="description"]',
                'div[class*="vacancy-description"]',
                'div[class*="vacancy-section"]',
                'div.vacancy-section',
                'div[class*="job-description"]',
                'div[itemprop="description"]',
            ]
            for sel in desc_selectors:
                desc_tag = soup.select_one(sel)
                if desc_tag:
                    description = desc_tag.get_text(separator="\n", strip=True)
                    break

            skills = []
            skills_selectors = [
                'div[data-qa*="skills"]',
                'div[data-qa*="skill"]',
                'div[class*="skills"]',
                'div[class*="skill"]',
                'div.bloko-tag-list',
                'ul[class*="skills"]',
                'li[data-qa*="skill"]',
            ]
            skill_container = None
            for sel in skills_selectors:
                skill_container = soup.select_one(sel)
                if skill_container:
                    break

            if skill_container:
                skill_tag_selectors = [
                    'span[data-qa*="skill"]',
                    'span.bloko-tag',
                    'span[class*="tag"]',
                    'li[class*="skill"]',
                    'a[data-qa*="skill"]',
                ]
                skill_tags = []
                for sel in skill_tag_selectors:
                    skill_tags = skill_container.select(sel)
                    if skill_tags:
                        break
                skills = [st.get_text(strip=True).lower() for st in skill_tags if st.get_text(strip=True)]

            text_skills = self.extract_skills(description) if description else []
            all_skills = list(set(skills + text_skills))

            return {
                "description": description,
                "skills": all_skills,
            }

        except TimeoutException:
            logger.warning(f"Таймаут загрузки вакансии: {url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки вакансии {url}: {e}")
            return None
