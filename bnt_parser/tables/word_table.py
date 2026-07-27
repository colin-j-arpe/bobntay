from bnt_parser.models import Line, Word


class WordTable:
    def find_word(self, word: str) -> Word | None:
        """
        Find a word record in the DB.

        :param word: The text of the word.
        :return: The Word object if found, else None.
        """
        from bnt_parser.models import Word

        return Word.objects.filter(text=word).first()

    def save_if_not_exists(self, text: str, line: Line) -> Word:
        """
        Check if the word exists in the DB; save new record if not.

        :param text: The text of the word.
        :return: The ID of the word.
        """
        from bnt_parser.models import Word

        word_object = self.find_word(word=text)

        if word_object is None:
            word_object = Word(text=text)
            word_object.save()

        word_object.line.add(line)

        return word_object

    def save_all(self, line_words: list[tuple[Line, list[str]]]) -> None:
        """
        Save every word of a song and its line links in a fixed number of queries.

        Saving word by word costs several round trips each, which is slow enough over a
        long-haul connection to the database to exhaust the request timeout on a large
        song. This does the same work in three queries regardless of word count.

        :param line_words: Pairs of a saved Line and the words parsed from it.
        """
        texts = {text for _, words in line_words for text in words}
        if not texts:
            return

        words_by_text = self.find_words(texts)

        new_words = [Word(text=text) for text in sorted(texts - words_by_text.keys())]
        if new_words:
            Word.objects.bulk_create(new_words)
            words_by_text = self.find_words(texts)

        link_model = Word.line.through
        links = [
            link_model(word_id=words_by_text[text].pk, line_id=line.pk)
            for line, words in line_words
            for text in words
        ]
        # A word repeated across lines yields one link per line; ignore_conflicts keeps
        # the unique (word, line) constraint from rejecting the whole batch on a re-save.
        link_model.objects.bulk_create(links, ignore_conflicts=True)

    def find_words(self, texts: set[str]) -> dict[str, Word]:
        """
        Look up several words at once, keyed by their text.

        :param texts: The word texts to look for.
        :return: A dict of text to the matching Word, omitting any that do not exist.
        """
        words_by_text: dict[str, Word] = {}
        for word in Word.objects.filter(text__in=texts).order_by("pk"):
            # Text is not unique, so keep the earliest match to mirror find_word().
            words_by_text.setdefault(word.text, word)

        return words_by_text
