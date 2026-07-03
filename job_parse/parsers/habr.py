from job_parse.config.settings import HABR_SEARCH_URL
from job_parse.parsers.selenium_base import SeleniumSiteParser


class HabrParser(SeleniumSiteParser):
    source = "habr"
    search_url = HABR_SEARCH_URL
    link_pattern = 'a[href*="/vacancies/"], a[class*="title"], a[class*="vacancy"]'
    container_keywords = ["vacancy", "card", "section-group"]

    company_selectors = [
        'div[class*="company"]', 'a[class*="company"]', 'span[class*="company"]',
    ]
    city_selectors = [
        'div[class*="location"]', 'span[class*="city"]', 'span[class*="location"]',
        'div[class*="address"]',
    ]
    salary_selectors = [
        'div[class*="salary"]', 'span[class*="salary"]', 'div[class*="price"]',
    ]
    desc_selectors = [
        'div[class*="description"]', 'div.vacancy-description',
        'div[class*="vacancy"] section', 'div.section',
    ]
    skills_container_selectors = [
        'div[class*="skills"]', 'div.tags', 'div[class*="tags"]',
    ]
    skills_tag_selectors = [
        'span[class*="tag"]', 'a[class*="tag"]', 'span[class*="skill"]',
    ]

    def build_search_url(self, query: str, city: str, page: int) -> str:
        params = f"?q={query}&type=all"
        if city:
            params += f"&city={city}"
        return f"{self.search_url}{params}&page={page + 1}"
