import sys
import traceback

from job_parse.cli.app import main as cli_main
from job_parse.gui.app import run_gui as gui_main


def main():
    if getattr(sys, "frozen", False):
        try:
            gui_main()
        except Exception:
            traceback.print_exc()
            input("\nНажмите Enter для выхода...")
    elif len(sys.argv) > 1 and sys.argv[1] == "gui":
        gui_main()
    else:
        cli_main()


if __name__ == "__main__":
    main()
