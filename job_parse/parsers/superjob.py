from job_parse.config.settings import SUPERJOB_SEARCH_URL, SUPERJOB_CITY_SLUGS
from job_parse.parsers.selenium_base import SeleniumSiteParser


class SuperJobParser(SeleniumSiteParser):
    source = "superjob"
    search_url = SUPERJOB_SEARCH_URL
    city_ids = SUPERJOB_CITY_SLUGS
    link_pattern = 'a[href*="/vakansii/"], a[href*="/job/"], a[href*="/vacancy/"]'
    container_keywords = ["vacancy", "job", "card", "item", "result"]

    company_selectors = [
        'span[class*="company"]', 'a[class*="company"]', 'div[class*="company"]',
        'span[data-qa*="employer"]', 'a[data-qa*="employer"]',
    ]
    city_selectors = [
        'span[class*="town"]', 'span[class*="city"]', 'span[class*="location"]',
        'div[class*="town"]', 'div[class*="location"]', 'span[data-qa*="address"]',
    ]
    salary_selectors = [
        'span[class*="salary"]', 'div[class*="salary"]', 'span[class*="price"]',
        'span[class*="compensation"]', 'span[data-qa*="salary"]',
    ]
    desc_selectors = [
        'div[class*="description"]', 'div[class*="vacancy-description"]',
        'section[class*="description"]', 'div[class*="text"]',
        'div[itemprop="description"]', 'article',
    ]
    skills_container_selectors = [
        'div[class*="skills"]', 'div[class*="key-skills"]',
        'ul[class*="skills"]', 'div[class*="tags"]',
    ]
    skills_tag_selectors = [
        'span[class*="tag"]', 'li', 'span', 'a',
    ]

    def build_search_url(self, query: str, city: str, page: int) -> str:
        params = f"?keywords={query}"
        if city and city in self.city_ids:
            params += f"&town={self.city_ids[city]}"
        return f"{self.search_url}{params}&page={page + 1}"
