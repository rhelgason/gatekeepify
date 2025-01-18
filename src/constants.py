import os
CLIENT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
HOST_CONSTANTS_PATH = "src/host_constants"
HOST_CONSTANTS_TEST_PATH = "src/host_constants_test"
# must EXACTLY match the redirect URI in Spotify Developer Dashboard
REDIRECT_URI = os.environ.get("GATEKEEPIFY_REDIRECT_URI")
if REDIRECT_URI is None:
    REDIRECT_URI = input("Please input your Spotify API redirect URI: ")
DEFAULT_SCOPE = "user-read-private user-read-email user-read-recently-played"
MAXIMUM_RECENT_TRACKS = 50
APP_TITLE = """
  ____       _       _                   _  __
 \\/ ___| __ _| |_ ___| | _____  ___ _ __ (_)/ _|_   _
| |  _ / _` | __/ _ \\ |/ / _ \\/ _ \\ '_ \\| | |_| | | |
| |_| | (_| | ||  __/   <  __/  __/ |_) | |  _| |_| |
 \\____|\\__,_|\\__\\___|_|\\_\\___|\\___| .__/|_|_|  \\__, |
                                  |_|          |___/
"""
