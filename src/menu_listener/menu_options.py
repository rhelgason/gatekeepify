from enum import Enum


class MenuOptions(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class MainMenuOptions(MenuOptions):
    SPOTIFY_WRAPPED = "Spotify Wrapped"
    VIEW_MY_STATS = "View My Stats"
    BACKFILL_MY_DATA = "Backfill My Data"
    QUIT = "Quit"


class DateOptions(MenuOptions):
    TODAY = "Today"
    LAST_MONTH = "Last Month"
    LAST_YEAR = "Last Year"
    ALL_TIME = "All Time"
    RETURN = "Return"


class StatViewerOptions(MenuOptions):
    TOP_TRACKS = "Top Tracks"
    TOP_ARTISTS = "Top Artists"
    TOP_GENRES = "Top Genres"
    RETURN = "Return"
