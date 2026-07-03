from job_parse.config.settings import RABOTA_SEARCH_URL, RABOTA_CITY_IDS
from job_parse.parsers.selenium_base import SeleniumSiteParser


class RabotaParser(SeleniumSiteParser):
    source = "rabota"
    search_url = RABOTA_SEARCH_URL
    city_ids = RABOTA_CITY_IDS
    link_pattern = 'a[href*="/vacancy/"], a[href*="/jobs/"]'
    container_keywords = ["vacancy", "job", "card", "item", "result"]

    company_selectors = [
        'span[class*="company"]', 'a[class*="company"]', 'div[class*="company"]',
        'span[data-qa*="company"]', 'div[data-qa*="employer"]',
    ]
    city_selectors = [
        'span[class*="city"]', 'div[class*="city"]', 'span[class*="metro"]',
        'span[class*="address"]', 'span[data-qa*="address"]',
    ]
    salary_selectors = [
        'span[class*="salary"]', 'div[class*="salary"]', 'span[class*="price"]',
        'div[class*="price"]', 'span[data-qa*="salary"]',
    ]
    desc_selectors = [
        'div[class*="description"]', 'div[itemprop="description"]',
        'div[class*="vacancy-description"]', 'article',
        'div[class*="text"]', 'div[class*="content"]',
    ]
    skills_container_selectors = [
        'div[class*="skill"]', 'div[class*="tag"]',
        'ul[class*="skill"]', 'div[class*="requirement"]', 'div[class*="key"]',
    ]
    skills_tag_selectors = [
        'span[class*="tag"]', 'li', 'span', 'a',
    ]

    def build_search_url(self, query: str, city: str, page: int) -> str:
        if city and city in self.city_ids:
            return f"{self.search_url}{self.city_ids[city]}/?query={query}&page={page + 1}"
        return f"{self.search_url}?query={query}&page={page + 1}"
