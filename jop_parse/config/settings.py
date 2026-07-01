from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "vacancies.db"
LOGS_DIR = BASE_DIR / "jop_parse" / "logs"
PROXY_FILE = BASE_DIR / "proxies.txt"

HH_SEARCH_URL = "https://hh.ru/search/vacancy"
HABR_SEARCH_URL = "https://career.habr.com/vacancies"

DEFAULT_PAGES = 3
DEFAULT_DELAY_MIN = 2.0
DEFAULT_DELAY_MAX = 5.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
PAUSE_ON_CAPTCHA = 60
CONSECUTIVE_ERROR_LIMIT = 5

CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Нижний Новгород", "Челябинск", "Самара",
    "Омск", "Ростов-на-Дону", "Уфа", "Красноярск",
    "Воронеж", "Пермь", "Волгоград", "Краснодар",
]

SKILL_KEYWORDS = [
    "python", "django", "fastapi", "flask", "sqlalchemy", "asyncio",
    "docker", "kubernetes", "k8s", "docker-compose",
    "postgresql", "postgres", "mysql", "mongodb", "redis",
    "sql", "nosql", "elasticsearch", "clickhouse",
    "git", "linux", "bash", "ci/cd", "github actions", "gitlab ci",
    "aws", "gcp", "azure", "yandex cloud", "cloud",
    "pytest", "unittest", "selenium", "playwright", "allure",
    "javascript", "typescript", "react", "vue", "vue.js", "angular",
    "html", "css", "sass", "less",
    "rabbitmq", "kafka", "nginx", "caddy",
    "graphql", "grpc", "rest", "rest api",
    "numpy", "pandas", "scikit-learn", "tensorflow", "pytorch",
    "go", "golang", "java", "kotlin", "c++", "c#", "rust",
    "microservices", "architecture", "ddd", "tdd", "solid",
    "terraform", "ansible", "helm",
    "prometheus", "grafana", "zabbix", "datadog",
    "drf", "django rest framework", "celery",
]

HH_CITY_IDS = {
    "Москва": 1,
    "Санкт-Петербург": 2,
    "Новосибирск": 4,
    "Екатеринбург": 3,
    "Казань": 88,
    "Нижний Новгород": 66,
    "Челябинск": 104,
    "Самара": 78,
    "Омск": 68,
    "Ростов-на-Дону": 76,
    "Уфа": 99,
    "Красноярск": 54,
    "Воронеж": 26,
    "Пермь": 72,
    "Волгоград": 24,
    "Краснодар": 53,
}

CURRENCY_RATES = {
    "USD": 90.0,
    "EUR": 98.0,
    "KZT": 0.2,
}
