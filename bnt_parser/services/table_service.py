from bnt_parser.tables.external_source_table import ExternalSourceTable
from bnt_parser.tables.line_table import LineTable
from bnt_parser.tables.release_table import ReleaseTable
from bnt_parser.tables.section_table import SectionTable
from bnt_parser.tables.song_table import SongTable
from bnt_parser.tables.word_table import WordTable
from bnt_parser.tables.writer_table import WriterTable

class TableService:
    TABLE_NAMES = {
        "external_source": ExternalSourceTable,
        "line": LineTable,
        "release": ReleaseTable,
        "section": SectionTable,
        "song": SongTable,
        "word": WordTable,
        "writer": WriterTable,
    }
    TABLES = {}

    # def __init__(self, table):

    def get_table(self, name: str):
        if name not in self.TABLE_NAMES.keys():
            raise ValueError(f"Table '{name}' is not recognised.")

        if name not in self.TABLES.keys():
            self.TABLES[name] = self.TABLE_NAMES[name]()
        return self.TABLES[name]
