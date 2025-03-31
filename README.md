# gatekeepify
Better gatekeep music from your friends by proving quantitatively how early and often you started listening to an artist.

## Usage
1. Clone the repo
2. Set up the chron job
3. Download your Spotify data
4. Upsert the Spotify data

## Backfill your Data
To get better functionality, you can backfill your data. This will allow you to see more information across your
all time listening history. To do this, you will need to:
1. Download your data from Spotify. Within a few days of your request, they will send you a zip file with your data.
2. Unzip the file to your machine.
3. Run the app and select the "Backfill my Data" option. The program will read each JSON file and upsert it to the database.
