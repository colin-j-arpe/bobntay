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
        word_object.save()

        return word_object
