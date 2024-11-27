from Database import Database
from SpotifyClient import SpotifyClient

print("Loading database...")
db = Database()

# get most recent tracks from spotify API
client = SpotifyClient()
client.gen_upsert_most_recent_tracks()

db.close()
print("Done.")
