import sqlite3
import logging


class DatabaseEngine:
    INITIAL_SCORE_VALUES = [
        (1, 3.4),
        (2, 4.0),
        (3, 5.0),
        (4, 2.7),
        (5, 3.9)
    ]
    INITIAL_INTERESTS_VALUES = [
        (1, 0, 1, 1, 0),
        (2, 1, 0, 1, 0),
        (3, 0, 1, 0, 1),
        (4, 1, 1, 0, 0),
        (5, 0, 0, 1, 1)
    ]

    def __init__(self, db_name: str):
        self.db_name = db_name
        try:
            open(db_name)
            logging.error(f"Найден файл с БД: '{db_name}'")
        except IOError as e:
            if e.args[0] == 2:  # No such file or dir
                logging.error(f"Файл с БД не найден - создан файл '{db_name}'")
                self.initialize_db(db_name)

    @classmethod
    def initialize_db(cls, db_name):
        logging.info(f"Дефолтные данные для старта работы сохранены в БД")
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client_scores
            ([client_id] INTEGER PRIMARY KEY, [score] REAL)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client_interests
            ([client_id] INTEGER PRIMARY KEY, [travel] INTEGER, [hitech] INTEGER, [sport] INTEGER, [music] INTEGER)
            """
        )
        cursor.executemany("INSERT INTO client_scores VALUES (?, ?)", cls.INITIAL_SCORE_VALUES)
        cursor.executemany("INSERT INTO client_interests VALUES (?, ?, ?, ?, ?)", cls.INITIAL_INTERESTS_VALUES)
        conn.commit()
        conn.close()

    @staticmethod
    def dict_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    def get_dict_con(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = self.dict_factory
        return conn

    def get_update_con(self):
        conn = sqlite3.connect(self.db_name)
        return conn
