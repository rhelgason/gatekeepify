import os
from typing import Callable, Generic, Optional, Type, TypeVar, Union

from menu_options import MenuOptions
from pynput import keyboard

MAX_ENTRIES = 9
ASCII_1 = 49

E = TypeVar("E", bound=MenuOptions)


class MenuListener(Generic[E]):
    is_key_already_pressed: bool = False
    selected_idx: int = 0
    menu_options: Type[E]
    message: Optional[str] = None

    def __init__(self, menu_options: Type[E], message: str) -> None:
        self.is_key_already_pressed = False
        self.selected_idx = 0
        if len(menu_options) >= MAX_ENTRIES:
            raise Exception("Menu listener only currently supports 9 options.")
        self.menu_options = menu_options
        self.message = message

    def use_menu(self) -> E:
        self.print_menu()
        with keyboard.Listener(
            on_press=self.on_press_menu_key,
            on_release=self.on_release_menu_key,
            suppress=True,
        ) as listener:
            listener.join()
        return list(self.menu_options)[self.selected_idx].value

    def print_menu(self) -> None:
        os.system("clear")
        print(f"{self.message}\n")
        for i, value in enumerate(self.menu_options.list()):
            if i == self.selected_idx:
                print(f">  {i+1}. {value}")
            else:
                print(f"   {i+1}. {value}")
        print()

    def on_press_menu_key(
        self, key: Optional[Union[keyboard.Key, keyboard.KeyCode]]
    ) -> None:
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
            return
        elif key == keyboard.Key.esc or key == keyboard.KeyCode.from_char("q"):
            self.selected_idx = len(self.menu_options) - 1
            return
        elif (
            ascii_key
            and ascii_key >= ASCII_1
            and ascii_key < ASCII_1 + len(self.menu_options)
        ):
            self.selected_idx = ascii_key - ASCII_1
            return

        self.print_menu()
        return

    def on_release_menu_key(
        self, key: Optional[Union[keyboard.Key, keyboard.KeyCode]]
    ) -> None:
        self.is_key_already_pressed = False
