import os

from constants import APP_TITLE


def clear_terminal():
    os.system("clear")
    print(f"{APP_TITLE}\n")
