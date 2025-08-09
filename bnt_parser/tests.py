import json

from django.test import TestCase
from django.db import connections

# Test API clients
from bnt_parser.clients import genius_client
from bnt_parser.services import song_service
from bnt_parser.utils import genius_page

class GeniusClientTestCase(TestCase):
    def setUp(self):
        self.client = genius_client.GeniusClient()
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

        assert result == 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics', "Expected URL for the song"

class GeniusPageTestCase(TestCase):
    def setUp(self):
        url = 'https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics'
        self.page = genius_page.GeniusPage(url=url)
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
        # mock instance of GeniusPage
        self.page = genius_page.GeniusPage(url='https://genius.com/Guided-by-voices-buzzards-and-dreadful-crows-lyrics')
        self.service = song_service.SongService(self.page) # Placeholder for the song service instance
        pass

    def tearDown(self):
        # Close any connections to the test database
        for connection in connections.all():
            if connection.connection:
                connection.close()
        pass

    def test_song_service(self):
        self.service.parse_sections()
        print(json.dumps(self.service.sections))
        # Placeholder for future tests related to song service
        pass