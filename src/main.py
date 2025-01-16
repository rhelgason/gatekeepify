import os
from datetime import datetime, timedelta

from menu_listener.display_utils import use_main_menu, use_view_my_stats
from menu_listener.menu_options import DateOptions, MainMenuOptions
from spotify.stat_viewer import StatViewer


def main() -> int:
    os.system("tput civis")
    res = use_main_menu()
    if res == 1:
        exit_program()
        return 1
    return exit_program()


def view_my_stats() -> int:
    option = use_view_my_stats()
    while option != DateOptions.RETURN:
        earliest_ds = None
        if option == DateOptions.TODAY:
            earliest_ds = datetime.today()
        elif option == DateOptions.LAST_MONTH:
            earliest_ds = datetime.today() - timedelta(days=30)
        elif option == DateOptions.LAST_YEAR:
            earliest_ds = datetime.today() - timedelta(days=365)

        stat_viewer = StatViewer(earliest_ds)
        stat_viewer.display()
        option = use_view_my_stats()
    return 0


def exit_program():
    os.system("tput cnorm")
    return 0


if __name__ == "__main__":
    main()
