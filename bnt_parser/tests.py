import json
import os
from unittest.mock import patch, call, MagicMock

from django.test import TestCase
from django.db import connections

# Test API clients
from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.models import ExternalSource, Release, Song, Section, Line, Word, Writer
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
    FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'buzzards_and_dreadful_crows.html')

    def setUp(self):
        with open(self.FIXTURE_PATH, 'rb') as f:
            fixture_content = f.read()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fixture_content
        with patch('bnt_parser.utils.genius_page.requests.get', return_value=mock_response):
            self.page = GeniusPage(url='https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics')

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_parse_page(self):
        results = self.page.lyrics()

        assert len(results) == 29, "Expected 29 lines of lyrics"
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
        self.service = SongService(
            table_service=self.table_service,
            genius_client=self.genius_client,
        )

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_select_song(self):
        existing_song_external_id = 1234
        existing_song = {
            'title': 'Existing Song Title',
            'primary_artist_names': 'Existing Song Artist',
            'album': {'full_title': 'Existing Song Album'},
            'id': existing_song_external_id,
            'api_path': f'/songs/{existing_song_external_id}',
        }
        new_song_external_id = 4321
        new_song = {
            'title': 'New Song Title',
            'primary_artist_names': 'New Song Artist',
            'album': {'full_title': 'New Song Album'},
            'id': new_song_external_id,
            'api_path': f'/songs/{new_song_external_id}',
            'url': 'https://genius.com/Artist-name-song-title-lyrics',
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
            patch.object(GeniusClient, 'get_next_song') as mock_get_next_song,
            patch.object(GeniusClient, 'fetch_entry', return_value=new_song_genius_entry),
            patch.object(TableService, 'get_table') as mock_get_table,
            patch.object(ExternalSourceTable, 'song_exists') as mock_song_exists,
            patch.object(GeniusPage, 'fetchContent'),
            patch.object(GeniusPage, 'lyrics') as mock_lyrics,
        ):
            # Configure the mock to return a generator of song data
            mock_get_next_song.return_value = iter([
                existing_song,
                new_song,
                None
            ])

            # Simulate that the table service returns the song table
            mock_get_table.return_value = self.external_source_table

            # Simulate that the first song exists in the database, the second does not
            mock_song_exists.side_effect = [True, False]

            # Simulate that the GeniusPage.get_lyrics method returns the new song lyrics
            mock_lyrics.return_value = new_song_lyrics

            self.service.select_song()
            mock_get_next_song.assert_called_once()
            mock_get_table.assert_called_with('external_source')
            assert mock_get_table.call_count == 2, "Expected two calls to access the external source table"

            expected_song_calls = [
                call(
                    api=ExternalSource.SourceEnum.GENIUS,
                    id=existing_song_external_id,
                    url=existing_song['api_path'],
                ),
                call(
                    api=ExternalSource.SourceEnum.GENIUS,
                    id=new_song_external_id,
                    url=new_song['api_path'],
                ),
            ]
            mock_song_exists.assert_has_calls(expected_song_calls)
            assert mock_song_exists.call_count == 2, "Expected to check if two songs exist"

            mock_lyrics.assert_called_once()

            assert self.service.artist == new_song['primary_artist_names'], "Expected artist name"
            assert self.service.title == new_song['title'], "Expected song title"
            assert self.service.genius_record is not None, "Expected Genius record to be set"

    def test_save_song(self):
        test_title = 'Test Song'
        test_artist = 'Test Artist'
        test_lyrics = '[Verse 1]\nTest lyrics'
        test_album_id = 12345
        test_album = {
            'album_id': test_album_id,
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
        test_genius_entry = {
            'id': test_genius_entry_id,
            'api_path': f'/songs/{test_genius_entry_id}',
            'album': {'api_path': f'/albums/{test_album_id}'},
            'writer_artists': test_writers,
        }
        self.service.genius_record = test_genius_entry

        with (
            patch.object(GeniusClient, 'fetch_entry') as mock_fetch_entry,
            patch.object(TableService, 'get_table') as mock_get_table,
            patch.object(ReleaseTable, 'save_if_not_exists') as mock_release_table_save,
            patch.object(WriterTable, 'save_if_not_exists') as mock_writer_table_save,
            patch.object(SongTable, 'save_if_not_exists') as mock_song_table_save,
        ):
            # Configure the mocks
            mock_fetch_entry.return_value = test_album
            mock_get_table.side_effect = [
                self.release_table,
                self.song_table,
                self.writer_table,
                self.writer_table,
            ]
            mock_release_table_save.return_value = test_release_object
            mock_writer_table_save.side_effect = test_writer_objects
            mock_song_table_save.return_value = test_song_id

            self.service.save_song()

            mock_fetch_entry.assert_called_once_with(path=test_genius_entry['album']['api_path'])

            expected_get_table_calls = [
                call('release'),
                call('song'),
                call('writer'),
                call('writer'),
            ]
            mock_get_table.assert_has_calls(expected_get_table_calls)
            assert mock_get_table.call_count == 4, "Expected four calls to access different tables"

            mock_release_table_save.assert_called_once_with(test_album)

            expected_writer_calls = [
                call(writer_data=test_writers[0], song=test_song_id),
                call(writer_data=test_writers[1], song=test_song_id),
            ]
            mock_writer_table_save.assert_has_calls(expected_writer_calls)
            assert mock_writer_table_save.call_count == 2, "Expected two calls to save writers"

            mock_song_table_save.assert_called_once_with(
                song_record=test_genius_entry,
                album_object=test_release_object,
            )

    def test_parse_sections(self):
        test_lyrics = [
            '[Verse 1]',
            'First line of verse',
            'Second line of verse',
            '',
            '[Chorus: Featured Artist]',
            'First line of chorus',
            'Second line of chorus',
            '|', # Empty line should start a new section labelled verse
            'First standalone line',
            'Second standalone line',
            '',
            '[Solo]', # Ignore empty section
            ''
            '[Verse 2: Featured Artist]',
            'Line in second verse',
            '[Pre-Chorus]', # Section type should start a new section even without empty line
            'Line in third verse',
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
                ],
            },
            {
                'type': '',
                'song_order': 3,
                'lines': [
                    'First standalone line',
                    'Second standalone line',
                ],
            },
            {
                'type': 'Verse',
                'song_order': 4,
                'lines': [
                    'Line in second verse',
                ],
            },
            {
                'type': 'Pre-Chorus',
                'song_order': 5,
                'lines': [
                    'Line in third verse',
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
                    multiple_sections=False,
                ),
                call(
                    song=test_song_object,
                    section_data=test_section_data[1],
                    multiple_sections=False,
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

class GeniusPagePrefetchedTestCase(TestCase):
    """Tests for GeniusPage when pre-fetched HTML is provided via the html parameter."""
    FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'buzzards_and_dreadful_crows.html')

    def setUp(self):
        with open(self.FIXTURE_PATH, 'rb') as f:
            self.fixture_content = f.read()

    def tearDown(self):
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_prefetched_html_bypasses_fetch(self):
        with patch('bnt_parser.utils.genius_page.requests.get') as mock_get:
            page = GeniusPage(url='https://genius.com/test', html=self.fixture_content)
            mock_get.assert_not_called()
            assert page.page_content == self.fixture_content

    def test_prefetched_html_lyrics_parsed(self):
        page = GeniusPage(url='https://genius.com/test', html=self.fixture_content)
        results = page.lyrics()
        assert len(results) == 29, "Expected 29 lines of lyrics"
        assert results[0][0] == '[', "First line should be a section header"
        assert results[-1] == 'You were the only one', "Last line of the song"


class FindNextTrackTestCase(TestCase):
    def setUp(self):
        self.external_source_table = ExternalSourceTable()
        self.service = SongService(
            table_service=TableService(),
            genius_client=GeniusClient(),
        )
        self.existing_song = {
            'title': 'Existing Song',
            'primary_artist_names': 'Artist',
            'id': 1111,
            'api_path': '/songs/1111',
            'url': 'https://genius.com/artist-existing-song-lyrics',
        }
        self.new_song = {
            'title': 'New Song',
            'primary_artist_names': 'Artist',
            'id': 2222,
            'api_path': '/songs/2222',
            'url': 'https://genius.com/artist-new-song-lyrics',
        }
        self.genius_record = {
            'id': 2222,
            'writer_artists': [],
        }

    def tearDown(self):
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_skips_existing_returns_new(self):
        with (
            patch.object(GeniusClient, 'get_next_song', return_value=iter([self.existing_song, self.new_song, None])),
            patch.object(TableService, 'get_table', return_value=self.external_source_table),
            patch.object(ExternalSourceTable, 'song_exists', side_effect=[True, False]),
            patch.object(GeniusClient, 'fetch_entry', return_value=self.genius_record),
        ):
            result = self.service.find_next_track()
            assert result is not None
            assert result['track'] == self.new_song
            assert result['genius_record'] == self.genius_record

    def test_returns_none_when_all_songs_exist(self):
        with (
            patch.object(GeniusClient, 'get_next_song', return_value=iter([self.existing_song, None])),
            patch.object(TableService, 'get_table', return_value=self.external_source_table),
            patch.object(ExternalSourceTable, 'song_exists', return_value=True),
        ):
            result = self.service.find_next_track()
            assert result is None

    def test_skips_track_when_fetch_entry_fails(self):
        with (
            patch.object(GeniusClient, 'get_next_song', return_value=iter([self.new_song, None])),
            patch.object(TableService, 'get_table', return_value=self.external_source_table),
            patch.object(ExternalSourceTable, 'song_exists', return_value=False),
            patch.object(GeniusClient, 'fetch_entry', return_value=None),
        ):
            result = self.service.find_next_track()
            assert result is None


class LoadPrefetchedTestCase(TestCase):
    FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'buzzards_and_dreadful_crows.html')

    def setUp(self):
        with open(self.FIXTURE_PATH, 'rb') as f:
            self.html = f.read()
        self.service = SongService(
            table_service=TableService(),
            genius_client=GeniusClient(),
        )
        self.track_data = {
            'title': 'Buzzards and Dreadful Crows',
            'primary_artist_names': 'Guided by Voices',
            'url': 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics',
            'api_path': '/songs/12345',
        }
        self.genius_record = {
            'id': 12345,
            'writer_artists': [{'name': 'Robert Pollard'}],
        }

    def tearDown(self):
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_sets_service_state(self):
        self.service.load_prefetched(
            track_data=self.track_data,
            genius_record=self.genius_record,
            html=self.html,
        )
        assert self.service.title == self.track_data['title']
        assert self.service.artist == self.track_data['primary_artist_names']
        assert self.service.genius_record == self.genius_record
        assert len(self.service.lyrics) == 29

    def test_no_http_calls(self):
        with patch('bnt_parser.utils.genius_page.requests.get') as mock_get:
            self.service.load_prefetched(
                track_data=self.track_data,
                genius_record=self.genius_record,
                html=self.html,
            )
            mock_get.assert_not_called()


class NextSongViewTestCase(TestCase):
    API_KEY = 'test-api-key-123'

    def setUp(self):
        self.track_data = {
            'title': 'New Song',
            'primary_artist_names': 'Artist',
            'id': 2222,
            'api_path': '/songs/2222',
            'url': 'https://genius.com/artist-new-song-lyrics',
        }
        self.genius_record = {'id': 2222, 'writer_artists': []}

    def tearDown(self):
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def test_returns_track_with_valid_key(self):
        find_result = {'track': self.track_data, 'genius_record': self.genius_record}
        with (
            patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}),
            patch.object(SongService, 'find_next_track', return_value=find_result),
        ):
            response = self.client.get('/parse/next-song/', HTTP_X_API_KEY=self.API_KEY)
            assert response.status_code == 200
            data = response.json()
            assert data['track'] == self.track_data
            assert data['genius_record'] == self.genius_record

    def test_returns_403_without_key(self):
        with patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}):
            response = self.client.get('/parse/next-song/')
            assert response.status_code == 403

    def test_returns_403_with_wrong_key(self):
        with patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}):
            response = self.client.get('/parse/next-song/', HTTP_X_API_KEY='wrong-key')
            assert response.status_code == 403

    def test_returns_404_when_no_new_songs(self):
        with (
            patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}),
            patch.object(SongService, 'find_next_track', return_value=None),
        ):
            response = self.client.get('/parse/next-song/', HTTP_X_API_KEY=self.API_KEY)
            assert response.status_code == 404


class SubmitPageViewTestCase(TestCase):
    API_KEY = 'test-api-key-123'
    FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'buzzards_and_dreadful_crows.html')

    def setUp(self):
        with open(self.FIXTURE_PATH, 'r', encoding='utf-8') as f:
            self.html_content = f.read()
        self.track_data = {
            'title': 'Buzzards and Dreadful Crows',
            'primary_artist_names': 'Guided by Voices',
            'url': 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics',
            'api_path': '/songs/12345',
        }
        self.genius_record = {'id': 12345, 'writer_artists': [{'name': 'Robert Pollard'}]}

    def tearDown(self):
        for connection in connections.all():
            if connection.connection:
                connection.close()

    def _post(self, data=None, key=None):
        headers = {'HTTP_X_API_KEY': key} if key else {}
        return self.client.post(
            '/parse/submit-page/',
            data=json.dumps(data or {}),
            content_type='application/json',
            **headers,
        )

    def test_saves_song_with_valid_data(self):
        with (
            patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}),
            patch('bnt_parser.views.SongService') as MockSongService,
        ):
            mock_service = MagicMock()
            mock_service.title = self.track_data['title']
            mock_service.artist = self.track_data['primary_artist_names']
            MockSongService.return_value = mock_service

            response = self._post(
                data={
                    'track_data': self.track_data,
                    'genius_record': self.genius_record,
                    'html': self.html_content,
                },
                key=self.API_KEY,
            )

            assert response.status_code == 200
            mock_service.load_prefetched.assert_called_once_with(
                track_data=self.track_data,
                genius_record=self.genius_record,
                html=self.html_content.encode('utf-8'),
            )
            mock_service.save_song.assert_called_once()
            mock_service.save_lyrics.assert_called_once()
            assert 'Buzzards and Dreadful Crows' in response.json()['detail']

    def test_returns_400_when_fields_missing(self):
        with patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}):
            response = self._post(
                data={'track_data': self.track_data},
                key=self.API_KEY,
            )
            assert response.status_code == 400

    def test_returns_403_without_key(self):
        with patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}):
            response = self._post(
                data={
                    'track_data': self.track_data,
                    'genius_record': self.genius_record,
                    'html': self.html_content,
                },
            )
            assert response.status_code == 403

    def test_returns_403_with_wrong_key(self):
        with patch.dict('os.environ', {'PARSE_API_KEY': self.API_KEY}):
            response = self._post(
                data={
                    'track_data': self.track_data,
                    'genius_record': self.genius_record,
                    'html': self.html_content,
                },
                key='wrong-key',
            )
            assert response.status_code == 403


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


# ============================================================
# Table Tests
# ============================================================

class ExternalSourceTableTestCase(TestCase):
    def setUp(self):
        self.table = ExternalSourceTable()

    def test_save(self):
        source = self.table.save(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=123,
            endpoint='/songs/123',
        )
        assert source.pk is not None, "ExternalSource should have a DB ID after save"
        assert source.source == ExternalSource.SourceEnum.GENIUS
        assert source.external_id == 123
        assert source.endpoint == '/songs/123'

    def test_song_exists_true(self):
        ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=456,
            endpoint='/songs/456',
        )
        assert self.table.song_exists(
            api=ExternalSource.SourceEnum.GENIUS,
            id=456,
            url='/songs/456',
        ) is True

    def test_song_exists_false_wrong_id(self):
        ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=789,
            endpoint='/songs/789',
        )
        assert self.table.song_exists(
            api=ExternalSource.SourceEnum.GENIUS,
            id=999,
            url='/songs/789',
        ) is False

    def test_song_exists_false_wrong_endpoint(self):
        ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=101,
            endpoint='/songs/101',
        )
        assert self.table.song_exists(
            api=ExternalSource.SourceEnum.GENIUS,
            id=101,
            url='/songs/different',
        ) is False


class ReleaseTableTestCase(TestCase):
    def setUp(self):
        self.table = ReleaseTable()

    def _make_release(self, external_id=1, title='Test Album', artist='Test Artist'):
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=external_id,
            endpoint=f'/albums/{external_id}',
        )
        return Release.objects.create(
            title=title,
            artist=artist,
            release_date='2020-01-01',
            label='Test Label',
            external_source=ext,
        )

    # NOTE: test_get_release_by_title_* will fail because get_release_by_title
    # uses 'inexact' (an invalid Django lookup) instead of 'iexact'.
    def test_get_release_by_title_exists(self):
        self._make_release(title='Alien Lanes', artist='Guided by Voices')
        result = self.table.get_release_by_title(title='alien lanes', artist='guided by voices')
        assert result is not None, "Should find release with case-insensitive match"
        assert result.title == 'Alien Lanes'

    def test_get_release_by_title_not_found(self):
        result = self.table.get_release_by_title(title='Does Not Exist', artist='Nobody')
        assert result is None, "Should return None when no release matches"

    def test_get_release_by_source_exists(self):
        self._make_release(external_id=42)
        result = self.table.get_release_by_source(external_id=42)
        assert result is not None, "Should find release by external_id"

    def test_get_release_by_source_not_found(self):
        result = self.table.get_release_by_source(external_id=9999)
        assert result is None, "Should return None when no release has that external_id"

    def test_save_if_not_exists_new_release(self):
        release_data = {
            'id': 201,
            'api_path': '/albums/201',
            'primary_artist_names': 'Guided by Voices',
            'name': 'Bee Thousand',
            'release_date': '1994-06-21',
            'label': 'Scat Records',
        }
        release = self.table.save_if_not_exists(release_data)
        assert release.pk is not None
        assert release.title == 'Bee Thousand'
        assert release.artist == 'Guided by Voices'
        assert Release.objects.filter(pk=release.pk).exists()

    def test_save_if_not_exists_existing_release(self):
        self._make_release(external_id=202, title='Bee Thousand')
        release_data = {
            'id': 202,
            'api_path': '/albums/202',
            'primary_artist_names': 'Guided by Voices',
            'name': 'Bee Thousand',
            'release_date': '1994-06-21',
        }
        self.table.save_if_not_exists(release_data)
        assert Release.objects.filter(external_source__external_id=202).count() == 1, \
            "Should not create a duplicate release"


class SongTableTestCase(TestCase):
    def setUp(self):
        self.table = SongTable()

    def _make_external_source(self, external_id=1, endpoint=None):
        return ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=external_id,
            endpoint=endpoint or f'/songs/{external_id}',
        )

    def _make_release(self, external_id=100, title='Test Album', artist='Test Artist'):
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=external_id,
            endpoint=f'/albums/{external_id}',
        )
        return Release.objects.create(
            title=title,
            artist=artist,
            release_date='2020-01-01',
            label='',
            external_source=ext,
        )

    def _make_song(self, external_id=1, title='Test Song', artist='Test Artist', release=None):
        ext = self._make_external_source(external_id=external_id)
        return Song.objects.create(
            title=title,
            artist=artist,
            release=release,
            external_source=ext,
        )

    def test_find_song_exists(self):
        self._make_song(title='Buzzards and Dreadful Crows', artist='Guided by Voices')
        result = self.table.find_song(
            title='buzzards and dreadful crows',
            artist='guided by voices',
            release_title=None,
        )
        assert result is not None, "Should find song with case-insensitive match"

    def test_find_song_with_release(self):
        release = self._make_release(title='Bee Thousand')
        self._make_song(external_id=2, title='Echos Myron', artist='Guided by Voices', release=release)
        result = self.table.find_song(
            title='Echos Myron',
            artist='Guided by Voices',
            release_title='Bee Thousand',
        )
        assert result is not None, "Should find song when release title matches"

    def test_find_song_not_found(self):
        result = self.table.find_song(title='Unknown Song', artist='Nobody', release_title=None)
        assert result is None, "Should return None when no song matches"

    def test_song_exists_true(self):
        self._make_song(title='Motor Away', artist='Guided by Voices')
        assert self.table.song_exists(
            title='Motor Away', artist='Guided by Voices', release_title=None
        ) is True

    def test_song_exists_false(self):
        assert self.table.song_exists(
            title='Nonexistent', artist='Nobody', release_title=None
        ) is False

    def test_save_if_not_exists_new_song(self):
        song_record = {
            'id': 501,
            'api_path': '/songs/501',
            'title': 'Glad Girls',
            'primary_artist': {'name': 'Guided by Voices'},
        }
        song = self.table.save_if_not_exists(song_record=song_record, album_object=None)
        assert song.pk is not None
        assert song.title == 'Glad Girls'
        assert song.artist == 'Guided by Voices'
        assert song.release is None
        assert Song.objects.filter(pk=song.pk).exists()

    def test_save_if_not_exists_existing_song(self):
        self._make_song(external_id=502, title='Glad Girls', artist='Guided by Voices')
        song_record = {
            'id': 999,
            'api_path': '/songs/999',
            'title': 'Glad Girls',
            'primary_artist': {'name': 'Guided by Voices'},
        }
        self.table.save_if_not_exists(song_record=song_record, album_object=None)
        assert Song.objects.filter(
            title__iexact='Glad Girls', artist__iexact='Guided by Voices'
        ).count() == 1, "Should not create a duplicate song"


class SectionTableTestCase(TestCase):
    def setUp(self):
        self.table = SectionTable()
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=1,
            endpoint='/songs/1',
        )
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            external_source=ext,
        )

    def test_save_known_type(self):
        section = self.table.save(
            song=self.song,
            section_data={'type': 'Chorus', 'song_order': 1},
        )
        assert section.pk is not None
        assert section.type == Section.SectionTypeEnum.CHORUS
        assert section.order == 1

    def test_save_type_case_insensitive(self):
        section = self.table.save(
            song=self.song,
            section_data={'type': 'verse', 'song_order': 2},
        )
        assert section.type == Section.SectionTypeEnum.VERSE

    def test_save_type_strips_special_chars(self):
        # "Pre-Chorus" → strip non-word chars → "PRECHORUS" → matches PRECHORUS enum
        section = self.table.save(
            song=self.song,
            section_data={'type': 'Pre-Chorus', 'song_order': 3},
        )
        assert section.type == Section.SectionTypeEnum.PRECHORUS

    def test_save_unknown_type_single_section(self):
        section = self.table.save(
            song=self.song,
            section_data={'type': 'Funk', 'song_order': 4},
            multiple_sections=False,
        )
        assert section.type == Section.SectionTypeEnum.VERSE, \
            "Unknown type with multiple_sections=False should default to VERSE"

    def test_save_unknown_type_multiple_sections(self):
        section = self.table.save(
            song=self.song,
            section_data={'type': 'Funk', 'song_order': 5},
            multiple_sections=True,
        )
        assert section.type == Section.SectionTypeEnum.OTHER, \
            "Unknown type with multiple_sections=True should default to OTHER"

    def test_save_order(self):
        section = self.table.save(
            song=self.song,
            section_data={'type': 'Verse', 'song_order': 7},
        )
        assert section.order == 7


class LineTableTestCase(TestCase):
    def setUp(self):
        self.table = LineTable()
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=1,
            endpoint='/songs/1',
        )
        song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            external_source=ext,
        )
        self.section = Section.objects.create(
            song=song,
            order=1,
            type=Section.SectionTypeEnum.VERSE,
        )

    def test_save(self):
        line = self.table.save(
            lyrics='The lifeblood, the lighthouse flashing',
            order=1,
            section=self.section,
        )
        assert line.pk is not None
        assert line.lyrics == 'The lifeblood, the lighthouse flashing'
        assert line.order == 1
        assert line.section == self.section


class WordTableTestCase(TestCase):
    def setUp(self):
        self.table = WordTable()
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=1,
            endpoint='/songs/1',
        )
        song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            external_source=ext,
        )
        section = Section.objects.create(
            song=song,
            order=1,
            type=Section.SectionTypeEnum.VERSE,
        )
        self.line = Line.objects.create(
            lyrics='Test line of lyrics',
            order=1,
            section=section,
        )

    def test_find_word_exists(self):
        Word.objects.create(text='buzzards')
        result = self.table.find_word('buzzards')
        assert result is not None
        assert result.text == 'buzzards'

    def test_find_word_not_found(self):
        result = self.table.find_word('nonexistent')
        assert result is None

    def test_find_word_case_sensitive(self):
        Word.objects.create(text='Buzzards')
        result = self.table.find_word('buzzards')
        assert result is None, "find_word should be case-sensitive"

    def test_save_if_not_exists_new_word(self):
        word = self.table.save_if_not_exists(text='dreadful', line=self.line)
        assert word.pk is not None
        assert word.text == 'dreadful'
        assert self.line in word.line.all(), "Line should be associated with the word"

    def test_save_if_not_exists_existing_word(self):
        existing_word = Word.objects.create(text='crows')
        word = self.table.save_if_not_exists(text='crows', line=self.line)
        assert word.pk == existing_word.pk, "Should reuse existing word"
        assert self.line in word.line.all(), "Line should be added to existing word"
        assert Word.objects.filter(text='crows').count() == 1, "Should not create a duplicate word"


class WriterTableTestCase(TestCase):
    def setUp(self):
        self.table = WriterTable()
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=1,
            endpoint='/songs/1',
        )
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            external_source=ext,
        )

    def test_get_writer_by_name_exists(self):
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=10,
            endpoint='/artists/10',
        )
        Writer.objects.create(name='Robert Pollard', external_source=ext)
        result = self.table.get_writer_by_name('robert pollard')
        assert result is not None, "Should find writer with case-insensitive match"
        assert result.name == 'Robert Pollard'

    def test_get_writer_by_name_not_found(self):
        result = self.table.get_writer_by_name('Nobody')
        assert result is None

    def test_save_if_not_exists_new_writer(self):
        writer_data = {
            'name': 'Robert Pollard',
            'id': 11,
            'api_path': '/artists/11',
        }
        writer = self.table.save_if_not_exists(writer_data=writer_data, song=self.song)
        assert writer.pk is not None
        assert writer.name == 'Robert Pollard'
        assert self.song in writer.songs.all(), "Song should be associated with the writer"
        assert writer.external_source.external_id == 11

    def test_save_if_not_exists_existing_writer(self):
        ext = ExternalSource.objects.create(
            source=ExternalSource.SourceEnum.GENIUS,
            external_id=12,
            endpoint='/artists/12',
        )
        existing_writer = Writer.objects.create(name='Tobin Sprout', external_source=ext)
        writer_data = {
            'name': 'Tobin Sprout',
            'id': 12,
            'api_path': '/artists/12',
        }
        writer = self.table.save_if_not_exists(writer_data=writer_data, song=self.song)
        assert writer.pk == existing_writer.pk, "Should return existing writer"
        assert self.song in writer.songs.all(), "Song should be added to existing writer"
        assert Writer.objects.filter(name='Tobin Sprout').count() == 1, \
            "Should not create a duplicate writer"