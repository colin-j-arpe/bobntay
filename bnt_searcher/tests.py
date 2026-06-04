from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase

from bnt_parser.models import ExternalSource, Line, Section, Song, Word
from bnt_searcher.clients.mw_client import fetch_inflections
from bnt_searcher.models import WordVariant, WordVariantAlias, WordVariantLookup
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

        assert result == (None, ['ran', 'running', 'runs'])

    def test_strips_interpunct_bullet(self):
        data = [{'ins': [{'if': 'hap\u00b7pi\u00b7er'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('happy')

        assert result == (None, ['happier'])

    def test_strips_asterisk(self):
        data = [{'ins': [{'if': 'hap*pi*er'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('happy')

        assert result == (None, ['happier'])

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

        assert result == (None, ['ran'])

    def test_returns_empty_when_response_is_suggestion_strings(self):
        data = ['running', 'runner', 'ran']
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            result = fetch_inflections('runn')

        assert result == (None, [])

    def test_returns_empty_when_response_is_empty(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response([])),
        ):
            result = fetch_inflections('xyz')

        assert result == (None, [])

    def test_returns_empty_on_request_exception(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  side_effect=requests.ConnectionError('network error')),
        ):
            result = fetch_inflections('run')

        assert result == (None, [])

    def test_returns_empty_on_http_error(self):
        mock_resp = self._mock_response({}, status_code=500)
        mock_resp.raise_for_status.side_effect = requests.HTTPError('500')
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=mock_resp),
        ):
            result = fetch_inflections('run')

        assert result == (None, [])

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

        assert result == (None, ['ran'])

    def test_uses_api_key_from_env(self):
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'my-secret-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response([])) as mock_get,
        ):
            fetch_inflections('run')

        _, kwargs = mock_get.call_args
        assert kwargs['params']['key'] == 'my-secret-key'

    def test_returns_headword_from_meta_stems(self):
        data = [
            {
                'meta': {'stems': ['run', 'running', 'ran']},
                'ins': [{'if': 'ran'}, {'if': 'running'}],
            }
        ]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            headword, inflections = fetch_inflections('run')

        assert headword == 'run'
        assert inflections == ['ran', 'running']

    def test_headword_strips_interpunct_and_asterisk(self):
        data = [{'meta': {'stems': ['hap\u00b7p*y']}, 'ins': []}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            headword, _ = fetch_inflections('happy')

        assert headword == 'happy'

    def test_returns_none_headword_when_meta_stems_absent(self):
        data = [{'ins': [{'if': 'ran'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            headword, _ = fetch_inflections('run')

        assert headword is None

    def test_returns_none_headword_when_meta_stems_empty(self):
        data = [{'meta': {'stems': []}, 'ins': [{'if': 'ran'}]}]
        with (
            patch.dict('os.environ', {'MW_API_KEY': 'test-key'}),
            patch('bnt_searcher.clients.mw_client.requests.get',
                  return_value=self._mock_response(data)),
        ):
            headword, _ = fetch_inflections('run')

        assert headword is None


# ---------------------------------------------------------------------------
# variant_service.get_variants
# ---------------------------------------------------------------------------

class GetVariantsTestCase(TestCase):
    def test_alias_hit_returns_variants_without_api_call(self):
        lookup = WordVariantLookup.objects.create(
            headword='run', fetched_at=datetime.now(tz=timezone.utc)
        )
        WordVariant.objects.create(lookup=lookup, text='ran')
        WordVariant.objects.create(lookup=lookup, text='running')
        WordVariantAlias.objects.create(searched_term='run', lookup=lookup)

        with patch('bnt_searcher.services.variant_service.fetch_inflections') as mock_fetch:
            result = get_variants('run')

        mock_fetch.assert_not_called()
        assert set(result) == {'ran', 'running'}

    def test_alias_miss_headword_exists_creates_alias_no_new_lookup(self):
        lookup = WordVariantLookup.objects.create(
            headword='run', fetched_at=datetime.now(tz=timezone.utc)
        )
        WordVariant.objects.create(lookup=lookup, text='ran')

        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=('run', ['ran'])):
            result = get_variants('run')

        assert WordVariantLookup.objects.count() == 1
        assert WordVariantAlias.objects.filter(searched_term='run', lookup=lookup).exists()
        assert result == ['ran']

    def test_alias_miss_no_lookup_creates_lookup_variants_alias(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=('run', ['ran', 'running'])):
            result = get_variants('running')

        lookup = WordVariantLookup.objects.get(headword='run')
        assert set(
            WordVariant.objects.filter(lookup=lookup).values_list('text', flat=True)
        ) == {'ran', 'running'}
        assert WordVariantAlias.objects.filter(searched_term='running', lookup=lookup).exists()
        assert set(result) == {'ran', 'running'}

    def test_none_headword_falls_back_to_search_term_as_headword(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=(None, [])):
            result = get_variants('xyz')

        lookup = WordVariantLookup.objects.get(headword='xyz')
        assert WordVariantAlias.objects.filter(searched_term='xyz', lookup=lookup).exists()
        assert result == []

    def test_second_call_is_alias_hit_no_api_call(self):
        with patch('bnt_searcher.services.variant_service.fetch_inflections',
                   return_value=('run', ['ran'])) as mock_fetch:
            get_variants('run')
            get_variants('run')

        mock_fetch.assert_called_once()


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
