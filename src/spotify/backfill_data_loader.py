import json
import os
from typing import Dict, List, Optional

from db.constants import DB_NAME, DB_TEST_NAME
from db.Database import Database

FILE_PREFIX = "Streaming_History_Audio"
FILE_SUFFIX = ".json"


class BackfillDataLoader:
    db: Database
    directory_path: str
    listens_json: List[Dict[str, Optional[int | str | bool]]]

    def __init__(self, is_test: bool = False) -> None:
        self.db = Database(db_name=DB_TEST_NAME if is_test else DB_NAME)
        self.directory_path = input("Enter absolute path to Spotify data directory: ")

        # check if directory exists
        if not os.path.exists(self.directory_path):
            raise ValueError(f"Directory {self.directory_path} does not exist.")

        # load listens from each .json file in directory
        self.listens_json = []
        for file in os.listdir(self.directory_path):
            if file.startswith(FILE_PREFIX) and file.endswith(FILE_SUFFIX):
                with open(os.path.join(self.directory_path, file), "r") as f:
                    json_arr = json.load(f)
                    self.listens_json.extend(json_arr)

    def validate_listens(self) -> None:
        pass

    def write_listens(self) -> None:
        pass
