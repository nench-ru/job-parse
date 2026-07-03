import json
from pathlib import Path
from typing import Any

from job_parse.config.settings import BASE_DIR


CONFIG_FILE = BASE_DIR / "gui_config.json"


DEFAULT_CONFIG: dict[str, Any] = {
    "site": "all",
    "query": "",
    "city": "",
    "pages": 3,
    "limit": 0,
    "headless": False,
    "no_captcha_check": False,
    "proxy_file": "",
    "export_format": "excel",
    "export_path": "report.xlsx",
    "list_source": "all",
    "list_limit": 20,
    "window_geometry": "1200x800",
}


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any]):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")
