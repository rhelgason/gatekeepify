# gatekeepify
Better gatekeep music from your friends by proving quantitatively how early and often you started listening to an artist.

## Usage
1. Clone the repo
2. Set up the cron jobs (see below).
3. Download your Spotify data
4. Upsert the Spotify data

## Backfill your Data
To get better functionality, you can backfill your data. This will allow you to see more information across your all time listening history. To do this, you will need to:
1. Download your data from Spotify. Within a few days of your request, they will send you a zip file with your data.
2. Unzip the file to your machine.
3. Run the app and select the "Backfill my Data" option. The program will read each JSON file and upsert it to the database.

## Cron Jobs
There are two cron jobs that you will want to set up in order to keep your data active:
1. Fetch recent listens: this job keeps a constantly updated list of your Spotify listening data. We can only fetch the 50 most recent listens (each of at least 30 seconds), so this job should run about every 20 minutes. Example crontab entry: `*/20 * * * * cd <gatekeepify path> && python3 src/cron_recent_listens.py`
2. If we ever do a one-time backfill of all Spotify listening history for a user, we will almost certainly have some gaps in track data. We solve this problem with an occasional job for backfilling additional track data (album, artists, duration). We still want to avoid Spotify API rate-limiting, so we run this job about every 1 minute. Example crontab entry: ``
