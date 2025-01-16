import os

from menu_listener.menu_listener import MenuListener
from menu_listener.menu_options import MainMenuOptions


def clear_terminal():
    os.system("clear")


def use_main_menu():
    main_menu = MenuListener[MainMenuOptions](
        menu_options=MainMenuOptions,
        message="Welcome to Gatekeepify! Select one of the following options:",
    )
    return main_menu.use_menu()
