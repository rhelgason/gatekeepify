from db.Database import Database
from SpotifyClient import SpotifyClient

"""
Upserts most recent tracks from Spotify API into database.
Should be associated with a cron job at least every 25 minutes.
This is because Spotify API returns a maximum of 50 tracks, and
they only record a listen if the track was played at least 30 seconds.
"""
client = SpotifyClient()
user = client.gen_current_user()
client.gen_run_cron_backfill(user)
