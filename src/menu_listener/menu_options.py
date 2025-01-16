from enum import Enum


class MenuOptions(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class MainMenuOptions(MenuOptions):
    VIEW_MY_STATS = "View My Stats"
    QUIT = "Quit"


class DateOptions(MenuOptions):
    TODAY = "Today"
    LAST_MONTH = "Last Month"
    LAST_YEAR = "Last Year"
    ALL_TIME = "All Time"
    RETURN = "Return"
