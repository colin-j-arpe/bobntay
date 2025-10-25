import json
from unittest.mock import patch, call

from django.test import TestCase
from django.db import connections

# Test API clients
from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.clients.musixmatch_client import MusixmatchClient
from bnt_parser.models import ExternalSource
from bnt_parser.services.song_service import SongService
from bnt_parser.services.table_service import TableService
from bnt_parser.tables.line_table import LineTable
from bnt_parser.tables.section_table import SectionTable
from bnt_parser.tables.external_source_table import ExternalSourceTable
from bnt_parser.tables.release_table import ReleaseTable
from bnt_parser.tables.song_table import SongTable
from bnt_parser.tables.word_table import WordTable
from bnt_parser.tables.writer_table import WriterTable
from bnt_parser.utils.genius_page import GeniusPage
import dj_database_url

class GeniusClientTestCase(TestCase):
    def setUp(self):
        self.client = GeniusClient()
        pass

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()
        pass

    def test_search_songs(self):
        artist = 'Guided by Voices'
        title = 'Buzzards and Dreadful Crows'
        result = self.client.search(artist=artist, title=title)

        assert result is not None, "Expected a result from Genius API"
        assert result['url'] == 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics', "Expected URL for the song"

class GeniusPageTestCase(TestCase):
    def setUp(self):
        url = 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics'
        self.page = GeniusPage(url=url)
        pass

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()
        pass

    def test_parse_page(self):
        results = self.page.lyrics()

        assert len(results) == 26, "Expected 26 lines of lyrics"
        assert results[0][0] == '[', "First line should be a section header"
        assert results[-1] == 'You were the only one', "Last line of the song"

class SongServiceTestCase(TestCase):
    def setUp(self):
        self.table_service = TableService()
        self.line_table = LineTable()
        self.release_table = ReleaseTable()
        self.section_table = SectionTable()
        self.song_table = SongTable()
        self.word_table = WordTable()
        self.external_source_table = ExternalSourceTable()
        self.writer_table = WriterTable()
        self.genius_client = GeniusClient()
        self.genius_url = 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics'
        self.genius_page = GeniusPage(url=self.genius_url)
        self.musixmatch_client = MusixmatchClient()
        self.service = SongService(
            table_service=self.table_service,
            musixmatch_client=self.musixmatch_client,
            genius_client=self.genius_client,
        )

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_select_song(self):
        existing_song = {
            'track_name': 'Existing Song Title',
            'artist_name': 'Existing Song Artist',
            'album_name': 'Existing Song Album',
        }
        new_song = {
            'track_name': 'New Song Title',
            'artist_name': 'New Song Artist',
            'album_name': 'New Song Album',
        }
        new_song_writers = [
            {'name': 'New Song Writer 2'},
            {'name': 'New Song Writer 1'},
        ]
        new_song_genius_entry = {'id': 123456,
            'url': self.genius_url,
            'writer_artists': new_song_writers,
        }
        new_song_lyrics = [
            '[Verse 1]',
            'First line of lyrics',
            'Second line of lyrics',
            '[Chorus]',
            'Chorus line 1',
            'Chorus line 2',
        ]

        with (
            patch.object(MusixmatchClient, 'get_next_song') as mock_get_next_song,
            patch.object(TableService, 'get_table') as mock_get_table,
            patch.object(SongTable, 'song_exists') as mock_song_exists,
            patch.object(GeniusClient, 'search') as mock_genius_search,
            patch.object(GeniusPage, 'lyrics') as mock_lyrics,
        ):
            # Configure the mock to return a generator of song data
            mock_get_next_song.return_value = iter([
                existing_song,
                new_song,
                None
            ])

            # Simulate that the table service returns the song table
            mock_get_table.return_value = self.song_table

            # Simulate that the first song exists in the database, the second does not
            mock_song_exists.side_effect = [True, False]

            # Simulate that the Genius search returns a new song entry
            mock_genius_search.return_value = new_song_genius_entry

            # Simulate that the GeniusPage.get_lyrics method returns the new song lyrics
            mock_lyrics.return_value = new_song_lyrics

            self.service.select_song()
            mock_get_next_song.assert_called_once()
            mock_get_table.assert_called_with(self.service.TABLES['song'])
            assert mock_get_table.call_count == 2, "Expected two calls to access the song table"

            expected_song_calls = [
                call(
                    title=existing_song['track_name'],
                    artist=existing_song['artist_name'],
                    release_title=existing_song['album_name'],
                ),
                call(
                    title=new_song['track_name'],
                    artist=new_song['artist_name'],
                    release_title=new_song['album_name'],
                ),
            ]
            mock_song_exists.assert_has_calls(expected_song_calls)
            assert mock_song_exists.call_count == 2, "Expected to check if two songs exist"

            mock_genius_search.assert_called_once_with(
                title=new_song['track_name'],
                artist=new_song['artist_name'],
            )
            mock_lyrics.assert_called_once()

            assert self.service.artist == new_song['artist_name'], "Expected artist name"
            assert self.service.title == new_song['track_name'], "Expected song title"
            assert self.service.musixmatch_record is not None, "Expected musixmatch record to be set"

    def test_save_song(self):
        test_title = 'Test Song'
        test_artist = 'Test Artist'
        test_lyrics = '[Verse 1]\nTest lyrics'
        test_mmx_album_id = 12345
        test_mmx_album = {
            'album_id': test_mmx_album_id,
            'album_name': 'Test Album',
            'artist_name': test_artist,
        }
        test_release_id = 1
        test_release_object = {
            'id': test_release_id,
        }
        test_external_source_id = 789
        test_genius_entry_id = 654
        test_genius_url = 'https://genius.com/Test-artist-test-song-lyrics'
        test_external_source = {
            'id': test_external_source_id,
            'external_id': test_genius_entry_id,
            'endpoint': test_genius_url,
        }
        test_writer = 'Test Writer'
        test_writers = [
            {'name': test_writer},
            {'name': test_artist},
        ]
        test_writer_objects = [
            {'id': 1, 'name': test_writer},
            {'id': 2, 'name': test_artist},
        ]
        test_song_id = 321

        self.service.title = test_title
        self.service.artist = test_artist

        with self.assertRaises(ValueError) as context:
            self.service.save_song()
        assert str(context.exception) == "Incomplete song data. Cannot save song.", "Cannot save without title, artist, and lyrics"

        self.service.lyrics = test_lyrics
        self.service.musixmatch_record = test_mmx_album
        self.service.genius_record = {
            'id': test_genius_entry_id,
            'url': test_genius_url,
            'writer_artists': test_writers,
        }

        with (
            patch.object(MusixmatchClient, 'get_release') as mock_get_release,
            patch.object(TableService, 'get_table') as mock_get_table,
            patch.object(ExternalSourceTable, 'save') as mock_external_source_save,
            patch.object(ReleaseTable, 'save_if_not_exists') as mock_release_table_save,
            patch.object(WriterTable, 'save_if_not_exists') as mock_writer_table_save,
            patch.object(SongTable, 'save_if_not_exists') as mock_song_table_save,
        ):
            # Configure the mocks
            mock_get_release.return_value = test_mmx_album
            mock_get_table.side_effect = [
                self.external_source_table,
                self.release_table,
                self.writer_table,
                self.writer_table,
                self.song_table,
            ]
            mock_external_source_save.return_value = test_external_source
            mock_release_table_save.return_value = test_release_object
            mock_writer_table_save.side_effect = test_writer_objects
            mock_song_table_save.return_value = test_song_id

            self.service.save_song()

            mock_external_source_save.assert_called_once_with(
                source=ExternalSource.SourceEnum.GENIUS,
                external_id=test_genius_entry_id,
                endpoint=test_genius_url,
            )

            mock_get_release.assert_called_once_with(test_mmx_album_id)

            expected_get_table_calls = [
                call('external_source'),
                call('release'),
                call('writer'),
                call('writer'),
                call('song'),
            ]
            mock_get_table.assert_has_calls(expected_get_table_calls)
            assert mock_get_table.call_count == 5, "Expected four calls to access different tables"

            mock_release_table_save.assert_called_once_with(test_mmx_album)

            expected_writer_calls = [
                call(test_writers[0]),
                call(test_writers[1]),
            ]
            mock_writer_table_save.assert_has_calls(expected_writer_calls)
            assert mock_writer_table_save.call_count == 2, "Expected two calls to save writers"

            mock_song_table_save.assert_called_once_with(
                title=test_title,
                artist=test_artist,
                release=test_release_object,
                external_source=test_external_source,
                writers=test_writer_objects,
            )

    def test_parse_sections(self):
        test_lyrics = [
            '[Verse 1]',
            'First line of verse',
            'Second line of verse',
            '',
            '[Chorus]',
            'First line of chorus',
            'Second line of chorus',
            '', # Empty line should be ignored
            'Third line of chorus',
            '',
            '[Solo]', # Ignore empty section
            ''
            '[Verse 2]',
            'Line in second verse',
            '',
            '[Outro]', # Ignore empty section
        ]
        expected_sections = [
            {
                'type': 'Verse',
                'song_order': 1,
                'lines': [
                    'First line of verse',
                    'Second line of verse',
                ],
            },
            {
                'type': 'Chorus',
                'song_order': 2,
                'lines': [
                    'First line of chorus',
                    'Second line of chorus',
                    'Third line of chorus',
                ],
            },
            {
                'type': 'Verse',
                'song_order': 3,
                'lines': [
                    'Line in second verse',
                ],
            },
        ]

        self.service.lyrics = test_lyrics
        self.service.parse_sections()

        assert self.service.sections == expected_sections, "Parsed sections do not match expected structure"

    def test_parse_words(self):
        test_line = "Hello, this world! This is either/or an app's test-line."
        expected_words = ["an", "app", "app's", "either", "hello", "is", "line", "or", "test", "test-line", "this", "world"]

        parsed_words = self.service.parse_words(test_line)

        assert parsed_words == expected_words, "Parsed words do not match expected list"

    def test_save_lyrics(self):
        test_song_object = {'id': 1}
        self.service.song_object = test_song_object

        self.service.lyrics = [
            '[Verse 1]',
            'First line of verse',
            'Second line of verse',
            '',
            '[Chorus]',
            'First line of chorus',
            'Second line of chorus',
        ]

        test_section_data = [
            {
                'type': 'Verse',
                'song_order': 1,
                'lines': [
                    'First line of verse',
                    'Second line of verse',
                ],
            },
            {
                'type': 'Chorus',
                'song_order': 2,
                'lines': [
                    'First line of chorus',
                    'Second line of chorus',
                ],
            },
        ]
        test_section_objects = [
            {'id': 1, 'type': 'Verse', 'order': 1},
            {'id': 2, 'type': 'Chorus', 'order': 2},
        ]

        test_line_data = [
            {
                'lyrics': 'First line of verse',
                'order': 1,
                'section': test_section_objects[0],
            },
            {
                'lyrics': 'Second line of verse',
                'order': 2,
                'section': test_section_objects[0],
            },
            {
                'lyrics': 'First line of chorus',
                'order': 1,
                'section': test_section_objects[1],
            },
            {
                'lyrics': 'Second line of chorus',
                'order': 2,
                'section': test_section_objects[1],
            },
        ]
        test_line_objects = [
            {'id': 1, 'order': 1, 'section_id': 1},
            {'id': 2, 'order': 2, 'section_id': 1},
            {'id': 3, 'order': 1, 'section_id': 2},
            {'id': 4, 'order': 2, 'section_id': 2},
        ]

        with (
            patch.object(TableService, 'get_table') as mock_get_table,
            patch.object(SectionTable, 'save') as mock_section_save,
            patch.object(LineTable, 'save') as mock_line_save,
            patch.object(WordTable, 'save_if_not_exists') as mock_word_save,
        ):
            mock_get_table.side_effect = [
                self.section_table,
                self.line_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.line_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.section_table,
                self.line_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.line_table,
                self.word_table,
                self.word_table,
                self.word_table,
                self.word_table,
            ]
            expected_get_table_calls = [
                call('section'),
                call('line'),
                call('word'),
                call('word'),
                call('word'),
                call('word'),
                call('line'),
                call('word'),
                call('word'),
                call('word'),
                call('word'),
                call('section'),
                call('line'),
                call('word'),
                call('word'),
                call('word'),
                call('word'),
                call('line'),
                call('word'),
                call('word'),
                call('word'),
                call('word'),
            ]

            mock_section_save.side_effect = test_section_objects
            expected_section_save_calls = [
                call(
                    song=test_song_object,
                    section_data=test_section_data[0],
                ),
                call(
                    song=test_song_object,
                    section_data=test_section_data[1],
                ),
            ]

            mock_line_save.side_effect = test_line_objects
            expected_line_save_calls = [
                call(
                    lyrics=test_line_data[0]['lyrics'],
                    order=test_line_data[0]['order'],
                    section=test_section_objects[0],
                ),
                call(
                    lyrics=test_line_data[1]['lyrics'],
                    order=test_line_data[1]['order'],
                    section=test_section_objects[0],
                ),
                call(
                    lyrics=test_line_data[2]['lyrics'],
                    order=test_line_data[2]['order'],
                    section=test_section_objects[1],
                ),
                call(
                    lyrics=test_line_data[3]['lyrics'],
                    order=test_line_data[3]['order'],
                    section=test_section_objects[1],
                ),
            ]

            expected_word_save_calls = [
                call(text='first', line=test_line_objects[0]),
                call(text='line', line=test_line_objects[0]),
                call(text='of', line=test_line_objects[0]),
                call(text='verse', line=test_line_objects[0]),
                call(text='line', line=test_line_objects[1]),
                call(text='of', line=test_line_objects[1]),
                call(text='second', line=test_line_objects[1]),
                call(text='verse', line=test_line_objects[1]),
                call(text='chorus', line=test_line_objects[2]),
                call(text='first', line=test_line_objects[2]),
                call(text='line', line=test_line_objects[2]),
                call(text='of', line=test_line_objects[2]),
                call(text='chorus', line=test_line_objects[3]),
                call(text='line', line=test_line_objects[3]),
                call(text='of', line=test_line_objects[3]),
                call(text='second', line=test_line_objects[3]),
            ]

            self.service.save_lyrics()

            mock_get_table.assert_has_calls(expected_get_table_calls)
            assert mock_get_table.call_count == 22, "Expected calls to access section, line, and word tables"

            mock_section_save.assert_has_calls(expected_section_save_calls)
            assert mock_section_save.call_count == 2, "Expected two calls to save sections"

            mock_line_save.assert_has_calls(expected_line_save_calls)
            assert mock_line_save.call_count == 4, "Expected four calls to save lines"

            mock_word_save.assert_has_calls(expected_word_save_calls)
            assert mock_word_save.call_count == 16, "Expected sixteen calls to save words"

            pass

class TableServiceTestCase(TestCase):
    def setUp(self):
        self.table_service = TableService()
        pass

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()
        pass

    def test_get_table(self):
        song_table = self.table_service.get_table('song')
        assert isinstance(song_table, SongTable), "Expected instance of SongTable"

        with self.assertRaises(ValueError) as context:
            self.table_service.get_table('invalid_table')
        assert str(context.exception) == "Table 'invalid_table' is not recognised.", "Expected ValueError for invalid table"