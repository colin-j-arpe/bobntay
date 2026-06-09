import os
from collections import defaultdict

from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from bnt_parser.models import Line, Word, Writer
from bnt_searcher.services.variant_service import get_variants


def _format_word_text(text):
    """Capitalise 'i' and contractions starting with "i'" (e.g. i'm → I'm)."""
    if text == 'i' or text.startswith("i'"):
        return text[0].upper() + text[1:]
    return text


def _build_page_url(request, page):
    params = request.GET.copy()
    params['page'] = page
    return request.build_absolute_uri(f'?{params.urlencode()}')


def _empty_response(word_data, page, page_size):
    return {
        'data': {'word': word_data, 'results': []},
        'meta': {
            'total_songs': 0,
            'total_lines': 0,
            'writers_in_results': [],
            'page': page,
            'page_size': page_size,
            'previous_page_url': None,
            'next_page_url': None,
        },
    }


PRIMARY_WRITERS = [
    name.strip()
    for name in os.environ.get('GENIUS_WRITERS', 'Robert Pollard,Taylor Swift').split(',')
    if name.strip()
]


class WriterListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        exclude_q = Q()
        for name in PRIMARY_WRITERS:
            exclude_q |= Q(name__iexact=name)
        names = (
            Writer.objects
            .exclude(exclude_q)
            .order_by('name')
            .values_list('name', flat=True)
        )
        return Response({'writers': list(names)})


class WordSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        search_term = request.GET.get('word', '').strip().lower()
        if not search_term:
            return Response({'detail': 'The "word" parameter is required.'}, status=400)

        primary_writers = request.GET.getlist('primary_writer')
        co_writers = request.GET.getlist('co_writer')
        section_types = [t.upper() for t in request.GET.getlist('section_type')]
        include_variants = request.GET.get('variants', '').lower() == 'true'
        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = max(1, min(50, int(request.GET.get('page_size', 20))))
        except (ValueError, TypeError):
            return Response({'detail': '"page" and "page_size" must be integers.'}, status=400)

        if include_variants:
            variant_texts = get_variants(search_term)
            all_terms = [search_term] + variant_texts
        else:
            all_terms = [search_term]

        word_obj = Word.objects.filter(text=search_term).first()
        word_data = {
            'id': word_obj.id if word_obj else None,
            'text': _format_word_text(search_term),
        }

        matching_words = Word.objects.filter(text__in=all_terms)
        if not matching_words.exists():
            return Response(_empty_response(word_data, page, page_size))

        lines_qs = (
            Line.objects
            .filter(words__in=matching_words)
            .select_related('section', 'section__song')
            .prefetch_related('section__song__writers')
            .order_by('section__song_id', 'section__order', 'order')
        )

        if section_types:
            lines_qs = lines_qs.filter(section__type__in=section_types)

        if primary_writers:
            q = Q()
            for pw in primary_writers:
                q |= Q(section__song__writers__name__icontains=pw)
            lines_qs = lines_qs.filter(q)

        if co_writers:
            for cw in co_writers:
                lines_qs = lines_qs.filter(section__song__writers__name__icontains=cw)

        lines_qs = lines_qs.distinct()

        # Group lines into song → section → lines, preserving order
        song_order = []
        song_map = {}
        section_map = {}       # section_id → {'obj': Section, 'lines': [Line, ...]}
        song_sections = defaultdict(list)  # song_id → [section_id, ...]

        for line in lines_qs:
            section = line.section
            song = section.song
            if song.id not in song_map:
                song_order.append(song.id)
                song_map[song.id] = song
            if section.id not in section_map:
                section_map[section.id] = {'obj': section, 'lines': []}
                song_sections[song.id].append(section.id)
            section_map[section.id]['lines'].append(line)

        total_songs = len(song_order)
        total_lines = sum(len(s['lines']) for s in section_map.values())

        all_writers = set()
        for song_id in song_order:
            for writer in song_map[song_id].writers.all():
                all_writers.add(writer.name)

        # Paginate by song
        start = (page - 1) * page_size
        end = start + page_size
        page_song_ids = song_order[start:end]

        results = []
        for song_id in page_song_ids:
            song = song_map[song_id]
            sections_out = []
            for section_id in song_sections[song_id]:
                s = section_map[section_id]
                section = s['obj']
                sections_out.append({
                    'id': section.id,
                    'type': section.type.value,
                    'order': section.order,
                    'lines': [
                        {'id': line.id, 'order': line.order, 'lyric': line.lyrics}
                        for line in s['lines']
                    ],
                })
            results.append({
                'id': song_id,
                'title': song.title,
                'artist': song.artist,
                'writers': [
                    {'id': w.id, 'name': w.name}
                    for w in song.writers.all()
                ],
                'sections': sections_out,
            })

        return Response({
            'data': {
                'word': word_data,
                'results': results,
            },
            'meta': {
                'total_songs': total_songs,
                'total_lines': total_lines,
                'writers_in_results': sorted(all_writers),
                'page': page,
                'page_size': page_size,
                'previous_page_url': _build_page_url(request, page - 1) if page > 1 else None,
                'next_page_url': _build_page_url(request, page + 1) if end < total_songs else None,
            },
        })
