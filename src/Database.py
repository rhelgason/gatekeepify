import os
import sqlite3
from datetime import datetime
from spotify.types import Track
from typing import Dict

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
        self.__create_tables()

    def __create_tables(self):
        self.__create_dim_all_tracks()
        self.__create_dim_all_artists()
        self.__create_dim_all_albums()
        self.__create_track_to_artist()
        self.__create_dim_all_users()
        self.__create_dim_all_listens()

    # table for storing information about every track
    def __create_dim_all_tracks(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_tracks (
            track_id VARCHAR(255),
            track_name VARCHAR(255),
            album_id VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every artist
    def __create_dim_all_artists(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_artists (
            artist_id VARCHAR(255),
            artist_name VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every album
    def __create_dim_all_albums(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_albums (
            album_id VARCHAR(255),
            album_name VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # mapping table between tracks and artists
    def __create_track_to_artist(self):
        query = """
        CREATE TABLE IF NOT EXISTS track_to_artist (
            track_id VARCHAR(255),
            artist_id VARCHAR(255)
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    # table for storing information about every user
    def __create_dim_all_users(self):
        query = """
        CREATE TABLE IF NOT EXISTS dim_all_users (
            user_id VARCHAR(255),
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
            ts DATETIME
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    def update_listened_tracks(self, tracks: Dict[datetime, Track]):
        pass

    def close(self):
        self.conn.close()
