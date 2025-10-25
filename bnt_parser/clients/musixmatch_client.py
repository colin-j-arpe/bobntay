import logging
import os
import random
import requests

PATHS = {
    'search': 'track.search',
    'song': 'track.get',
    'album': 'album.get',
}

WRITERS = [
    'robert pollard',
    'taylor swift',
]

class MusixmatchClient:
    """
    A client for interacting with the Musixmatch API.
    """
    BASE_URL = 'https://api.musixmatch.com/ws/1.1'
    API_KEY = os.getenv('MUSIXMATCH_API_KEY')

    # def __init__(self):

    def get_next_song(self):
        """
        Retrieves songs by a songwriter, page by page, until a new song is found.

        :return: A generator yielding song data.
        """
        page = 1
        url = f"{self.BASE_URL}/{PATHS['search']}"
        writer = WRITERS[random.randrange(0, len(WRITERS) - 1)]

        while True:
            headers = {
                'Accept': 'application/json',
            }
            query = {
                'apikey': self.API_KEY,
                'q_writer': writer,
                'page': page,
                'page_size': 10,
            }

            response = requests.get(
                url=url,
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

    def get_release(self, album_id: int):
        url = f"{self.BASE_URL}/{PATHS['album']}"
        headers = {
            'Accept': 'application/json',
        }
        query = {
            'apikey': self.API_KEY,
            'album_id': album_id,
        }

        response = requests.get(
            url=url,
            headers=headers,
            params=query,
        )
        data = response.json()

        if data['message']['header']['status_code'] != 200 or not data['message']['body']['album']:
            logging.error(data)
            raise ValueError('Invalid API response for album {id}', album_id)

        return data['message']['body']['album']