# job-parse — Умный парсер вакансий с аналитикой (alpha)

Парсит **6 сайтов** по заданным критериям: 5 через Selenium (с обходом антидетекта) + Trudvsem через официальное API.  
Анализирует требования к позициям (какие технологии чаще просят), строит статистику зарплат по стеку.  
Экспорт в **CSV** и **Excel** (4 листа).  
Графический интерфейс на **CustomTkinter**.

---

## Возможности

- Парсинг 6 сайтов:
  - **HH.ru**, **Habr Career**, **SuperJob.ru**, **GeekJob.ru**, **Rabota.ru** — через `undetected-chromedriver` (антидетект)
  - **Trudvsem.ru** (Работа России) — через официальное REST API (без Selenium)
- Дедупликация вакансий по URL — повторный запуск не сохраняет дубликаты
- Извлечение навыков: структурно (блок ключевых навыков) + текстовый поиск по словарю из 100+ технологий
- Парсинг зарплат (вилки, валюты, конвертация USD/EUR/KZT → RUB)
- Прокси-ротация с проверкой работоспособности
- Обработка капчи с паузой и скриншотом
- Статистика: топ навыков, распределение по городам/источникам
- Аналитика ЗП: по навыку, по городу, по источнику
- Экспорт: CSV (все вакансии) или Excel (4 листа: вакансии, топ навыков, ЗП по городам, общая статистика)
- CLI (rich-таблицы) и GUI (CustomTkinter) — два интерфейса на выбор
- Сохранение последних параметров между запусками (`gui_config.json`)

---

## Установка

### Требования

- **Python 3.11+** (не требуется для .exe)
- **Google Chrome** (установленный) — не требуется для Trudvsem (API) и если используете .exe

### Вариант 1: Python (pip)

```powershell
pip install job-parse
# или из локальной сборки:
pip install job_parse-1.0.0a1-py3-none-any.whl
```

### Вариант 2: git clone + зависимости

```powershell
git clone https://github.com/nench-ru/job-parse.git
cd job-parse
pip install -r requirements.txt
```

### Вариант 3: Windows .exe (без Python)

Скачайте `job_parse.exe` со страницы релиза и запустите двойным кликом.

> **Примечание:** для парсинга через Selenium (HH, Habr, SuperJob и др.) требуется установленный Chrome.
> Trudvsem работает через API — Chrome не нужен.

---

## Прокси (опционально)

Положите файл `proxies.txt` в рабочую директорию (откуда запускаете программу), по одной прокси на строку:

```
http://user:pass@ip:port
socks5://user:pass@ip:port
http://ip:port
```

Если прокси невалидны — программа использует прямой IP с предупреждением.

---

## Запуск

| Способ | Команда |
|--------|---------|
| После `pip install` | `job_parse <команда>` |
| Из папки с проектом | `python -m job_parse <команда>` |
| Windows .exe | `job_parse.exe <команда>` |

Для GUI добавьте аргумент `gui`:
```powershell
job_parse gui
```

---

## Использование (CLI)

### `parse` — Парсинг вакансий

```powershell
job_parse parse --site all --query "Python разработчик" --limit 20
```

| Аргумент | По умолчанию | Описание |
|----------|-------------|---------|
| `--site` | `all` | `hh` / `habr` / `superjob` / `geekjob` / `rabota` / `trudvsem` / `all` |
| `--query` | **обязательный** | Поисковый запрос |
| `--city` | — | Город |
| `--pages` | `3` | Количество страниц поиска |
| `--limit` | `0` | Лимит новых вакансий (0 — без лимита) |
| `--headless` | — | Запуск Chrome без GUI (фоном) |
| `--proxy-file` | — | Путь к файлу с прокси |
| `--no-captcha-check` | — | Отключить проверку капчи |

Примеры:
```powershell
# Все сайты
python -m job_parse parse --site all --query "Python" --limit 30 --headless

# SuperJob по Москве
python -m job_parse parse --site superjob --query "Java" --city "Москва" --pages 3

# Trudvsem через API (без Chrome, мгновенно)
python -m job_parse parse --site trudvsem --query "Python"

# HH с прокси
python -m job_parse parse --site hh --query "Go" --pages 5 --proxy-file proxies.txt

# Без проверки капчи
python -m job_parse parse --site hh --query "Python" --no-captcha-check
```

Если установили через `pip install` или используете `.exe`, замените `python -m job_parse` на `job_parse` / `job_parse.exe`:

```powershell
# Все сайты
job_parse parse --site all --query "Python" --limit 30 --headless

# SuperJob по Москве
job_parse parse --site superjob --query "Java" --city "Москва" --pages 3

# Trudvsem через API (без Chrome, мгновенно)
job_parse parse --site trudvsem --query "Python"

# HH с прокси
job_parse parse --site hh --query "Go" --pages 5 --proxy-file proxies.txt

# Без проверки капчи
job_parse parse --site hh --query "Python" --no-captcha-check
```

### `stats` — Общая статистика

```powershell
job_parse stats
```

Показывает количество вакансий по сайтам, топ-20 навыков, топ-10 городов.

### `analyze skills` — Анализ навыков

```powershell
job_parse analyze skills --top 30
job_parse analyze skills --skill Docker
```

### `analyze salary` — Анализ зарплат

```powershell
job_parse analyze salary
job_parse analyze salary --skill Python
```

### `list` — Список вакансий

```powershell
job_parse list --site hh --limit 10
```

### `export` — Экспорт данных

```powershell
job_parse export --format excel --output report.xlsx
job_parse export --format csv --output data.csv
```

---

## Использование (GUI)

```powershell
job_parse gui
```

Открывает окно с 4 вкладками:

| Вкладка | Функции |
|---------|---------|
| **Парсинг** | Все параметры парсинга + лог в реальном времени + кнопка Стоп |
| **Аналитика** | Топ навыков, ЗП по навыку/городу, общая статистика |
| **Экспорт** | Выбор формата, пути, кнопка экспорта |
| **База данных** | Таблица вакансий с фильтром по сайту |

Параметры автоматически сохраняются в `gui_config.json` в директории данных:
- Windows: `%APPDATA%/job-parse/gui_config.json`
- Linux: `~/.local/share/job-parse/gui_config.json`

---

## Структура проекта

```
job-parse/
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── LICENSE                  # MIT
├── build_exe.py             # Сборка .exe (PyInstaller)
├── job_parse/               # Python-пакет
│   ├── __main__.py          # Точка входа
│   ├── config/settings.py   # URL, города, словарь навыков
│   ├── models/vacancy.py    # dataclass Vacancy
│   ├── storage/db.py        # SQLite (дедупликация по URL)
│   ├── proxy/manager.py     # Загрузка/тест/ротация прокси
│   ├── parsers/
│   │   ├── base.py              # Базовый Selenium-класс
│   │   ├── selenium_base.py     # Общий класс для Selenium-сайтов
│   │   ├── hh.py, habr.py, superjob.py, geekjob.py, rabota.py
│   │   └── trudvsem.py          # API-парсер (без Selenium)
│   ├── analytics/
│   │   ├── stats.py         # Топ навыков, распределение
│   │   └── salary.py        # ЗП по стеку/городу
│   ├── export/exporter.py   # CSV / Excel
│   ├── cli/app.py           # CLI-интерфейс
│   └── gui/                 # GUI на CustomTkinter
│       ├── app.py, parse_tab.py, analytics_tab.py
│       ├── export_tab.py, list_tab.py
│       └── log_console.py, settings_store.py
```

### Директория данных

База данных, логи и настройки GUI хранятся в системной директории приложения:

| Платформа | Путь |
|-----------|------|
| Windows   | `%APPDATA%/job-parse/` |
| Linux     | `~/.local/share/job-parse/` |

Там находятся:
- `vacancies.db` — SQLite с вакансиями
- `gui_config.json` — сохранённые параметры GUI
- `logs/` — логи и скриншоты капчи

---

## Структура базы данных

Файл: `vacancies.db` (SQLite, создаётся автоматически в директории данных)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | INTEGER PK | Автоинкремент |
| `source` | TEXT | `hh` / `habr` / `superjob` / `geekjob` / `rabota` / `trudvsem` |
| `url` | TEXT UNIQUE | Ссылка (ключ дедупликации) |
| `title` | TEXT | Должность |
| `company` | TEXT | Компания |
| `city` | TEXT | Город |
| `salary_min` | INTEGER | Нижняя граница (₽) |
| `salary_max` | INTEGER | Верхняя граница (₽) |
| `salary_currency` | TEXT | Валюта |
| `description` | TEXT | Описание |
| `skills` | TEXT | JSON-массив технологий |
| `parsed_at` | TEXT | Дата парсинга |

---

## Обработка ошибок

| Ситуация | Поведение |
|----------|----------|
| Капча | 2 попытки × 60 сек, скриншот в `logs/captcha_debug.png`, затем RuntimeError |
| Таймаут (>60 сек) | Пропуск страницы |
| 5+ таймаутов подряд | Парсинг сайта прекращается |
| Прокси не работает | Случайный рабочий; если нет — прямой IP |
| Падение ChromeDriver | Автоперезапуск |
| Ошибка в карточке | Пропуск одной карточки |

Логи: `job_parse/logs/parser.log`
