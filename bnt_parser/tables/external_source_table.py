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
