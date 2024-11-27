from Database import Database
from SpotifyClient import SpotifyClient

print("Loading database...")
db = Database()

# get most recent tracks from spotify API
client = SpotifyClient()
user = client.gen_current_user()
recent_tracks = client.gen_most_recent_tracks()
print(f"Got {len(recent_tracks)} recent tracks from Spotify API for user ID {user.name}.")

# upsert all data into database
print("Upserting data into database...")
db.upsert_all_tables(user, recent_tracks)
print("Done.")
db.close()
