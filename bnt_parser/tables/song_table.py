from bnt_parser.models import Song

class SongTable:
    """
    Class representing the song table in the database.
    This class is responsible for managing song data, including sections and lyrics.
    """

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.table_name = 'songs'

    def song_exists(self, title: str, artist: str, release_title: str) -> bool:
        """
        Check if a song exists in the database.

        :param title: The title of the song.
        :param artist: The artist of the song.
        :param release_title: The release title of the song.
        :return: True if the song exists, False otherwise.
        """
        song = Song.objects.filter(
            title__inexact=title,
            artist__inexact=artist,
            release__title__inexact=release_title
        ).first()

        return song is not None