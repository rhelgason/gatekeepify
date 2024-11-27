from Database import Database
from SpotifyClient import SpotifyClient

print("Loading database...")
db = Database()

# get most recent tracks from spotify API
client = SpotifyClient()
user = client.gen_current_user()
recent_tracks = client.gen_most_recent_tracks()
print(f"Got {len(recent_tracks)} recent tracks from Spotify API for user ID {user.name}.")

db.close()
print("Done.")
