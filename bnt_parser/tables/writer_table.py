from bnt_parser.models import Writer, ExternalSource, Song
from bnt_parser.tables.external_source_table import ExternalSourceTable

class WriterTable():
    """
    Class representing the writer table in the database.
    This class is responsible for managing writer data.
    """

    def get_writer_by_name(self, name: str) -> Writer | None:
        """
        Check if a writer exists in the database.

        :param name: The name of the writer.
        :return: The ID of the writer if it exists, None otherwise.
        """
        writer = Writer.objects.filter(name__iexact=name).first()

        if writer is None:
            return None

        return writer

    def save_if_not_exists(self, writer_data: dict, song: Song) -> Writer:
        """
        Check if the writer exists in the DB; save new record if not.

        :param writer_data: Object from Genius API.
        :return: The saved Writer DB ID.
        """
        existing_writer = self.get_writer_by_name(writer_data['name'])
        if existing_writer is not None:
            return existing_writer

        external_source = ExternalSourceTable().save(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=writer_data['id'],
            endpoint=writer_data['api_path'],
        )

        writer = Writer(
            name=writer_data['name'],
            external_source=external_source,
        )
        writer.save()

        writer.songs.add(song)
        writer.save()

        return writer