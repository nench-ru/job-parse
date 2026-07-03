"""
Сборка .exe для Windows через PyInstaller.

Использование:
    pip install pyinstaller
    python build_exe.py

На выходе: dist/job_parse/job_parse.exe (onedir) или dist/job_parse.exe (onefile)

Рекомендуется onefile для распространения, onedir для отладки.
"""

import os
import sys

try:
    import PyInstaller.__main__
except ImportError:
    print("Установите PyInstaller: pip install pyinstaller")
    sys.exit(1)

name = "job_parse"
entry_point = "job_parse/__main__.py"

common_args = [
    entry_point,
    "--name", name,
    "--clean",
    "--noconfirm",
]

hidden_imports = [
    # Tkinter / CustomTkinter
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.filedialog",
    "--hidden-import", "tkinter.messagebox",
    "--hidden-import", "customtkinter",
    "--hidden-import", "PIL._tkinter_finder",

    # Парсеры
    "--hidden-import", "job_parse.parsers.hh",
    "--hidden-import", "job_parse.parsers.habr",
    "--hidden-import", "job_parse.parsers.superjob",
    "--hidden-import", "job_parse.parsers.geekjob",
    "--hidden-import", "job_parse.parsers.rabota",
    "--hidden-import", "job_parse.parsers.trudvsem",
    "--hidden-import", "job_parse.parsers.base",
    "--hidden-import", "job_parse.parsers.selenium_base",

    # Аналитика
    "--hidden-import", "job_parse.analytics.stats",
    "--hidden-import", "job_parse.analytics.salary",

    # GUI
    "--hidden-import", "job_parse.gui.app",
    "--hidden-import", "job_parse.gui.parse_tab",
    "--hidden-import", "job_parse.gui.list_tab",
    "--hidden-import", "job_parse.gui.analytics_tab",
    "--hidden-import", "job_parse.gui.export_tab",
    "--hidden-import", "job_parse.gui.log_console",
    "--hidden-import", "job_parse.gui.settings_store",

    # Selenium / ChromeDriver
    "--hidden-import", "selenium",
    "--hidden-import", "undetected_chromedriver",
    "--hidden-import", "webdriver_manager",

    # BS4 / lxml
    "--hidden-import", "bs4",
    "--hidden-import", "lxml",

    # Прочее
    "--hidden-import", "loguru",
    "--hidden-import", "httpx",
    "--hidden-import", "pandas",
    "--hidden-import", "numpy",
    "--hidden-import", "PIL",
    "--hidden-import", "openpyxl",
    "--hidden-import", "rich",
]

collect_data = [
    "--collect-data", "customtkinter",
    "--collect-data", "undetected_chromedriver",
]

if __name__ == "__main__":
    args = common_args + ["--onefile", "--windowed"] + hidden_imports + collect_data
    print("Сборка job_parse.exe (onefile, windowed)...")
    PyInstaller.__main__.run(args)
    print("Готово! Исполняемый файл: dist/job_parse.exe")
