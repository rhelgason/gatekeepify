import os
import sqlite3
from datetime import datetime
from spotify.types import Album, Artist, Track, User
from typing import Dict, List, Set

DB_DIRECTORY = "db"
DB_NAME = "database.db"

"""
Database setup for Gatekeepify. Currently includes the following tables:
- dim_all_tracks: stores information about every track
- dim_all_artists: stores information about every artist
- dim_all_albums: stores information about every album
- track_to_artist: mapping table between tracks and artists
- dim_all_users: stores information about every user
- dim_all_listens: stores every track listened to by every user
"""
class Database:
    def __init__(self, db_name=DB_NAME):
        path = os.path.join(DB_DIRECTORY, db_name)
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()
        self.__create_all_tables()

    """
    METHODS FOR CREATING ALL TABLES
    """
    def __create_all_tables(self):
        self.__create_dim_all_albums()
        self.__create_dim_all_tracks()
        self.__create_dim_all_artists()
        self.__create_track_to_artist()
        self.__create_dim_all_users()
        self.__create_dim_all_listens()

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

    """
    METHODS FOR UPSERTING DATA INTO ALL TABLES
    """
    def upsert_all_tables(self, user: User, listens: Dict[datetime, Track]):
        all_tracks = set(listens.values())
        all_albums = set([track.album for track in all_tracks])
        all_artists = set([artist for track in all_tracks for artist in track.artists])

        self.__upsert_dim_all_albums(all_albums)
        self.__upsert_dim_all_tracks(all_tracks)
        self.__upsert_dim_all_artists(all_artists)
        self.__upsert_track_to_artist(all_tracks)
        self.__upsert_dim_all_users(user)
        self.__upsert_dim_all_listens(user, listens)
    
    # upserts albums into dim_all_albums
    def __upsert_dim_all_albums(self, albums: Set[Album]):
        query = """
        INSERT INTO dim_all_albums (album_id, album_name)
        VALUES (?, ?)
        ON CONFLICT (album_id) DO UPDATE SET album_name=excluded.album_name
        """
        self.cursor.executemany(query, [(album.id, album.name) for album in albums])
        self.conn.commit()

    # upserts tracks into dim_all_tracks
    def __upsert_dim_all_tracks(self, tracks: Set[Track]):
        query = """
        INSERT INTO dim_all_tracks (track_id, track_name, album_id)
        VALUES (?, ?, ?)
        ON CONFLICT (track_id) DO UPDATE SET track_name=excluded.track_name, album_id=excluded.album_id
        """
        self.cursor.executemany(query, [(track.id, track.name, track.album.id) for track in tracks])
        self.conn.commit()

    # upserts artists into dim_all_artists
    def __upsert_dim_all_artists(self, artists: Set[Artist]):
        query = """
        INSERT INTO dim_all_artists (artist_id, artist_name)
        VALUES (?, ?)
        ON CONFLICT (artist_id) DO UPDATE SET artist_name=excluded.artist_name
        """
        self.cursor.executemany(query, [(artist.id, artist.name) for artist in artists])
        self.conn.commit()

    # upserts tracks to artists into track_to_artist
    def __upsert_track_to_artist(self, tracks: Set[Track]):
        query = """
        INSERT INTO track_to_artist (track_id, artist_id)
        VALUES (?, ?)
        ON CONFLICT (track_id, artist_id) DO NOTHING
        """
        self.cursor.executemany(query, [(track.id, artist.id) for track in tracks for artist in track.artists])
        self.conn.commit()
    
    # upserts users into dim_all_users
    def __upsert_dim_all_users(self, user: User):
        query = """
        INSERT INTO dim_all_users (user_id, user_name)
        VALUES (?, ?)
        ON CONFLICT (user_id) DO UPDATE SET user_name=excluded.user_name
        """
        self.cursor.execute(query, (user.id, user.name))
        self.conn.commit()
    
    # upserts listens into dim_all_listens
    def __upsert_dim_all_listens(self, user: User, listens: Dict[datetime, Track]):
        query = """
        INSERT INTO dim_all_listens (user_id, track_id, ts)
        VALUES (?, ?, ?)
        ON CONFLICT (user_id, track_id, ts) DO NOTHING
        """
        self.cursor.executemany(query, [(user.id, track.id, ts) for ts, track in listens.items()])
        self.conn.commit()

    def close(self):
        self.conn.close()
