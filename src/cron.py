from db.Database import Database
from SpotifyClient import SpotifyClient

# initialize database and client
db = Database()
client = SpotifyClient()

# upsert most recent tracks from Spotify API
user = client.gen_current_user()
most_recent_ts = db.gen_most_recent_listen_time(user)
recent_listens = client.gen_most_recent_tracks(most_recent_ts)
db.upsert_cron_backfill(user, recent_listens)
