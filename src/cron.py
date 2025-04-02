from datetime import datetime

from spotify.spotify_client import SpotifyClient

client = SpotifyClient()
if datetime.now().minute % 20 == 0:
    client.gen_run_cron_recent_listens()
else:
    client.gen_run_cron_unknown_tracks()
