import logging

from bnt_parser.api_clients.genius_client import GeniusClient
from bnt_parser.api_clients.musixmatch_client import MusixmatchClient
from bnt_parser.tables.song_table import SongTable
from bnt_parser.utils.genius_page import GeniusPage

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
        self.song_table = song_table
        self.musixmatch_client = musixmatch_client
        self.genius_client = genius_client

        self.lyrics = []
        self.sections = []
        self.title = None
        self.artist = None
        self.release_title = None
        self.writers = []

    def select_song(self):
        """
        Select a song from the Musixmatch API.
        Check database for each song, take first new song found.
        """
        for track in self.musixmatch_client.get_next_song():
            if track is None:
                break

            if self.song_table.song_exists(
                title=track.track_name,
                artist=track.artist_name,
                release_title=track.album_name,
            ):
                continue

            found_lyrics = self.fetch_genius_page(
                artist=track['artist_name'],
                title=track['track_name'],
            )
            if found_lyrics is False:
                logging.info('Skipping song "%s" by %s - no lyrics found', track['track_name'], track['artist_name'])
                continue

            self.title = track['track_name']
            self.artist = track['artist_name']
            self.release_title = track['album_name']

            break

        return self

    def fetch_genius_page(self, artist: str, title: str) -> bool:
        """
        Fetch the Genius page for the selected song.
        This method should be called after selecting a song.
        """

        genius_entry = self.genius_client.search(
            artist=self.artist,
            title=self.title,
        )
        if genius_entry is None:
            return False

        for writer in genius_entry['writer_artists']:
            self.writers.append(writer['name'])

        genius_page = GeniusPage(genius_entry['url'])
        self.lyrics = genius_page.lyrics()

        return True

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