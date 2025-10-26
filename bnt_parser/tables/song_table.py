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

    def save_if_not_exists(self, song_record: dict, album_object: dict) -> Song:
        existing_song = self.find_song(
            title=song_record['title'],
            artist=song_record['primary_artist']['name'],
            release_title=album_object['title']
        )
        if existing_song:
            return existing_song.id

        from bnt_parser.models import ExternalSource
        song_source = ExternalSource(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=song_record['id'],
            endpoint=song_record['api_path'],
        )

        from bnt_parser.models import Song
        song = Song(
            title=song_record['title'],
            artist=song_record['primary_artist']['name'],
            release=album_object,
            external_source=song_source,
            writers=song_record['writer_artists'],
        )
        song.save()
        return song



