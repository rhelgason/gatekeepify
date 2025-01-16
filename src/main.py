import os

from menu_listener.display_utils import use_main_menu
from menu_listener.menu_options import MainMenuOptions


def main() -> int:
    os.system("tput civis")
    option = use_main_menu()
    while option != MainMenuOptions.QUIT:
        res = 0

        if res == 1:
            exit_program()
            return 1
        option = use_main_menu()
    return exit_program()


def exit_program():
    os.system("tput cnorm")
    return 0


if __name__ == "__main__":
    main()
