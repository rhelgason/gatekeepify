from enum import Enum


class MenuOptions(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class MainMenuOptions(MenuOptions):
    DO_NOTHING = "Do Nothing"
    QUIT = "Quit"
