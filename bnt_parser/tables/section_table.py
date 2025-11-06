import re
from bnt_parser.models import Section, Song

class SectionTable:
    """
    Class representing the section table in the database.
    This class is responsible for managing section data.
    """

    def save(self, song: Song, section_data: dict, multiple_sections = False) -> Section:
        """
        Save a new section record in the DB.

        :param song: Song object the section belongs to.
        :param section_data: Object containing section data.
        :param multiple_sections: Use "Verse" or "Other" for unnamed sections
        :return: The saved Section object.
        """
        # Default to Verse if type is not recognized
        non_letter_pattern = re.compile('\\W')
        type_input = non_letter_pattern.sub('', section_data['type'].upper())
        if type_input in Section.SectionTypeEnum.names:
            try:
                section_type = Section.SectionTypeEnum[type_input]
            except KeyError:
                section_type = Section.SectionTypeEnum.VERSE
        elif multiple_sections:
            section_type = Section.SectionTypeEnum.OTHER
        else:
            section_type = Section.SectionTypeEnum.VERSE

        section = Section(
            song=song,
            order=section_data['song_order'],
            type=section_type,
        )
        section.save()

        return section