from spotify.spotify_client import SpotifyClient

"""
Fetches Spotify API data for unknown tracks and upserts them into database.
Should be associated with a cron job about every one minute to avoid API
rate limits.
"""
client = SpotifyClient()
client.gen_run_cron_unknown_tracks()
