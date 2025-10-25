from bnt_parser.models import Song, Writer, Release, ExternalSource

class SongTable:
    """
    Class representing the song table in the database.
    This class is responsible for managing song data, including sections and lyrics.
    """

    def find_song(self, title: str, artist: str, release_title: str):
        from bnt_parser.models import Song
        return Song.objects.filter(
            title__inexact=title,
            artist__inexact=artist,
            release__title__inexact=release_title
        ).first()

    def song_exists(self, title: str, artist: str, release_title: str) -> bool:
        """
        Check if a song exists in the database.

        :param title: The title of the song.
        :param artist: The artist of the song.
        :param release_title: The release title of the song.
        :return: True if the song exists, False otherwise.
        """
        song = self.find_song(title, artist, release_title)

        return song is not None

    def save_if_not_exists(self, title: str, artist: str, release: Release, external_source: ExternalSource, writers: list[Writer]) -> Song:
        existing_song = self.find_song(title, artist, release.title)
        if existing_song:
            return existing_song.id

        from bnt_parser.models import Song
        song = Song(
            title=title,
            artist=artist,
            release=release,
            external_source=external_source,
            writers=writers,
        )
        song.save()
        return song



