import logging
import sqlite3

from database import DatabaseEngine


class AbstractAPIService:
    pass


class AbstractDetailAPIService:
    NEED_FORMATTING = ("interests",)
    ALLOWED_METHODS = {'GET', 'PUT', 'DELETE'}
    SAFE_METHODS = {'GET', 'OPTIONS'}

    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        self.method = method
        self.client_id = client_id
        self.db = db
        self.data = data
        self.name = ''

    @classmethod
    def format_get_data(cls, data):
        if data.get('service') in cls.NEED_FORMATTING:
            valid_data = dict()
            for key, value in data.items():
                if key not in ('client_id', 'service'):
                    valid_data.update({key: "true"}) if value == 1 else valid_data.update({key: "false"})
                else:
                    valid_data.update({key: value})
            return valid_data
        return data

    def format_put_data(self, data, order):
        value_list = list()
        if self.name in self.NEED_FORMATTING:
            for key in order:
                value_list.append('1' if data.get(key) == 'true' else '0')
        else:
            for key in order:
                value_list.append(data.get(key))
        return tuple(value_list)

    def response(self):
        fields_order = list()
        service_method = getattr(self, self.method.lower())
        response_method = getattr(self, self.method.lower() + '_response')
        if self.method in self.SAFE_METHODS:
            query = service_method()
        else:
            query, fields_order = service_method()
        response = response_method(query, fields_order=fields_order)
        return response

    def put_response(self, query, fields_order):
        try:
            db_data = self.format_put_data(self.data, fields_order)
            conn = self.db.get_update_con()
            cursor = conn.cursor()
            cursor.execute(query, (db_data + (str(self.client_id),)))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
            pass
        return self.get_response(getattr(self, 'get').__call__())

    def get_response(self, query, **kwargs):
        db_data = dict()
        try:
            conn = self.db.get_dict_con()
            cursor = conn.execute(query, (self.client_id,))
            db_data = cursor.fetchone()
            if db_data:
                db_data.update({'service': self.name})
                db_data = self.format_get_data(db_data)
            cursor.close()
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


class InterestsDetailAPIService(AbstractDetailAPIService):
    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, client_id, db, data)
        self.name = "interests"

    def get(self):
        query = """SELECT * FROM client_interests WHERE client_id = ?"""
        return query

    def put(self):
        query = """UPDATE client_interests SET travel = ?, hitech = ?, sport = ?, music = ? WHERE client_id = ?"""
        return query, ['travel', 'hitech', 'sport', 'music']


class ScoreDetailAPIService(AbstractDetailAPIService):
    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, client_id, db, data)
        self.name = "score"

    def get(self):
        query = """SELECT * FROM client_scores WHERE client_id = ?"""
        return query

    def put(self):
        query = """UPDATE client_scores SET score = ? WHERE client_id = ?"""
        return query, ['score']


class InterestsListCreateAPIService(AbstractAPIService):
    pass


class ScoreListCreateAPIService(AbstractAPIService):
    pass
