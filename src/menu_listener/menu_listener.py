import os
from typing import Generic, Optional, Type, TypeVar, Union

from menu_listener.menu_options import MenuOptions
from pynput import keyboard

MAX_ENTRIES = 9
ASCII_1 = 49
APP_TITLE = """
  ____       _       _                   _  __       
 / ___| __ _| |_ ___| | _____  ___ _ __ (_)/ _|_   _ 
| |  _ / _` | __/ _ \ |/ / _ \/ _ \ '_ \| | |_| | | |
| |_| | (_| | ||  __/   <  __/  __/ |_) | |  _| |_| |
 \____|\__,_|\__\___|_|\_\___|\___| .__/|_|_|  \__, |
                                  |_|          |___/ 
"""

E = TypeVar("E", bound=MenuOptions)


class MenuListener(Generic[E]):
    is_key_already_pressed: bool = False
    menu_options: Type[E]
    message: Optional[str] = None
    selected_idx: int = 0
    verbose: bool = True

    def __init__(
        self, menu_options: Type[E], message: str, verbose: bool = True
    ) -> None:
        self.is_key_already_pressed = False
        self.selected_idx = 0
        if len(menu_options) > MAX_ENTRIES:
            raise Exception("Menu listener only currently supports 9 options.")
        self.menu_options = menu_options
        self.message = message
        self.verbose = verbose

    def use_menu(self) -> E:
        self.print_menu()
        with keyboard.Listener(
            # pyright: ignore [reportArgumentType]
            on_press=self.on_press_menu_key,
            on_release=self.on_release_menu_key,
            suppress=True,
        ) as listener:
            listener.join()
        return list(self.menu_options)[self.selected_idx]

    def print_menu(self) -> None:
        if not self.verbose:
            return

        os.system("clear")
        print(f"{APP_TITLE}\n{self.message}\n")
        for i, value in enumerate(self.menu_options.list()):
            if i == self.selected_idx:
                print(f">  {i+1}. {value}")
            else:
                print(f"   {i+1}. {value}")
        print()

    def on_press_menu_key(
        self, key: Optional[Union[keyboard.Key, keyboard.KeyCode]]
    ) -> Optional[bool]:
        if self.is_key_already_pressed:
            return
        self.is_key_already_pressed = True
        char = getattr(key, "char", None)
        ascii_key = ord(char) if char else None

        if key == keyboard.Key.down:
            self.selected_idx = (self.selected_idx + 1) % len(self.menu_options)
        elif key == keyboard.Key.up:
            self.selected_idx = (self.selected_idx - 1) % len(self.menu_options)
        elif key == keyboard.Key.enter:
            return False
        elif key == keyboard.Key.esc or key == keyboard.KeyCode.from_char("q"):
            self.selected_idx = len(self.menu_options) - 1
            return False
        elif (
            ascii_key
            and ascii_key >= ASCII_1
            and ascii_key < ASCII_1 + len(self.menu_options)
        ):
            self.selected_idx = ascii_key - ASCII_1
            return False

        self.print_menu()

    def on_release_menu_key(
        self, _: Optional[Union[keyboard.Key, keyboard.KeyCode]]
    ) -> None:
        self.is_key_already_pressed = False
