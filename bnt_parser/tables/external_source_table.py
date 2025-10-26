from bnt_parser.models import ExternalSource

class ExternalSourceTable():
    """
    Class representing the external source table in the database.
    This class is responsible for managing external source data.
    """

    def save(self, source: str, external_id: int, endpoint: str) -> ExternalSource:
        """
        Check if the external source exists in the DB; save new record if not.

        :param source: The source of the external ID (e.g., 'GENIUS').
        :param external_id: The external ID to look for.
        :param endpoint: The URL endpoint associated with the external ID.
        :return: The saved ExternalSource object.
        """
        external_source = ExternalSource(
            source=source,
            external_id=external_id,
            endpoint=endpoint,
        )
        external_source.save()

        return external_source

    def song_exists(self, api: ExternalSource.SourceEnum, id: int, url: str) -> bool:
        """
        Check if an external source exists in the database.

        :param api: The source of the external ID (e.g., 'GENIUS').
        :param id: ID in the external API.
        :param url: The URL endpoint associated with the external ID.
        :return: True if the external source exists, False otherwise.
        """
        external_source_results = ExternalSource.objects.filter(
            source=api,
            external_id=id
        ).all()

        for source in external_source_results:
            if source.endpoint == url:
                return True

        return False