import logging
import re
from re import Pattern

from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.clients.musixmatch_client import MusixmatchClient
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
            musixmatch_client: MusixmatchClient,
            genius_client: GeniusClient
    ):
        self.table_service = table_service
        self.musixmatch_client = musixmatch_client
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
        Select a song from the Musixmatch API.
        Check database for each song, take first new song found.
        """
        for track in self.musixmatch_client.get_next_song():
            if track is None:
                break

            if self.table_service.get_table('song').song_exists(
                title=track['track_name'],
                artist=track['artist_name'],
                release_title=track['album_name'],
            ):
                continue

            found_lyrics = self.fetch_genius_page(
                artist=track['artist_name'],
                title=track['track_name'],
            )
            if found_lyrics is False:
                logging.info('Skipping song "%s" by %s - no lyrics found', track['track_name'], track['artist_name'])
                continue

            self.musixmatch_record = track

            break

        return self

    def fetch_genius_page(self, artist: str, title: str) -> bool:
        """
        Fetch the Genius page for the selected song.
        This method should be called after selecting a song.
        """

        genius_entry = self.genius_client.search(
            artist=artist,
            title=title,
        )
        if genius_entry is None:
            return False

        self.genius_record = genius_entry
        genius_page = GeniusPage(genius_entry['url'])
        self.lyrics = genius_page.lyrics()

        self.title = title
        self.artist = artist

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

        # Save the external source for Genius
        external_source = self.table_service.get_table('external_source').save(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=self.genius_record['id'],
            endpoint=self.genius_record['url'],
        )

        # Save the album
        album_entry = self.musixmatch_client.get_release(self.musixmatch_record['album_id'])
        release = self.table_service.get_table('release').save_if_not_exists(album_entry)

        # Save the songwriter(s)
        writer_objects = []
        for writer_data in self.genius_record['writer_artists']:
            writer_objects.append(self.table_service.get_table('writer').save_if_not_exists(writer_data))

        # Save the song
        self.song_object = self.table_service.get_table('song').save_if_not_exists(
            title=self.title,
            artist=self.artist,
            release=release,
            external_source=external_source,
            writers=writer_objects,
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

        section = None
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

        strip_pattern: Pattern[str] = re.compile(r'(?:^\W+|\W+$)')
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

        print(sorted(list(stripped_words)))
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
