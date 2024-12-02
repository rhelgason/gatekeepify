from enum import Enum

DB_DIRECTORY = "db"
DB_NAME = "database.db"
DB_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

class LoggerAction(Enum):
    UPSERT_DIM_ALL_ALBUMS = "upsertDimAllAlbums"
    UPSERT_DIM_ALL_ARTISTS = "upsertDimAllArtists"
    UPSERT_DIM_ALL_TRACKS = "upsertDimAllTracks"
    UPSERT_TRACK_TO_ARTIST = "upsertTrackToArtist"
    UPSERT_DIM_ALL_USERS = "upsertDimAllUsers"
    UPSERT_DIM_ALL_LISTENS = "upsertDimAllListens"
    RUN_CRON_BACKFILL = "runCronBackfill"
    INCLUDE_POSSIBLE_MISSING_DATA = "includePossibleMissingData"
    CLEAR_POSSIBLE_MISSING_DATA = "clearPossibleMissingData"
