from bnt_parser.models import Section, Line


class LineTable:
    def save(self, lyrics: str, order: int, section: Section) -> Line:
        """
        Save a new line record in the DB.

        :param lyrics: The lyrics of the line.
        :param order: The order of the line within the section.
        :param section: The Section object the line belongs to.
        """
        line = Line(
            lyrics=lyrics,
            order=order,
            section=section,
        )
        line.save()

        return line