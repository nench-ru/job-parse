import random
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from jop_parse.config.settings import PROXY_FILE


class ProxyManager:
    def __init__(self, proxy_file: Optional[Path] = None):
        self.proxy_file = proxy_file or PROXY_FILE
        self.proxies: list[str] = []
        self.working_proxies: list[str] = []

    def load_proxies(self) -> list[str]:
        if not self.proxy_file or not self.proxy_file.exists():
            logger.warning(f"Файл прокси не найден: {self.proxy_file}")
            return []
        with open(self.proxy_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        self.proxies = lines
        logger.info(f"Загружено {len(self.proxies)} прокси из {self.proxy_file}")
        return self.proxies

    def test_proxy(self, proxy: str, timeout: int = 5) -> bool:
        try:
            url = "http://httpbin.org/ip"
            proxies = {"http://": proxy, "https://": proxy}
            with httpx.Client(proxies=proxies, timeout=timeout, verify=False) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    logger.debug(f"Прокси работает: {proxy}")
                    return True
        except Exception as e:
            logger.debug(f"Прокси не работает {proxy}: {e}")
        return False

    def test_all_proxies(self) -> list[str]:
        self.working_proxies = []
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
        logger.info(f"Рабочих прокси: {len(self.working_proxies)}/{len(self.proxies)}")
        return self.working_proxies

    def get_random_proxy(self) -> Optional[str]:
        if not self.working_proxies:
            if not self.proxies:
                return None
            return random.choice(self.proxies)
        return random.choice(self.working_proxies)

    def get_selenium_options(self) -> Optional[str]:
        proxy = self.get_random_proxy()
        if not proxy:
            return None
        return proxy

    def is_available(self) -> bool:
        return bool(self.proxies)
