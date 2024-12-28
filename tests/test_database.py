import os
import unittest

from db.constants import DB_TEST_NAME

from db.Database import Database


class TestDatabase(unittest.TestCase):
    db: Database

    def setUp(self) -> None:
        self.db = Database(db_name=DB_TEST_NAME)

    def tearDown(self) -> None:
        if self.db.conn:
            self.db.conn.close()
        os.remove(DB_TEST_NAME)
