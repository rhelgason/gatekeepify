import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Set

from db.constants import DB_DATETIME_FORMAT, DB_DIRECTORY, DB_NAME, LoggerAction
from spotify.types import Album, Artist, Listen, Track, User

"""
Database setup for Gatekeepify. Currently includes the following tables:
- dim_all_tracks: stores information about every track
- dim_all_artists: stores information about every artist
- dim_all_albums: stores information about every album
- track_to_artist: mapping table between tracks and artists
- dim_all_users: stores information about every user
- dim_all_listens: stores every track listened to by every user
- dim_possible_missing_data: stores information for ts that may not be tracked
- dim_all_logs: stores logging data for every program action
"""


class Database:
    def __init__(self, db_name=DB_NAME):
        if not os.path.exists(DB_DIRECTORY):
            os.makedirs(DB_DIRECTORY)
        path = os.path.join(DB_DIRECTORY, db_name)
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()
        self.__create_all_tables()

    def __del__(self):
        self.conn.close()

    """
    METHODS FOR CREATING ALL TABLES
    """

    def __create_all_tables(self):
        self.__create_dim_all_albums()
        self.__create_dim_all_tracks()
        self.__create_dim_all_artists()
        self.__create_track_to_artist()
        self.__create_artist_to_genre()
        self.__create_dim_all_users()
        self.__create_dim_all_listens()
        self.__create_dim_all_logs()

    # table for storing information about every album
    def __create_dim_all_albums(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_albums (
            album_id VARCHAR(255) PRIMARY KEY,
            album_name VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every track
    def __create_dim_all_tracks(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_tracks (
            track_id VARCHAR(255) PRIMARY KEY,
            track_name VARCHAR(255),
            album_id VARCHAR(255),
            duration_ms INTEGER,
            is_local BOOLEAN,
            FOREIGN KEY(album_id) REFERENCES dim_all_albums(album_id)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every artist
    def __create_dim_all_artists(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_artists (
            artist_id VARCHAR(255) PRIMARY KEY,
            artist_name VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # mapping table between tracks and artists
    def __create_track_to_artist(self):
        query = """
        CREATE TABLE IF NOT EXISTS track_to_artist (
            track_id VARCHAR(255),
            artist_id VARCHAR(255),
            PRIMARY KEY(track_id, artist_id),
            FOREIGN KEY(track_id) REFERENCES dim_all_tracks(track_id),
            FOREIGN KEY(artist_id) REFERENCES dim_all_artists(artist_id)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # mapping table between artists and genres
    def __create_artist_to_genre(self):
        query = """
        CREATE TABLE IF NOT EXISTS artist_to_genre (
            artist_id VARCHAR(255),
            genre VARCHAR(255),
            PRIMARY KEY(artist_id, genre),
            FOREIGN KEY(artist_id) REFERENCES dim_all_artists(artist_id)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every user
    def __create_dim_all_users(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_users (
            user_id VARCHAR(255) PRIMARY KEY,
            user_name VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table that stores every track listened to by every user
    def __create_dim_all_listens(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_listens (
            user_id VARCHAR(255),
            track_id VARCHAR(255),
            ts DATETIME,
            PRIMARY KEY(user_id, track_id, ts),
            FOREIGN KEY(user_id) REFERENCES dim_all_users(user_id),
            FOREIGN KEY(track_id) REFERENCES dim_all_tracks(track_id)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # logging table for storing every program action
    def __create_dim_all_logs(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_logs (
            ts DATETIME,
            action VARCHAR(255),
            metadata TEXT,
            PRIMARY KEY(ts, action)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    """
    METHODS FOR UPSERTING DATA INTO ALL TABLES
    """

    # top-level upsert method for all tables
    def upsert_all_tables(self, listens: List[Listen]):
        all_tracks = set(listen.track for listen in listens)
        all_users = set(listen.user for listen in listens)
        all_albums = set([track.album for track in all_tracks])
        all_artists = set([artist for track in all_tracks for artist in track.artists])

        self.__upsert_dim_all_albums(all_albums)
        self.__upsert_dim_all_tracks(all_tracks)
        self.__upsert_dim_all_artists(all_artists)
        self.__upsert_track_to_artist(all_tracks)
        self.__upsert_artist_to_genre(all_artists)
        self.__upsert_dim_all_users(all_users)
        self.__upsert_dim_all_listens(listens)

    # upserts all tables with logs for the current cron job
    def upsert_cron_backfill(self, listens: List[Listen]):
        self.upsert_all_tables(listens)
        log_json = {
            "listens": [listen.to_json_str() for listen in listens],
        }
        self.__upsert_dim_all_logs(LoggerAction.RUN_CRON_BACKFILL, json.dumps(log_json))

    # upserts albums into dim_all_albums
    def __upsert_dim_all_albums(self, albums: Set[Album]):
        query = """
        INSERT INTO dim_all_albums (album_id, album_name)
        VALUES (?, ?)
        -- update if album has updated its name
        ON CONFLICT (album_id) DO UPDATE SET album_name=excluded.album_name
        """
        self.cursor.executemany(query, [(album.id, album.name) for album in albums])
        self.conn.commit()
        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_DIM_ALL_ALBUMS,
            json.dumps([album.to_json_str() for album in albums]),
        )

    # upserts tracks into dim_all_tracks
    def __upsert_dim_all_tracks(self, tracks: Set[Track]):
        query = """
        INSERT INTO dim_all_tracks (track_id, track_name, album_id, duration_ms, is_local)
        VALUES (?, ?, ?, ?, ?)
        -- update if track has updated its name, album, duration, or is_local flag
        ON CONFLICT (track_id) DO UPDATE SET track_name=excluded.track_name, album_id=excluded.album_id, duration_ms=excluded.duration_ms, is_local=excluded.is_local
        """
        self.cursor.executemany(
            query,
            [
                (
                    track.id,
                    track.name,
                    track.album.id,
                    track.duration_ms,
                    track.is_local,
                )
                for track in tracks
            ],
        )
        self.conn.commit()
        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_DIM_ALL_TRACKS,
            json.dumps([track.to_json_str() for track in tracks]),
        )

    # upserts artists into dim_all_artists
    def __upsert_dim_all_artists(self, artists: Set[Artist]):
        query = """
        INSERT INTO dim_all_artists (artist_id, artist_name)
        VALUES (?, ?)
        -- update if artist has updated their name
        ON CONFLICT (artist_id) DO UPDATE SET artist_name=excluded.artist_name
        """
        self.cursor.executemany(query, [(artist.id, artist.name) for artist in artists])
        self.conn.commit()
        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_DIM_ALL_ARTISTS,
            json.dumps([artist.to_json_str() for artist in artists]),
        )

    # upserts tracks to artists into track_to_artist
    def __upsert_track_to_artist(self, tracks: Set[Track]):
        # remove artists that are no longer associated with track
        query = """
        DELETE FROM track_to_artist
        WHERE track_id=?
        AND artist_id NOT IN (?)
        """
        self.cursor.executemany(
            query,
            [
                (
                    track.id,
                    ", ".join(map(str, track.artists)),
                )
                for track in tracks
            ],
        )
        self.conn.commit()

        # upsert new tracks to artists
        query = """
        INSERT INTO track_to_artist (track_id, artist_id)
        VALUES (?, ?)
        -- do nothing, as track to artist mapping already exists
        ON CONFLICT (track_id, artist_id) DO NOTHING
        """
        self.cursor.executemany(
            query,
            [(track.id, artist.id) for track in tracks for artist in track.artists],
        )
        self.conn.commit()

        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_TRACK_TO_ARTIST,
            json.dumps([track.to_json_str() for track in tracks]),
        )

    # upserts genres to artists into artist_to_genre
    def __upsert_artist_to_genre(self, artists: Set[Artist]):
        # remove genres that are no longer associated with artist
        query = """
        DELETE FROM artist_to_genre
        WHERE artist_id=?
        AND genre NOT IN (?)
        """
        self.cursor.executemany(
            query,
            [
                (
                    artist.id,
                    ", ".join(artist.genres),
                )
                for artist in artists
            ],
        )
        self.conn.commit()

        # upsert new genres to artists
        query = """
        INSERT INTO artist_to_genre (artist_id, genre)
        VALUES (?, ?)
        -- do nothing, as artist to genre mapping already exists
        ON CONFLICT (artist_id, genre) DO NOTHING
        """
        self.cursor.executemany(
            query, [(artist.id, genre) for artist in artists for genre in artist.genres]
        )
        self.conn.commit()

        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_ARTIST_TO_GENRE,
            json.dumps([artist.to_json_str() for artist in artists]),
        )

    # upserts users into dim_all_users
    def __upsert_dim_all_users(self, users: Set[User]):
        query = """
        INSERT INTO dim_all_users (user_id, user_name)
        VALUES (?, ?)
        -- update if user has updated their name
        ON CONFLICT (user_id) DO UPDATE SET user_name=excluded.user_name
        """
        self.cursor.executemany(query, [(user.id, user.name) for user in users])
        self.conn.commit()
        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_DIM_ALL_USERS,
            json.dumps([user.to_json_str() for user in users]),
        )

    # upserts listens into dim_all_listens
    def __upsert_dim_all_listens(self, listens: List[Listen]):
        query = """
        INSERT INTO dim_all_listens (user_id, track_id, ts)
        VALUES (?, ?, ?)
        -- do nothing, as listen already exists for that user and time
        ON CONFLICT (user_id, track_id, ts) DO NOTHING
        """
        self.cursor.executemany(
            query, [(listen.user.id, listen.track.id, listen.ts) for listen in listens]
        )
        self.conn.commit()

        log_json = {
            "listens": [listen.to_json_str() for listen in listens],
        }
        self.__upsert_dim_all_logs(
            LoggerAction.UPSERT_DIM_ALL_LISTENS, json.dumps(log_json)
        )

    # upserts logs into dim_all_logs
    def __upsert_dim_all_logs(self, action: LoggerAction, metadata: str):
        query = """
        INSERT INTO dim_all_logs (ts, action, metadata)
        VALUES (?, ?, ?)
        """
        self.cursor.execute(query, (datetime.now(), action.value, metadata))
        self.conn.commit()

    """
    METHODS FOR QUERYING ALL TABLES
    """

    def get_all_albums(self) -> Set[Album]:
        query = """
        SELECT album_id, album_name FROM dim_all_albums
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return {Album(row[0], row[1]) for row in results}

    def get_all_tracks(self, track_ids: Optional[List[str]] = None) -> Set[Track]:
        query = """
        SELECT
            t.track_id,
            track_name,
            t.album_id,
            album_name,
            duration_ms,
            is_local,
            JSON_GROUP_ARRAY(JSON_ARRAY(ar.artist_id, ar.artist_name, ar.genres)) artists
        FROM dim_all_tracks t
        LEFT JOIN dim_all_albums al ON t.album_id=al.album_id
        LEFT JOIN track_to_artist ta ON t.track_id=ta.track_id
        LEFT JOIN (
            SELECT
                a.artist_id,
                artist_name,
                JSON_GROUP_ARRAY(genre) genres
            FROM dim_all_artists a
            LEFT JOIN artist_to_genre ag ON ag.artist_id=a.artist_id
            GROUP BY a.artist_id, artist_name
        ) ar ON ta.artist_id=ar.artist_id
        """
        if track_ids:
            query += "WHERE t.track_id IN (" + ", ".join(track_ids) + ")"
        query += "GROUP BY t.track_id, track_name, t.album_id, album_name, duration_ms, is_local"

        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return {
            Track(
                row[0],
                row[1],
                Album(row[2], row[3]),
                [
                    Artist(artist[0], artist[1], json.loads(artist[2]))
                    for artist in json.loads(row[6])
                ],
                row[4],
                row[5],
            )
            for row in results
        }

    def get_all_artists(self) -> Set[Artist]:
        query = """
        SELECT
            ar.artist_id,
            artist_name,
            JSON_GROUP_ARRAY(genre) genres
        FROM dim_all_artists ar
        LEFT JOIN artist_to_genre ag ON ar.artist_id=ag.artist_id
        GROUP BY ar.artist_id, artist_name
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return {Artist(row[0], row[1], json.loads(row[2])) for row in results}

    def get_all_users(self) -> Set[User]:
        query = """
        SELECT user_id, user_name FROM dim_all_users
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return {User(row[0], row[1]) for row in results}

    def get_all_listens(
        self, user: Optional[User] = None, ds: Optional[datetime] = None
    ) -> Set[Listen]:
        query = """
        SELECT
            l.user_id,
            u.user_name,
            ts,
            t.track_id,
            track_name,
            t.album_id,
            album_name,
            duration_ms,
            is_local,
            JSON_GROUP_ARRAY(JSON_ARRAY(ar.artist_id, ar.artist_name, ar.genres)) artists
        FROM dim_all_listens l
        LEFT JOIN dim_all_users u ON l.user_id=u.user_id
        LEFT JOIN dim_all_tracks t ON l.track_id=t.track_id
        LEFT JOIN dim_all_albums al ON t.album_id=al.album_id
        LEFT JOIN track_to_artist ta ON t.track_id=ta.track_id
        LEFT JOIN (
            SELECT
                a.artist_id,
                artist_name,
                JSON_GROUP_ARRAY(genre) genres
            FROM dim_all_artists a
            LEFT JOIN artist_to_genre ag ON ag.artist_id=a.artist_id
            GROUP BY a.artist_id, artist_name
        ) ar ON ta.artist_id=ar.artist_id
        WHERE
            CASE WHEN ? IS NOT NULL THEN l.user_id = ? ELSE TRUE END
            AND CASE WHEN ? IS NOT NULL THEN ts >= ? ELSE TRUE END
        GROUP BY l.user_id, u.user_name, ts, t.track_id, track_name, t.album_id, album_name
        """
        user_id = user.id if user else None
        ts = ds.strftime(DB_DATETIME_FORMAT) if ds else None

        self.cursor.execute(query, (user_id, user_id, ts, ts))
        results = self.cursor.fetchall()
        return {
            Listen(
                User(row[0], row[1]),
                Track(
                    row[3],
                    row[4],
                    Album(row[5], row[6]),
                    [
                        Artist(artist[0], artist[1], json.loads(artist[2]))
                        for artist in json.loads(row[9])
                    ],
                    row[7],
                    row[8],
                ),
                datetime.strptime(row[2], DB_DATETIME_FORMAT),
            )
            for row in results
        }

    # query most recent listen time for a user
    def get_most_recent_listen_time(self, user: User) -> Optional[datetime]:
        query = """
        SELECT MAX(ts) FROM dim_all_listens WHERE user_id=?
        """
        self.cursor.execute(query, (user.id,))
        result = self.cursor.fetchone()
        return datetime.strptime(result[0], DB_DATETIME_FORMAT) if result[0] else None
