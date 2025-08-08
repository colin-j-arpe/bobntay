class SongTable:
    """
    Class representing the song table in the database.
    This class is responsible for managing song data, including sections and lyrics.
    """

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.table_name = 'songs'