import os
from random import random
import requests

class MusixmatchClient:
    """
    A client for interacting with the Musixmatch API.
    """
    BASE_URL = 'https://api.musixmatch.com/ws/1.1'
    API_KEY = os.getenv('MUSIMMATCH_API_KEY')
    WRITERS = [
        'robert pollard',
        'taylor swift',
    ]

    # def __init__(self):

    def get_next_song(self):
        """
        Retrieves songs by a songwriter, page by page, until a new song is found.

        :return: A generator yielding song data.
        """
        page = 1
        url = self.BASE_URL + '/track.search'
        writer = self.WRITERS[random.randint(0, len(self.WRITERS) - 1)]

        while True:
            headers = {
                'Accept': 'application/json',
            }
            query = {
                'apikey': self.API_KEY,
                'q_writer': writer,
                'page': page,
                'page_size': 100,
            }

            response = requests.get(
                url,
                headers=headers,
                params=query,
            )
            data = response.json()

            if data['message']['header']['status_code'] != 200 or not data['message']['body']['track_list']:
                yield None
                break

            for track in data['message']['body']['track_list']:
                yield track['track']

            page += 1
        yield None