from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase

from bnt_parser.models import ExternalSource, Line, Section, Song, Word
from bnt_searcher.clients.mw_client import fetch_inflections
from bnt_searcher.models import WordVariant, WordVariantLookup
from bnt_searcher.services.variant_service import get_variants


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_song(title='Test Song', artist='Test Artist', external_id=1):
    ext = ExternalSource.objects.create(
        source=ExternalSource.SourceEnum.GENIUS,
        external_id=external_id,
        endpoint=f'/songs/{external_id}',
    )
    return Song.objects.create(title=title, artist=artist, external_source=ext)


def _make_word(text, song=None):
    """Create a Word and optionally attach it to a line in a new song."""
    word = Word.objects.create(text=text)
    if song:
        section = Section.objects.create(
            song=song, order=1, type=Section.SectionTypeEnum.VERSE
        )
        line = Line.objects.create(lyrics=f'line with {text}', order=1, section=section)
        word.line.add(line)
    return word


# ---------------------------------------------------------------------------
# mw_client.fetch_inflections
# ---------------------------------------------------------------------------

class FetchInflectionsTestCase(TestCase):
    def _mock_response(self, json_data, status_code=200):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status = MagicMock()
        return mock

    def test_returns_inflections_from_entries(self):
        data = [
            {'ins': [{'if': 'ran'}, {'if': 'run\u00b7ning'}]},
            {'ins': [{'if': 'runs'}]},
        ]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('run')

        assert result == ['ran', 'running', 'runs']

    def test_strips_interpunct_bullet(self):
        data = [{'ins': [{'if': 'hap\u00b7pi\u00b7er'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('happy')

        assert result == ['happier']

    def test_strips_asterisk(self):
        data = [{'ins': [{'if': 'hap*pi*er'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('happy')

        assert result == ['happier']

    def test_deduplicates_forms(self):
        data = [
            {'ins': [{'if': 'ran'}]},
            {'ins': [{'if': 'ran'}]},
        ]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('run')

        assert result == ['ran']

    def test_returns_empty_when_response_is_suggestion_strings(self):
        data = ['running', 'runner', 'ran']
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('runn')

        assert result == []

    def test_returns_empty_when_response_is_empty(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response([])),
        ):
            result = fetch_inflections('xyz')

        assert result == []

    def test_returns_empty_on_request_exception(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  side_effect=requests.ConnectionError('network error')),
        ):
            result = fetch_inflections('run')

        assert result == []

    def test_returns_empty_on_http_error(self):
        mock_resp = self._mock_response({}, status_code=500)
        mock_resp.raise_for_status.side_effect = requests.HTTPError('500')
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=mock_resp),
        ):
            result = fetch_inflections('run')

        assert result == []

    def test_skips_entries_without_ins(self):
        data = [
            {'meta': {'id': 'run'}},
            {'ins': [{'if': 'ran'}]},
        ]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('run')

        assert result == ['ran']

    def test_uses_api_key_from_env(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'my-secret-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response([])) as mock_get,
        ):
            fetch_inflections('run')

        _, kwargs = mock_get.call_args
        assert kwargs['params']['key'] == 'my-secret-key'


# ---------------------------------------------------------------------------
# variant_service.get_variants
# ---------------------------------------------------------------------------

class GetVariantsTestCase(TestCase):
    def test_returns_cached_variants_without_calling_api(self):
        from datetime import datetime, timezone
        lookup = WordVariantLookup.objects.create(
            search_term='run', fetched_at=datetime.now(tz=timezone.utc)
        )
        WordVariant.objects.create(lookup=lookup, text='ran')
        WordVariant.objects.create(lookup=lookup, text='running')

        with patch('bnt_searcher.services.variant_service.fetch_inflections') as mock_fetch:
            result = get_variants('run')

        mock_fetch.assert_not_called()
        assert set(result) == {'ran', 'running'}

    def test_calls_api_on_cache_miss(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=['ran', 'running']) as mock_fetch:
            result = get_variants('run')

        mock_fetch.assert_called_once_with('run')
        assert result == ['ran', 'running']

    def test_persists_lookup_and_variants_on_cache_miss(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=['ran', 'runs']):
            get_variants('run')

        assert WordVariantLookup.objects.filter(search_term='run').exists()
        variant_texts = set(
            WordVariant.objects
            .filter(lookup__search_term='run')
            .values_list('text', flat=True)
        )
        assert variant_texts == {'ran', 'runs'}

    def test_creates_lookup_with_no_variants_when_api_returns_empty(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=[]):
            result = get_variants('xyz')

        assert result == []
        assert WordVariantLookup.objects.filter(search_term='xyz').exists()
        assert not WordVariant.objects.filter(lookup__search_term='xyz').exists()

    def test_does_not_create_duplicate_lookup_on_second_call(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=['ran']):
            get_variants('run')
            get_variants('run')

        assert WordVariantLookup.objects.filter(search_term='run').count() == 1


# ---------------------------------------------------------------------------
# WordSearchView — variants flag
# ---------------------------------------------------------------------------

class WordSearchVariantsViewTestCase(TestCase):
    def setUp(self):
        self.song = _make_song(title='Test Song', artist='Test Artist', external_id=1)
        self.word = _make_word('run', song=self.song)

    def test_variants_false_does_not_call_get_variants(self):
        with patch('bnt_searcher.views.get_variants') as mock_get_variants:
            response = self.client.get('/search/word/', {'word': 'run', 'variants': 'false'})

        mock_get_variants.assert_not_called()
        assert response.status_code == 200

    def test_variants_omitted_does_not_call_get_variants(self):
        with patch('bnt_searcher.views.get_variants') as mock_get_variants:
            response = self.client.get('/search/word/', {'word': 'run'})

        mock_get_variants.assert_not_called()
        assert response.status_code == 200

    def test_variants_true_calls_get_variants(self):
        with patch('bnt_searcher.views.get_variants', return_value=[]) as mock_get_variants:
            self.client.get('/search/word/', {'word': 'run', 'variants': 'true'})

        mock_get_variants.assert_called_once_with('run')

    def test_variants_expands_results_to_include_variant_words(self):
        variant_song = _make_song(title='Variant Song', artist='Test Artist', external_id=2)
        _make_word('ran', song=variant_song)

        with patch('bnt_searcher.views.get_variants', return_value=['ran']):
            response = self.client.get('/search/word/', {'word': 'run', 'variants': 'true'})

        assert response.status_code == 200
        data = response.json()
        titles = [r['title'] for r in data['data']['results']]
        assert 'Test Song' in titles
        assert 'Variant Song' in titles

    def test_variants_true_returns_empty_when_no_words_match(self):
        with patch('bnt_searcher.views.get_variants', return_value=['jumped']):
            response = self.client.get('/search/word/', {'word': 'jump', 'variants': 'true'})

        assert response.status_code == 200
        data = response.json()
        assert data['data']['results'] == []
        assert data['meta']['total_songs'] == 0

    def test_word_data_reflects_search_term_not_variants(self):
        with patch('bnt_searcher.views.get_variants', return_value=['ran', 'running']):
            response = self.client.get('/search/word/', {'word': 'run', 'variants': 'true'})

        data = response.json()
        assert data['data']['word']['text'] == 'run'
