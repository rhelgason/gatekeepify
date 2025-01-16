import os

from menu_listener.menu_listener import MenuListener
from menu_listener.menu_options import DateOptions, MainMenuOptions

def clear_terminal():
    os.system("clear")

def use_main_menu():
    main_menu = MenuListener[MainMenuOptions](
        menu_options=MainMenuOptions,
        message="Welcome to Gatekeepify! Select one of the following options:",
    )
    return main_menu.use_menu()

def use_view_my_stats():
    stats_menu = MenuListener[DateOptions](
        menu_options=DateOptions,
        message="Please select a date range to view your stats for:",
    )
    return stats_menu.use_menu()
