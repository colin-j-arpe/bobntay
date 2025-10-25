from bnt_parser.models import Section, Song

class SectionTable:
    """
    Class representing the section table in the database.
    This class is responsible for managing section data.
    """

    def save(self, song: Song, section_data: dict) -> Section:
        """
        Save a new section record in the DB.

        :param song: Song object the section belongs to.
        :param section_data: Object containing section data.
        :return: The saved Section object.
        """
        section = Section(
            song=song,
            order=section_data['song_order'],
            type=section_data['type'],
        )
        section.save()

        return section