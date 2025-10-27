import logging
import re
from re import Pattern

from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.models import ExternalSource
from bnt_parser.services.table_service import TableService
from bnt_parser.utils.genius_page import GeniusPage

class SongService:
    """
    Service class for handling song-related operations.
    """
    def __init__(
            self,
            table_service: TableService,
            genius_client: GeniusClient
    ):
        self.table_service = table_service
        self.genius_client = genius_client

        self.musixmatch_record = None
        self.genius_record = None

        self.artist = ''
        self.title = ''
        self.lyrics = []
        self.sections = []

        self.song_object = None

    def select_song(self):
        """
        Select a song from the Genius API.
        Check database for each song, take first new song found.
        """
        for track in self.genius_client.get_next_song():
            if track is None:
                logging.info('No more songs found.')
                break

            if self.table_service.get_table('external_source').song_exists(
                api=ExternalSource.SourceEnum.GENIUS,
                id=track['id'],
                url=track['api_path'],
            ):
                continue

            found_lyrics = self.fetch_genius_page(track)
            if not found_lyrics:
                logging.info('Skipping song "%s" by %s - no lyrics found', track['track_name'], track['artist_name'])
                continue

            break

        return self

    def fetch_genius_page(self, track_data: dict) -> bool:
        """
        Fetch the Genius page for the selected song.
        This method should be called after selecting a song.
        """

        genius_entry = self.genius_client.fetch_entry(path=track_data['api_path'])
        if genius_entry is None:
            return False

        self.genius_record = genius_entry
        genius_page = GeniusPage(track_data['url'])
        self.lyrics = genius_page.lyrics()

        self.title = track_data['title']
        self.artist = track_data['primary_artist_names']

        return True

    def save_song(self):
        """
        Save the song and its sections to the database.
        This method should be implemented to handle the actual saving logic.
        """
        if not self.lyrics \
            or not self.title \
            or not self.artist:
            raise ValueError("Incomplete song data. Cannot save song.")

        # Save the album
        album_entry = self.genius_client.fetch_entry(path=self.genius_record['album']['api_path'])
        release = self.table_service.get_table('release').save_if_not_exists(album_entry)

        # Save the songwriter(s)
        writer_objects = []
        for writer_data in self.genius_record['writer_artists']:
            writer_objects.append(self.table_service.get_table('writer').save_if_not_exists(writer_data))

        # Save the song
        self.song_object = self.table_service.get_table('song').save_if_not_exists(
            song_record=self.genius_record,
            album_object=release,
        )

    def parse_sections(self):
        """
        Parse the lyrics into sections.
        """
        self.sections = []

        if self.lyrics[0][0] != '[':
            # If the first line is not a section header, treat the entire lyrics as a single verse
            self.sections.append({
                'type': 'Verse',
                'song_order': 1,
                'lines': self.lyrics,
            })

            return

        section = {'lines': []}
        for line in self.lyrics:
            if line.startswith('['):
                if section and len(section['lines']) > 0:
                    # If we are already in a section and it has lines, save it
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
                if len(line) > 0 and section is not None: # Do not add empty lines
                    section['lines'].append(line)  # Add line to the current section

        if section and len(section['lines']) > 0:
            self.sections.append(section)

    def parse_words(self, line: str) -> list[str]:
        """
        Parse a line into individual words.
        This is a simple implementation and can be enhanced as needed.
        """
        split_pattern: Pattern[str] = re.compile(r'[ /&]')
        words = split_pattern.split(line)

        strip_pattern: Pattern[str] = re.compile(r'(^\W+|\W+$)')
        possessive_pattern: Pattern[str] = re.compile(r"('s)$")
        hyphen_pattern: Pattern[str] = re.compile(r'(^\w+-\w+$)')
        stripped_words = set()

        for word in words:
            # Strip punctuation from start and end of the word; save word
            word = strip_pattern.sub('', word)
            if word:
                stripped_words.add(word.lower())

            # Detect if the word is a possessive; save the base word in addition to the possessive form
            possessive = possessive_pattern.search(word)
            if possessive:
                base_word = possessive_pattern.sub('', word)
                if base_word:
                    stripped_words.add(base_word.lower())

            # Detect hyphenated words; save each part separately
            hyphenated = hyphen_pattern.match(word)
            if hyphenated:
                parts = word.split('-')
                for part in parts:
                    if part:
                        stripped_words.add(part.lower())

        return sorted(list(stripped_words))

    def save_lyrics(self):
        """
        Save the lyrics sections to the database.
        This method should be implemented to handle the actual saving logic.
        """
        self.parse_sections()

        if not self.sections:
            raise ValueError("No sections to save. Cannot save lyrics.")

        for section in self.sections:
            section_object = self.table_service.get_table('section').save(
                song=self.song_object,
                section_data=section,
            )

            for line_order, line in enumerate(section['lines'], start=1):
                line_object = self.table_service.get_table('line').save(
                    lyrics=line,
                    order=line_order,
                    section=section_object,
                )

                for word in self.parse_words(line):
                    self.table_service.get_table('word').save_if_not_exists(
                        text=word,
                        line=line_object,
                    )
