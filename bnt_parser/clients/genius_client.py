import logging
import os
import random
import urllib.parse
import requests

PATHS = {
    'search': 'search',
}
WRITERS = [
    'robert pollard',
    'taylor swift',
]
PAGE_SIZE = 48

class GeniusClient:
    """
    A client for interacting with the Genius API.
    """
    ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
    BASE_URL = 'https://api.genius.com'

    def __init__(self):
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.ACCESS_TOKEN}',
        }

    def get_next_song(self):
        """
        Retrieves songs by a songwriter, page by page, until a new song is found.

        :return: A generator yielding song data.
        """
        page = 1
        url = f"{self.BASE_URL}/{PATHS['search']}"
        writer = WRITERS[random.randrange(0, len(WRITERS) - 1)]
        query_params = {
            'q': writer,
            'per_page': PAGE_SIZE,
        }

        while True:
            query_params['page'] = page

            response = requests.get(
                url=url,
                params=urllib.parse.urlencode(query_params),
                headers=self.headers,
            )
            data = response.json()

            if data is None:
                logging.error(f'No response from Genius API for {writer}')
                yield None
                break

            if response.status_code != 200:
                logging.error(f'Genius API returned status {response.status_code}; response: {response.text}')
                yield None
                break

            hits = data['response']['hits']
            if not hits:
                yield None
                break

            for hit in hits:
                if hit['result']['type'] == 'song':
                    yield hit['result']

            page += 1
        yield None

    def search(self, artist: str, title: str) -> dict | None:
        url = f"{self.BASE_URL}/{PATHS['search']}"
        query = {
            'q': f"{artist} {title}"
        }

        response = requests.get(
            url=url,
            params=urllib.parse.urlencode(query),
            headers=self.headers,
        )
        results = response.json()

        for hit in results['response']['hits']:
            song = hit['result']
            if song['primary_artist']['name'].lower() == artist.lower() and song['title'].lower() == title.lower():
                return song

        return None