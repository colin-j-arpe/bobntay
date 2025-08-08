from bnt_parser.api_clients.genius_client import GeniusClient
from bnt_parser.api_clients.musixmatch_client import MusixmatchClient
from bnt_parser.tables.song_table import SongTable

class SongService:
    """
    Service class for handling song-related operations.
    """

    def __init__(
            self,
            song_table: SongTable,
            musixmatch_client: MusixmatchClient,
            genius_client: GeniusClient
    ):

    def parse_sections(self):
        """
        Parse the lyrics into sections.
        """
        self.sections = []

        if self.lyrics[0][0] != '[':
            # If the first line is not a section header, treat the entire lyrics as a single verse
            self.sections.push({
                'type': 'Verse',
                'song_order': 1,
                'lines': self.lyrics,
            })

            return

        section = None
        for line in self.lyrics:
            if line[0] == '[':
                if section:
                    # If we were already in a section, save it
                    self.sections.append(section)

                index_end = line.find(' ')
                if index_end == -1:
                    # If no space found, treat the whole line as a section type
                    index_end = line.find(']')
                section_type = line[1:index_end]
                section = {
                    'type': section_type,
                    'song_order': len(self.sections) + 1,  # Incremental order
                    'lines': [],
                }

            else:
                section['lines'].append(line)  # Add line to the current section

        self.sections.append(section)

    def save_song(self):
        """
        Save the song and its sections to the database.
        This method should be implemented to handle the actual saving logic.
        """
        # Placeholder for saving logic
        pass