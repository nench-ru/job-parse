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
        'span[class*="city"]', 'div[class*="city"]', 'span[class*="location"]',
        'span[itemprop="address"]',
    ]
    salary_selectors = [
        'div[class*="salary"]', 'span[class*="salary"]', 'div[class*="price"]',
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

    def build_search_url(self, query: str, city: str, page: int) -> str:
        params = f"?q={query}"
        if city and city in self.city_ids:
            params += f"&city={self.city_ids[city]}"
        return f"{self.search_url}{params}&page={page + 1}"
