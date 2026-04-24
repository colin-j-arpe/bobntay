import os

from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from bnt_parser.clients.genius_client import GeniusClient
from bnt_parser.services.song_service import SongService
from bnt_parser.services.table_service import TableService


class ApiKeyPermission(BasePermission):
    def has_permission(self, request, view):
        api_key = request.headers.get('X-Api-Key')
        return bool(api_key and api_key == os.environ.get('PARSE_API_KEY'))


class NextSongView(APIView):
    """
    GET: Find the next unprocessed song and return its track data and Genius record.
    The caller is expected to fetch the Genius page HTML and submit it to SubmitPageView.
    """
    permission_classes = [ApiKeyPermission]

    def get(self, request):
        song_service = SongService(
            table_service=TableService(),
            genius_client=GeniusClient(),
        )
        result = song_service.find_next_track()
        if result is None:
            return Response({'detail': 'No new songs found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class SubmitPageView(APIView):
    """
    POST: Accept pre-fetched Genius page HTML along with track metadata, parse the
    lyrics, and save the song to the database.

    Expected JSON body:
        track_data    (dict)  — the track object returned by NextSongView
        genius_record (dict)  — the genius_record object returned by NextSongView
        html          (str)   — the raw HTML content of the Genius lyrics page
    """
    permission_classes = [ApiKeyPermission]

    def post(self, request):
        track_data = request.data.get('track_data')
        genius_record = request.data.get('genius_record')
        html = request.data.get('html')

        if not track_data or not genius_record or not html:
            return Response(
                {'detail': 'Missing required fields: track_data, genius_record, html.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        song_service = SongService(
            table_service=TableService(),
            genius_client=GeniusClient(),
        )
        song_service.load_prefetched(
            track_data=track_data,
            genius_record=genius_record,
            html=html.encode('utf-8'),
        )
        song_service.save_song()
        song_service.save_lyrics()

        return Response({'detail': f'Saved "{song_service.title}" by {song_service.artist}.'})
