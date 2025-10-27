from bnt_parser.models import Release, ExternalSource

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

    def get_release_by_source(self, external_id: int) -> Release | None:
        """
        Check if a release exists in the database by its external source ID.

        :param external_id: The ID of the release in the external API.
        :return: The Release object if it exists, None otherwise.
        """
        release = Release.objects.filter(
            external_source__external_id=external_id
        ).first()

        if release is None:
            return None

        return release

    def save_if_not_exists(self, release_data: dict) -> Release:
        """
        Check if the album exists in the DB; save new record if not.

        :param release_data: Object from the Genius API containing release data.
        :return: The saved Release DB ID.
        """
        existing_release = self.get_release_by_source(
            external_id=release_data['id']
        )
        if existing_release is not None:
            return existing_release

        album_source = ExternalSource(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=release_data['id'],
            endpoint=release_data['api_path'],
        )
        album_source.save()

        release = Release(
            artist=release_data['primary_artist_names'],
            title=release_data['name'],
            release_date=release_data['release_date'],
            label=release_data.get('label', ''),
            external_source=album_source,
        )
        release.save()

        return release
