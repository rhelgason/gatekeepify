from enum import Enum

DB_DIRECTORY = "db"
DB_NAME = "database.db"
DB_TEST_NAME = "test_database.db"
DB_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class LoggerAction(Enum):
    # table upserts
    UPSERT_DIM_ALL_ALBUMS = "upsertDimAllAlbums"
    UPSERT_DIM_ALL_ARTISTS = "upsertDimAllArtists"
    UPSERT_DIM_ALL_TRACKS = "upsertDimAllTracks"
    UPSERT_TRACK_TO_ARTIST = "upsertTrackToArtist"
    UPSERT_ARTIST_TO_GENRE = "upsertArtistToGenre"
    UPSERT_DIM_ALL_USERS = "upsertDimAllUsers"
    UPSERT_DIM_ALL_LISTENS = "upsertDimAllListens"
    # cron or scheduled jobs
    RUN_RECENT_LISTENS_JOB = "runRecentListensJob"
    RUN_FULL_BACKFILL_JOB = "runFullBackfill"
    RUN_LOAD_UNKNOWN_TRACKS_JOBS = "runUnknownTracksBackfill"
    # errors
    ERROR_TRACKS_NOT_FOUND = "errorTrackNotFound"
