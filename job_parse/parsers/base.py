import os
import re
import time
import random
import shutil
from abc import ABC, abstractmethod
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

from job_parse.config.settings import (
    DEFAULT_DELAY_MIN,
    DEFAULT_DELAY_MAX,
    MAX_RETRIES,
    PAUSE_ON_CAPTCHA,
    CONSECUTIVE_ERROR_LIMIT,
    SKILL_KEYWORDS,
    CURRENCY_RATES,
)
from job_parse.proxy.manager import ProxyManager


class BaseParser(ABC):
    def __init__(
        self,
        proxy_manager: Optional[ProxyManager] = None,
        delay_min: float = DEFAULT_DELAY_MIN,
        delay_max: float = DEFAULT_DELAY_MAX,
        headless: bool = False,
        no_captcha_check: bool = False,
    ):
        self.proxy_manager = proxy_manager
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.headless = headless
        self.no_captcha_check = no_captcha_check
        self.driver: Optional[uc.Chrome] = None
        self.consecutive_errors = 0
        self._create_driver()

    @staticmethod
    def _check_chrome_installed() -> bool:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
        if shutil.which("chrome") or shutil.which("google-chrome"):
            return True
        return any(os.path.exists(p) for p in chrome_paths)

    def _create_driver(self):
        if not self._check_chrome_installed():
            raise RuntimeError(
                "Google Chrome не найден. Установите Chrome: https://www.google.com/chrome/"
            )

        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-webgl")
        options.add_argument("--disable-webrtc")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-popup-blocking")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )

        if self.headless:
            options.add_argument("--headless=new")

        proxy = None
        if self.proxy_manager and self.proxy_manager.is_available():
            proxy = self.proxy_manager.get_selenium_options()
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")

        try:
            self.driver = uc.Chrome(options=options)
        except Exception as e:
            logger.warning(f"undetected_chromedriver не запустился: {e}. Пробую fallback...")
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = uc.Chrome(options=options, service=service)
            except Exception as e2:
                raise RuntimeError(
                    f"Не удалось запустить ChromeDriver. Убедитесь, что Chrome установлен.\n"
                    f"Ошибка: {e2}"
                ) from e2

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.driver.set_page_load_timeout(60)
        logger.info("Браузер запущен" + (f" через прокси {proxy}" if proxy else ""))

    def restart_driver(self):
        self.quit()
        self._create_driver()
        self.consecutive_errors = 0

    def random_delay(self, min_s: float = None, max_s: float = None):
        min_s = min_s or self.delay_min
        max_s = max_s or self.delay_max
        time.sleep(random.uniform(min_s, max_s))

    def safe_find(self, by: By, value: str, timeout: int = 10, parent=None) -> Optional:
        parent = parent or self.driver
        try:
            return WebDriverWait(parent, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception:
            return None

    def safe_find_all(self, by: By, value: str, timeout: int = 10, parent=None) -> list:
        parent = parent or self.driver
        try:
            return WebDriverWait(parent, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
        except Exception:
            return []

    def safe_click(self, element, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(element)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            return True
        except Exception as e:
            logger.warning(f"Не удалось кликнуть: {e}")
            return False

    def is_captcha(self) -> bool:
        title = self.driver.title.lower()
        if "just a moment" in title:
            logger.info("Cloudflare: 'Just a moment...'")
            return True
        try:
            self.driver.find_element(
                By.CSS_SELECTOR,
                "iframe[src*='recaptcha'], iframe[src*='captcha'], div[class*='captcha']"
            )
            return True
        except Exception:
            pass
        return False

    def handle_captcha(self) -> bool:
        if self.no_captcha_check:
            return False
        for attempt in range(2):
            if not self.is_captcha():
                return False
            logger.warning(
                f"Обнаружена капча (попытка {attempt + 1}/2). "
                f"Пауза {PAUSE_ON_CAPTCHA} сек для ручного решения..."
            )
            try:
                screenshot_path = "job_parse/logs/captcha_debug.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Скриншот сохранён: {screenshot_path}")
            except Exception:
                pass
            time.sleep(PAUSE_ON_CAPTCHA)
        if self.is_captcha():
            logger.error("Капча не решена после 2 попыток. Завершение.")
            raise RuntimeError(
                "Капча не решена. Попробуйте:\n"
                "  1. Добавить --no-captcha-check (пропустить проверку)\n"
                "  2. Использовать прокси: создайте proxies.txt\n"
                "  3. Проверить, что сайт доступен в браузере вручную"
            )
        return False

    def extract_skills(self, text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for skill in SKILL_KEYWORDS:
            pattern = re.compile(r'(?<![a-zа-я])' + re.escape(skill) + r'(?![a-zа-я])', re.IGNORECASE)
            if pattern.search(text_lower):
                found.append(skill)
        return found

    def parse_salary(self, text: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
        if not text or text.strip() in ("", "по договорённости", "не указана", "з/п не указана"):
            return None, None, None

        text = text.strip().replace("\xa0", " ").replace("&nbsp;", " ")

        currency_map = {
            "₽": "RUB", "руб": "RUB", "руб.": "RUB", "rub": "RUB",
            "$": "USD", "usd": "USD", "USD": "USD",
            "€": "EUR", "eur": "EUR", "EUR": "EUR",
            "₸": "KZT", "kzt": "KZT", "тенге": "KZT",
        }

        currency = None
        for sym, cur in currency_map.items():
            if sym in text.lower():
                currency = cur
                break

        text_clean = text.replace(" ", "").replace("\u202f", "")

        patterns = [
            r'от(\d[\d\s]*)до(\d[\d\s]*)',
            r'(\d[\d\s]*)[—–-](\d[\d\s]*)',
            r'от(\d[\d\s]*)',
            r'до(\d[\d\s]*)',
            r'(\d[\d\s]*)(?:\s*[₽$€₸])',
            r'(\d[\d\s]*)\s*(?:руб|rub|usd|eur|kzt)',
        ]

        salary_min, salary_max = None, None

        for pattern in patterns:
            match = re.search(pattern, text_clean)
            if match:
                groups = match.groups()
                if len(groups) == 2 and groups[0] and groups[1]:
                    salary_min = int(re.sub(r'\s', '', groups[0]))
                    salary_max = int(re.sub(r'\s', '', groups[1]))
                elif "от" in pattern or "до" in pattern:
                    val = int(re.sub(r'\s', '', groups[0]))
                    if "от" in pattern:
                        salary_min = val
                    else:
                        salary_max = val
                else:
                    salary_min = int(re.sub(r'\s', '', groups[0]))
                break

        if currency and currency != "RUB" and currency in CURRENCY_RATES:
            rate = CURRENCY_RATES[currency]
            if salary_min:
                salary_min = int(salary_min * rate)
            if salary_max:
                salary_max = int(salary_max * rate)
            currency = "RUB"

        return salary_min, salary_max, currency

    @abstractmethod
    def parse_search_page(self, query: str, city: str = "", pages: int = 3, limit: int = 0) -> int:
        ...

    @abstractmethod
    def parse_vacancy_detail(self, url: str):
        ...

    def quit(self):
        driver = getattr(self, "driver", None)
        if driver is None:
            return
        try:
            driver.service.stop()
        except Exception:
            pass
        try:
            driver.quit()
        except Exception:
            pass
        try:
            driver.service.process = None
            driver.service.sender = None
            driver.service.receiver = None
        except Exception:
            pass
        self.driver = None
        try:
            import gc
            gc.collect()
        except Exception:
            pass
