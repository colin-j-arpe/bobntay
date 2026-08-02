from bnt_parser.models import ExternalSource, RejectedTrack


class RejectedTrackTable:
    """
    Class representing the rejected track table in the database.
    This class is responsible for managing records of tracks we chose not to store.
    """

    def is_rejected(self, api: ExternalSource.SourceEnum, id: int) -> bool:
        """
        Check whether a track has already been rejected.

        Deliberately keyed on the external ID alone, unlike
        ExternalSourceTable.song_exists() which also compares the endpoint. A
        rejection is a decision about the track itself, so it should hold however
        the track is reached.

        :param api: The source of the external ID (e.g., 'GENIUS').
        :param id: ID in the external API.
        :return: True if the track has been rejected, False otherwise.
        """
        return RejectedTrack.objects.filter(source=api, external_id=id).exists()

    def reject(
        self,
        api: ExternalSource.SourceEnum,
        id: int,
        endpoint: str,
        reason: RejectedTrack.ReasonEnum,
        title: str = "",
        artist: str = "",
    ) -> RejectedTrack:
        """
        Record a track as rejected; return the existing record if already rejected.

        Uses get_or_create so re-rejecting a track cannot raise on the unique
        constraint. The first reason recorded wins: a track can trip more than one
        filter, and which one fired first is not worth a write.

        :param api: The source of the external ID (e.g., 'GENIUS').
        :param id: ID in the external API.
        :param endpoint: The URL endpoint associated with the external ID.
        :param reason: Why the track was rejected.
        :param title: Track title, stored for auditing only.
        :param artist: Track artist, stored for auditing only.
        :return: The RejectedTrack object.
        """
        rejected_track, _ = RejectedTrack.objects.get_or_create(
            source=api,
            external_id=id,
            defaults={
                "endpoint": endpoint,
                "reason": reason,
                "title": title,
                "artist": artist,
            },
        )

        return rejected_track
