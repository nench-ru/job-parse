from job_parse.config.settings import HH_SEARCH_URL, HH_CITY_IDS
from job_parse.parsers.selenium_base import SeleniumSiteParser


class HHParser(SeleniumSiteParser):
    source = "hh"
    search_url = HH_SEARCH_URL
    city_ids = HH_CITY_IDS
    link_pattern = 'a[href*="/vacancy/"]'
    container_keywords = ["vacancy", "serp", "item", "card", "result"]

    company_selectors = [
        'a[data-qa*="employer"]', 'a[data-qa*="company"]',
        'span[data-qa*="company"]', 'div[data-qa*="company"]',
        'span[class*="company"]', 'div[class*="company"]', 'a[class*="company"]',
    ]
    city_selectors = [
        'span[data-qa*="address"]', 'span[data-qa*="location"]',
        'div[data-qa*="address"]', 'div[data-qa*="location"]',
        'span[class*="metro"]', 'span[class*="city"]',
        'div[class*="address"]', 'div[class*="location"]',
    ]
    salary_selectors = [
        'span[data-qa*="salary"]', 'div[data-qa*="salary"]',
        'span[class*="salary"]', 'div[class*="salary"]',
        'span[class*="compensation"]', 'div[class*="compensation"]',
    ]
    desc_selectors = [
        'div[data-qa*="vacancy-description"]', 'div[data-qa*="description"]',
        'div[class*="description"]', 'div[class*="vacancy-description"]',
        'div[class*="vacancy-section"]', 'div.vacancy-section',
        'div[class*="job-description"]', 'div[itemprop="description"]',
    ]
    skills_container_selectors = [
        'div[data-qa*="skills"]', 'div[data-qa*="skill"]',
        'div[class*="skills"]', 'div[class*="skill"]',
        'div.bloko-tag-list', 'ul[class*="skills"]', 'li[data-qa*="skill"]',
    ]
    skills_tag_selectors = [
        'span[data-qa*="skill"]', 'span.bloko-tag',
        'span[class*="tag"]', 'li[class*="skill"]', 'a[data-qa*="skill"]',
    ]

    def build_search_url(self, query: str, city: str, page: int) -> str:
        params = f"?text={query}"
        if city and city in self.city_ids:
            params += f"&area={self.city_ids[city]}"
        else:
            params += "&area=113"
        return f"{self.search_url}{params}&page={page}"
