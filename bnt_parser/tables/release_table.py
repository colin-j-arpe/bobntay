from bnt_parser.models import Release, ExternalSource
from bnt_parser.clients.musixmatch_client import PATHS

class ReleaseTable:
    """
    Class representing the release table in the database.
    This class is responsible for managing release data.
    """

    def get_release_by_title(self, title: str, artist: str) -> Release | None:
        """
        Check if a release exists in the database.

        :param title: The title of the release.
        :param artist: The artist of the release.
        :return: True if the release exists, False otherwise.
        """
        release = Release.objects.filter(
            title__inexact=title,
            artist__inexact=artist
        ).first()
        
        if release is None:
            return None

        return release

    def save_if_not_exists(self, release_data: {}) -> Release:
        """
        Check if the album exists in the DB; save new record if not.

        :param release_data: Object from the Musixmatch API containing release data.
        :return: The saved Release DB ID.
        """
        existing_release_id = self.get_release_by_title(
            title=release_data['album_name'],
            artist=release_data['artist_name']
        )
        if existing_release_id is not None:
            return existing_release_id

        album_source = ExternalSource(
            source=ExternalSource.SourceEnum.MUSIXMATCH,
            external_id=release_data['album_id'],
            endpoint=f"{PATHS['album']}?album_id={release_data['album_id']}",
        )
        album_source.save()

        release = Release(
            artist=release_data['artist_name'],
            title=release_data['album_name'],
            release_date=release_data['album_release_date'],
            label=release_data['album_label'],
            external_source=album_source,
        )
        release.save()

        return release
