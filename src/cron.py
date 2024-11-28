from Database import Database
from SpotifyClient import SpotifyClient

# initialize database and client
db = Database()
client = SpotifyClient()

# get most recent tracks from Spotify API
user = client.gen_current_user()
most_recent_ts = db.gen_most_recent_listen_time(user)
recent_tracks = client.gen_most_recent_tracks(most_recent_ts)

# TODO: upsert all new tracks to database
