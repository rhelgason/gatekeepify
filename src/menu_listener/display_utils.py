from datetime import datetime, timedelta

from menu_listener.menu_listener import MenuListener
from menu_listener.menu_options import DateOptions, MainMenuOptions, StatViewerOptions
from spotify.backfill_data_loader import BackfillDataLoader
from spotify.stat_viewer import StatViewer


def use_main_menu():
    main_menu = MenuListener[MainMenuOptions](
        menu_options=MainMenuOptions,
        message="Welcome to Gatekeepify! Select one of the following options:",
    )
    option = main_menu.use_menu()

    while option != MainMenuOptions.QUIT:
        if option == MainMenuOptions.SPOTIFY_WRAPPED:
            use_spotify_wrapped()
        elif option == MainMenuOptions.VIEW_MY_STATS:
            use_view_my_stats()
        elif option == MainMenuOptions.BACKFILL_MY_DATA:
            use_backfill_my_data()
        option = main_menu.use_menu()


def use_spotify_wrapped():
    start_of_year_ds = datetime(datetime.now().year, 1, 1)
    stat_viewer = StatViewer(start_of_year_ds)
    stat_viewer.all_stats()
    return 0


def use_view_my_stats():
    date_menu = MenuListener[DateOptions](
        menu_options=DateOptions,
        message="Please select a date range to view your stats for:",
    )
    stats_menu = MenuListener[StatViewerOptions](
        menu_options=StatViewerOptions,
        message="Please select a stat to view:",
    )
    date_option = date_menu.use_menu()

    while date_option != DateOptions.RETURN:
        earliest_ds = None
        if date_option == DateOptions.TODAY:
            earliest_ds = datetime.today()
        elif date_option == DateOptions.LAST_MONTH:
            earliest_ds = datetime.today() - timedelta(days=30)
        elif date_option == DateOptions.LAST_YEAR:
            earliest_ds = datetime.today() - timedelta(days=365)
        stat_viewer = StatViewer(earliest_ds)

        stat_option = stats_menu.use_menu()
        while stat_option != StatViewerOptions.RETURN:
            if stat_option == StatViewerOptions.TOP_TRACKS:
                stat_viewer.top_tracks()
            elif stat_option == StatViewerOptions.TOP_ARTISTS:
                stat_viewer.top_artists()
            elif stat_option == StatViewerOptions.TOP_GENRES:
                stat_viewer.top_genres()
            stat_option = stats_menu.use_menu()
        date_option = date_menu.use_menu()
    return 0


def use_backfill_my_data():
    data_loader = BackfillDataLoader()
    data_loader.write_listens()
    return 0
