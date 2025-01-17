import os

from menu_listener.display_utils import use_main_menu


def main() -> int:
    os.system("tput civis")
    res = use_main_menu()
    if res == 1:
        exit_program()
        return 1
    return exit_program()


def exit_program():
    os.system("tput cnorm")
    return 0


if __name__ == "__main__":
    main()
