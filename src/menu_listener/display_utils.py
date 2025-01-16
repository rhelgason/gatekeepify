import os
from datetime import datetime, timedelta

from menu_listener.menu_listener import MenuListener
from menu_listener.menu_options import DateOptions, MainMenuOptions
from spotify.stat_viewer import StatViewer


def clear_terminal():
    os.system("clear")


def use_main_menu():
    main_menu = MenuListener[MainMenuOptions](
        menu_options=MainMenuOptions,
        message="Welcome to Gatekeepify! Select one of the following options:",
    )
    option = main_menu.use_menu()

    while option != MainMenuOptions.QUIT:
        if option == MainMenuOptions.VIEW_MY_STATS:
            use_view_my_stats()
        option = main_menu.use_menu()


def use_view_my_stats():
    stats_menu = MenuListener[DateOptions](
        menu_options=DateOptions,
        message="Please select a date range to view your stats for:",
    )
    date_option = stats_menu.use_menu()

    while date_option != DateOptions.RETURN:
        earliest_ds = None
        if date_option == DateOptions.TODAY:
            earliest_ds = datetime.today()
        elif date_option == DateOptions.LAST_MONTH:
            earliest_ds = datetime.today() - timedelta(days=30)
        elif date_option == DateOptions.LAST_YEAR:
            earliest_ds = datetime.today() - timedelta(days=365)

        stat_viewer = StatViewer(earliest_ds)
        stat_viewer.display()
        date_option = stats_menu.use_menu()
    return 0
