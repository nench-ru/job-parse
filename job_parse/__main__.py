import sys

from job_parse.cli.app import main as cli_main
from job_parse.gui.app import run_gui as gui_main


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        gui_main()
    else:
        cli_main()


if __name__ == "__main__":
    main()
