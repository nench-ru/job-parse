import re

from job_parse.config.settings import GEEKJOB_SEARCH_URL, GEEKJOB_CITY_IDS
from job_parse.parsers.selenium_base import SeleniumSiteParser


class GeekJobParser(SeleniumSiteParser):
    source = "geekjob"
    search_url = GEEKJOB_SEARCH_URL
    city_ids = GEEKJOB_CITY_IDS
    link_pattern = 'a[href*="/vacancy/"], a[href*="/job/"]'
    container_keywords = ["vacancy", "job", "card", "item"]

    company_selectors = [
        'div[class*="company"]', 'a[class*="company"]', 'span[class*="company"]',
        'span[itemprop="name"]', 'span[data-qa*="company"]',
    ]
    city_selectors = [
        'div.info a',
    ]
    salary_selectors = [
        'span.salary', 'div[class*="salary"]', 'span[class*="salary"]', 'div[class*="price"]',
        'span[class*="amount"]',
    ]
    desc_selectors = [
        'div[class*="description"]', 'div[class*="text"]',
        'article', 'section[class*="about"]',
        'div[itemprop="description"]', 'div[class*="content"]',
    ]
    skills_container_selectors = [
        'div[class*="skill"]', 'div[class*="tag"]',
        'ul[class*="skill"]', 'div[class*="requirement"]',
    ]
    skills_tag_selectors = [
        'span[class*="tag"]', 'li', 'span', 'a[class*="skill"]',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_city = ""

    def build_search_url(self, query: str, city: str, page: int) -> str:
        return f"{self.search_url}?qs={query}&page={page + 1}"

    def _clean_city(self, raw: str) -> str:
        parts = re.split(r'[\n\r]', raw)
        city_part = parts[0].strip()
        city_part = re.sub(r'\s*\d[\d\s.,KkМм—–-]*[₽$€]?\s*', '', city_part).strip()
        return city_part.rstrip(",").strip()

    def _first_match(self, container, soup, selectors: list[str]) -> str:
        for sel in selectors:
            tag = container.select_one(sel) or soup.select_one(sel)
            if tag:
                raw = tag.get_text(strip=True)
                if sel == 'div.info a':
                    return self._clean_city(raw)
                return raw
        return ""

    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        self.filter_city = city
        return super().parse_search_page(query, city, pages, limit)

    def _parse_card(self, card: dict) -> bool:
        if self.filter_city and self.filter_city not in card.get("city", ""):
            return False
        return super()._parse_card(card)