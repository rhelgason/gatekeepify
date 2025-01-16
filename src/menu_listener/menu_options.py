from enum import Enum
from types import DynamicClassAttribute


class MenuOptions(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class MainMenuOptions(MenuOptions):
    QUIT = "Quit"
