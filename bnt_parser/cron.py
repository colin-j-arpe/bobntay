from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.clients.musixmatch_client import MusixmatchClient
from bnt_parser.services.song_service import SongService
from bnt_parser.tables.song_table import SongTable


def add_song():
    """
    Placeholder function for adding a song.
    This function is intended to be called by a cron job.
    """
    song_table = SongTable()  # Replace with actual DB connection if needed
    mxm_client = MusixmatchClient()
    gen_client = GeniusClient()
    song_service = SongService(song_table, mxm_client, gen_client)

    song_service.select_song()
    song_service.parse_sections()
    song_service.save_song()

    # Here you would implement the logic to add a song, e.g., fetching from an API
    print("Cron job executed: add_song function called.")