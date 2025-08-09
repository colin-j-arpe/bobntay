import os
import urllib.parse
import requests

class GeniusClient:
    CLIENT_ID = os.getenv("GENIUS_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GENIUS_CLIENT_SECRET")
    ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
    BASE_URL = 'https://api.genius.com'

    # def __init__(self, client_id, client_secret, access_token):

    def search(self, artist: str, title: str) -> dict | None:
        url = self.BASE_URL + '/search'
        query = {
            'q': f"{artist} {title}"
        }
        headers = {
            'Authorization': f'Bearer {self.ACCESS_TOKEN}',
            'Accept': 'application/json',
        }

        response = requests.get(
            url,
            params=urllib.parse.urlencode(query),
            headers=headers,
        )
        results = response.json()

        for hit in results['response']['hits']:
            song = hit['result']
            if song['primary_artist']['name'].lower() == artist.lower() and song['title'].lower() == title.lower():
                return song

        return None