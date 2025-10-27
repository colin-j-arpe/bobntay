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
        # Default to Verse if type is not recognized
        if section_data['type'] in Section.SectionTypeEnum.labels:
            try:
                section_type = Section.SectionTypeEnum[section_data['type'].upper()]
            except KeyError:
                section_type = Section.SectionTypeEnum.VERSE
        else:
            section_type = Section.SectionTypeEnum.VERSE

        section = Section(
            song=song,
            order=section_data['song_order'],
            type=section_type,
        )
        section.save()

        return section