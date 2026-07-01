import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import box
from loguru import logger

from jop_parse.config.settings import DB_PATH, PROXY_FILE
from jop_parse.storage.db import Database
from jop_parse.proxy.manager import ProxyManager
from jop_parse.parsers.hh import HHParser
from jop_parse.parsers.habr import HabrParser
from jop_parse.analytics.stats import StatsAnalyzer
from jop_parse.analytics.salary import SalaryAnalyzer
from jop_parse.export.exporter import Exporter


console = Console()


def setup_logging(verbose: bool = False):
    logger.remove()
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
    )
    logger.add(
        "jop_parse/logs/parser.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
    )


def cmd_parse(args: argparse.Namespace):
    proxy_manager = ProxyManager(PROXY_FILE) if args.proxy_file else ProxyManager()

    if args.proxy_file:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Загрузка и проверка прокси...", total=None)
            proxy_manager.load_proxies()
            proxy_manager.test_all_proxies()
            progress.update(task, visible=False)

    sources_to_parse = []
    if args.site in ("hh", "all"):
        sources_to_parse.append(("hh", HHParser))
    if args.site in ("habr", "all"):
        sources_to_parse.append(("habr", HabrParser))

    if not sources_to_parse:
        console.print("[red]Неверный сайт. Используйте: hh, habr, all[/red]")
        return

    with Database(DB_PATH) as db:
        total_parsed = 0
        for source_name, parser_class in sources_to_parse:
            console.print(f"\n[bold cyan]Парсинг {source_name.upper()}...[/bold cyan]")
            parser = parser_class(
                proxy_manager=proxy_manager if args.proxy_file else None,
                headless=args.headless,
                no_captcha_check=args.no_captcha_check,
            )
            parser.set_db(db)
            try:
                count = parser.parse_search_page(
                    query=args.query,
                    city=args.city,
                    pages=args.pages,
                    limit=args.limit,
                )
                total_parsed += count
                console.print(f"[green]Добавлено вакансий с {source_name.upper()}: {count}[/green]")
            except RuntimeError as e:
                console.print(f"[red]{e}[/red]")
                return
            finally:
                parser.quit()

        counts = db.get_vacancies_count()
        console.print(Panel(
            f"[bold green]Готово![/bold green]\n"
            f"  Новых вакансий добавлено: {total_parsed}\n"
            f"  Всего в базе: {counts.get('total', 0)} (hh: {counts.get('hh', 0)}, habr: {counts.get('habr', 0)})",
            title="Результат",
            box=box.ROUNDED,
        ))


def cmd_stats(args: argparse.Namespace):
    with Database(DB_PATH) as db:
        analyzer = StatsAnalyzer(db)
        counts = db.get_vacancies_count()

        console.print(Panel(
            f"[bold]Всего вакансий:[/bold] {counts.get('total', 0)}\n"
            f"[bold]HH.ru:[/bold] {counts.get('hh', 0)}\n"
            f"[bold]Habr:[/bold] {counts.get('habr', 0)}",
            title="Общая статистика",
            box=box.ROUNDED,
        ))

        top = analyzer.top_skills(20)
        if top:
            table = Table(title="Топ-20 навыков", box=box.SIMPLE)
            table.add_column("#", style="dim")
            table.add_column("Навык", style="cyan")
            table.add_column("Количество", justify="right")
            table.add_column("Частота", justify="right")
            total = sum(c for _, c in top)
            for i, (skill, count) in enumerate(top, 1):
                freq = f"{count / total * 100:.1f}%"
                table.add_row(str(i), skill, str(count), freq)
            console.print(table)

        cities = analyzer.city_distribution()[:10]
        if cities:
            table2 = Table(title="Топ-10 городов", box=box.SIMPLE)
            table2.add_column("#", style="dim")
            table2.add_column("Город", style="cyan")
            table2.add_column("Вакансий", justify="right")
            for i, (city, count) in enumerate(cities, 1):
                table2.add_row(str(i), city, str(count))
            console.print(table2)


def cmd_analyze_skills(args: argparse.Namespace):
    with Database(DB_PATH) as db:
        analyzer = StatsAnalyzer(db)
        top = analyzer.top_skills(args.top)

        if not top:
            console.print("[yellow]Нет данных о навыках[/yellow]")
            return

        if args.skill:
            filtered = [(s, c) for s, c in top if args.skill.lower() in s.lower()]
            if not filtered:
                console.print(f"[yellow]Навык '{args.skill}' не найден[/yellow]")
                return
            top = filtered

        table = Table(title=f"Топ навыков", box=box.SIMPLE)
        table.add_column("#", style="dim")
        table.add_column("Навык", style="cyan")
        table.add_column("Количество", justify="right")
        total = sum(c for _, c in top)
        for i, (skill, count) in enumerate(top, 1):
            freq = f"{count / total * 100:.1f}%"
            table.add_row(str(i), skill, str(count), freq)
        console.print(table)


def cmd_analyze_salary(args: argparse.Namespace):
    with Database(DB_PATH) as db:
        salary_analyzer = SalaryAnalyzer(db)

        if args.skill:
            data = salary_analyzer.salary_by_skill(args.skill)
            if data["count"] == 0:
                console.print(f"[yellow]Нет данных о зарплате для навыка '{args.skill}'[/yellow]")
                return
            table = Table(title=f"Зарплаты для навыка: {args.skill}", box=box.SIMPLE)
            table.add_column("Показатель", style="cyan")
            table.add_column("Значение", justify="right")
            table.add_row("Вакансий с ЗП", str(data["count"]))
            table.add_row("Средняя", f"{data['avg']:,.0f} ₽")
            table.add_row("Медианная", f"{data['median']:,.0f} ₽")
            table.add_row("Мин", f"{data['min']:,.0f} ₽")
            table.add_row("Макс", f"{data['max']:,.0f} ₽")
            console.print(table)
        else:
            df_overview = salary_analyzer.salary_overview()
            if not df_overview.empty:
                table = Table(title="Общая статистика зарплат", box=box.SIMPLE)
                table.add_column("Показатель", style="cyan")
                table.add_column("Значение", justify="right")
                for col in df_overview.columns:
                    val = df_overview.iloc[0][col]
                    if isinstance(val, (int, float)):
                        table.add_row(col, f"{val:,.0f}")
                    else:
                        table.add_row(col, str(val))
                console.print(table)

            df_city = salary_analyzer.salary_by_city()
            if not df_city.empty:
                table2 = Table(title="Зарплаты по городам", box=box.SIMPLE)
                for col in df_city.columns:
                    table2.add_column(col.capitalize(), style="cyan" if col == "city" else None, justify="right" if col != "city" else None)
                for _, row in df_city.iterrows():
                    table2.add_row(*[str(row[col]) for col in df_city.columns])
                console.print(table2)


def cmd_list(args: argparse.Namespace):
    with Database(DB_PATH) as db:
        if args.site and args.site != "all":
            vacancies = db.get_vacancies_by_source(args.site)
        else:
            vacancies = db.get_all_vacancies()

        if args.limit:
            vacancies = vacancies[:args.limit]

        if not vacancies:
            console.print("[yellow]Нет вакансий в базе[/yellow]")
            return

        table = Table(title=f"Последние вакансии ({len(vacancies)})", box=box.SIMPLE)
        table.add_column("#", style="dim")
        table.add_column("Источник", style="dim")
        table.add_column("Должность", style="cyan")
        table.add_column("Компания")
        table.add_column("Город")
        table.add_column("Зарплата", justify="right")
        table.add_column("Навыки")

        for i, v in enumerate(vacancies, 1):
            salary = ""
            if v.salary_min and v.salary_max:
                salary = f"{v.salary_min:,} - {v.salary_max:,} ₽"
            elif v.salary_min:
                salary = f"от {v.salary_min:,} ₽"
            elif v.salary_max:
                salary = f"до {v.salary_max:,} ₽"
            else:
                salary = "н/у"

            skills_str = ", ".join(v.skills[:5]) if v.skills else ""
            if len(v.skills) > 5:
                skills_str += f"..."

            table.add_row(
                str(i),
                v.source,
                v.title[:50],
                v.company[:30],
                v.city[:20],
                salary,
                skills_str[:40],
            )

        console.print(table)


def cmd_export(args: argparse.Namespace):
    with Database(DB_PATH) as db:
        exporter = Exporter(db)
        output = Path(args.output)

        try:
            if args.format == "csv":
                path = exporter.to_csv(output)
                console.print(f"[green]Экспорт в CSV завершён: {path}[/green]")
            elif args.format == "excel":
                path = exporter.to_excel(output)
                console.print(f"[green]Экспорт в Excel завершён: {path}[/green]")
            else:
                console.print("[red]Неверный формат. Используйте: csv, excel[/red]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="jop_parse — Умный парсер вакансий с аналитикой",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Подробный лог")
    subparsers = parser.add_subparsers(dest="command", help="Команды")

    parse_parser = subparsers.add_parser("parse", help="Парсинг вакансий")
    parse_parser.add_argument("--site", choices=["hh", "habr", "all"], default="all", help="Сайт для парсинга")
    parse_parser.add_argument("--query", required=True, help="Поисковый запрос")
    parse_parser.add_argument("--city", default="", help="Город (необязательно)")
    parse_parser.add_argument("--pages", type=int, default=3, help="Количество страниц (по умолчанию 3)")
    parse_parser.add_argument("--limit", type=int, default=0, help="Максимум вакансий (0 — без лимита)")
    parse_parser.add_argument("--headless", action="store_true", help="Запуск без GUI")
    parse_parser.add_argument("--proxy-file", default="", help="Файл с прокси")
    parse_parser.add_argument("--no-captcha-check", action="store_true", help="Отключить проверку капчи")

    stats_parser = subparsers.add_parser("stats", help="Общая статистика")

    analyze_parser = subparsers.add_parser("analyze", help="Аналитика")
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_type")

    skills_parser = analyze_sub.add_parser("skills", help="Анализ навыков")
    skills_parser.add_argument("--skill", default="", help="Фильтр по навыку")
    skills_parser.add_argument("--top", type=int, default=20, help="Топ N навыков")

    salary_parser = analyze_sub.add_parser("salary", help="Анализ зарплат")
    salary_parser.add_argument("--skill", default="", help="Навык для анализа зарплат")

    list_parser = subparsers.add_parser("list", help="Список вакансий")
    list_parser.add_argument("--site", choices=["hh", "habr", "all"], default="all")
    list_parser.add_argument("--limit", type=int, default=20)

    export_parser = subparsers.add_parser("export", help="Экспорт данных")
    export_parser.add_argument("--format", choices=["csv", "excel"], default="excel")
    export_parser.add_argument("--output", default="report.xlsx", help="Путь к файлу")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "parse":
        cmd_parse(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "analyze":
        if args.analyze_type == "skills":
            cmd_analyze_skills(args)
        elif args.analyze_type == "salary":
            cmd_analyze_salary(args)
        else:
            console.print("[red]Используйте: analyze skills или analyze salary[/red]")
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
