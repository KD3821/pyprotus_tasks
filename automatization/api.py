import logging
import sqlite3


url_patterns = [
    ('api/get_interests/<int:id>', lambda client_id: InterestsAPIService(client_id)),
    ('api/get_score/<int:id>', lambda client_id: ScoreAPIService(client_id))
]


def get_api_service(path_params: dict):
    url = ''
    id_key = None
    for key, path in path_params.items():
        if path.isnumeric():
            id_key = int(path)
            url += '<int:id>'
            continue
        url += f'{path}/'
    url = url.rstrip('/')

    for pattern in url_patterns:
        try:
            pattern.index(url)
            if id_key is not None:
                return pattern[-1](client_id=id_key)
        except ValueError:
            continue
    return None


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_db_con():
    conn = sqlite3.connect('backend.db')
    conn.row_factory = dict_factory
    return conn


class AbstractAPIService:
    SCORES = "score"
    INTERESTS = "interests"

    def __init__(self, client_id: int):
        self.client_id = client_id
        self.name = ''
        self.query = ''

    def retrieve_data(self):
        db_data = dict()
        try:
            conn = get_db_con()
            cursor = conn.execute(self.query, (self.client_id,))
            db_data = cursor.fetchone()
            if db_data:
                db_data.update({'service': self.name})
                db_data = self.format_data(db_data)
            conn.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
            pass
        return self.validate(db_data)

    def validate(self, data):
        if not data:
            data = {'error': True, 'client_id': self.client_id}
            logging.error(f"Предупреждение БД: отсутствуют данные для пользователя с id: {self.client_id}")
        return data

    @classmethod
    def format_data(cls, data):
        if data.get('service') == cls.INTERESTS:
            valid_data = dict()
            for key, value in data.items():
                valid_data.update({key: "true"}) if value == 1 else valid_data.update({key: "false"})
            return valid_data
        return data


class InterestsAPIService(AbstractAPIService):
    def __init__(self, client_id: int):
        super().__init__(client_id)
        self.name = "interests"
        self.query = """SELECT * FROM client_interests WHERE client_id = ?"""


class ScoreAPIService(AbstractAPIService):
    def __init__(self, client_id: int):
        super().__init__(client_id)
        self.name = "score"
        self.query = """SELECT * FROM client_scores WHERE client_id = ?"""


