from typing import Optional
from abc import abstractmethod

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from loguru import logger

from job_parse.config.settings import CONSECUTIVE_ERROR_LIMIT, LOGS_DIR
from job_parse.models.vacancy import Vacancy
from job_parse.parsers.base import BaseParser
from job_parse.storage.db import Database


class SeleniumSiteParser(BaseParser):
    source = ""
    search_url = ""
    city_ids: dict[str, str] = {}
    link_pattern = 'a[href*="/vacancy/"]'
    container_keywords: list[str] = ["vacancy", "job", "card", "item", "result"]

    company_selectors: list[str] = []
    city_selectors: list[str] = []
    salary_selectors: list[str] = []
    desc_selectors: list[str] = []
    skills_container_selectors: list[str] = []
    skills_tag_selectors: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: Optional[Database] = None

    def set_db(self, db: Database):
        self.db = db

    @abstractmethod
    def build_search_url(self, query: str, city: str, page: int) -> str:
        ...

    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        parsed_count = 0

        for page in range(pages):
            url = self.build_search_url(query, city, page)
            logger.info(f"{self.source}: страница {page + 1}/{pages}")

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
                    logger.warning(f"{self.source}: нет вакансий на странице {page + 1}")
                    debug_path = LOGS_DIR / f"{self.source}_debug_page{page + 1}.html"
                    try:
                        with open(debug_path, "w", encoding="utf-8") as f:
                            f.write(self.driver.page_source)
                        logger.info(f"Сохранён HTML: {debug_path}")
                    except Exception:
                        pass
                    break

                for card in cards:
                    try:
                        if self._parse_card(card):
                            parsed_count += 1
                        self.random_delay(2, 5)
                    except Exception as e:
                        logger.error(f"{self.source}: ошибка парсинга карточки: {e}")
                        self.consecutive_errors += 1

                    if limit > 0 and parsed_count >= limit:
                        break

                self.consecutive_errors = 0
                if limit > 0 and parsed_count >= limit:
                    break

            except TimeoutException:
                logger.error(f"{self.source}: таймаут страницы {page + 1} (>60 сек)")
                self.consecutive_errors += 1
                if self.consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                    logger.error("Слишком много таймаутов подряд. Парсинг остановлен.")
                    break
                continue
            except Exception as e:
                logger.error(f"{self.source}: ошибка на странице {page + 1}: {e}")
                self.consecutive_errors += 1
                continue

        logger.info(f"{self.source}: завершён. Добавлено: {parsed_count}")
        return parsed_count

    def _find_vacancy_links(self, soup: BeautifulSoup) -> list[tuple]:
        results = []
        all_links = soup.select(self.link_pattern)
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
                if container.name in ("div", "article", "section", "li"):
                    classes = " ".join(container.get("class", []))
                    if any(kw in classes.lower() for kw in self.container_keywords):
                        break
            results.append((link, container))
        return results

    def _extract_cards_from_search(self, soup: BeautifulSoup) -> list[dict]:
        cards = []
        found_pairs = self._find_vacancy_links(soup)
        if not found_pairs:
            logger.warning(f"{self.source}: не найдены ссылки на вакансии")
            return []

        base_domain = self._extract_base_domain()

        for link_tag, container in found_pairs:
            url = link_tag.get("href", "")
            if not url:
                continue
            if url.startswith("/"):
                url = f"{base_domain}{url}"

            title = link_tag.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            company = self._first_match(container, soup, self.company_selectors)
            city_text = self._first_match(container, soup, self.city_selectors)
            salary_text = self._first_match(container, soup, self.salary_selectors)
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

        logger.info(f"{self.source}: найдено {len(cards)} карточек")
        return cards

    def _extract_base_domain(self) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(self.search_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _first_match(self, container, soup, selectors: list[str]) -> str:
        for sel in selectors:
            tag = container.select_one(sel) or soup.select_one(sel)
            if tag:
                return tag.get_text(strip=True)
        return ""

    def _parse_card(self, card: dict) -> bool:
        if not card["url"]:
            return False
        if self.db and self.db.url_exists(card["url"]):
            logger.debug(f"{self.source}: вакансия уже есть в БД: {card['title']}")
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
            logger.info(f"{self.source}: добавлен: {vacancy.title} ({vacancy.company})")
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
            for sel in self.desc_selectors:
                tag = soup.select_one(sel)
                if tag:
                    description = tag.get_text(separator="\n", strip=True)
                    break

            skills_container = None
            for sel in self.skills_container_selectors:
                skills_container = soup.select_one(sel)
                if skills_container:
                    break

            skills = []
            if skills_container:
                for sel in self.skills_tag_selectors:
                    tags = skills_container.select(sel)
                    if tags:
                        skills = [t.get_text(strip=True).lower() for t in tags if t.get_text(strip=True)]
                        break

            text_skills = self.extract_skills(description) if description else []
            all_skills = list(set(skills + text_skills))
            return {"description": description, "skills": all_skills}

        except TimeoutException:
            logger.warning(f"{self.source}: таймаут вакансии: {url}")
            return None
        except Exception as e:
            logger.error(f"{self.source}: ошибка загрузки {url}: {e}")
            return None
