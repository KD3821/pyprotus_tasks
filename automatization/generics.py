import logging
import sqlite3
import json

from database import DatabaseEngine


class AbstractAPIService:
    ALLOWED_METHODS = {'GET'}

    def __init__(self, method: str, db: DatabaseEngine):
        self.method = method
        self.db = db
        self.service = ''
        self.page_size = 10

    def get(self):
        table = self.validate_service_attrs()
        query = f"SELECT * FROM {table}"
        return query

    def validate_service_attrs(self):
        try:
            table = getattr(self, 'table')
        except AttributeError:
            raise KeyError(f"Не установлен аттрибут 'table' для {self.__class__.__name__}")  # for debug
        return table

    def allowed_method(self):
        if self.method not in self.ALLOWED_METHODS:
            return False
        return True

    def response(self):
        if not self.allowed_method():
            return {'error': True, 'method': self.method}
        fields_order = list()
        service_method = getattr(self, self.method.lower())
        response_method = getattr(self, self.method.lower() + '_response')
        if self.method in ('GET', 'DELETE'):
            query = service_method()
        elif self.method in ('PUT', 'POST'):
            query, fields_order = service_method()
        response = response_method(query, fields_order=fields_order)
        return response

    def format_get_data(self, data):  # for bool formatting from 1-0 to true-false
        need_formatting = getattr(self, 'need_formatting', False)
        if need_formatting:
            valid_data = dict()
            for key, value in data.items():
                if key != self.field_id:
                    valid_data.update({key: "true"}) if value == 1 else valid_data.update({key: "false"})
                else:
                    valid_data.update({key: value})
            return valid_data
        return data

    def get_response(self, query, **kwargs):
        counter = 0
        results = list()
        try:
            conn = self.db.get_dict_con()
            cursor = conn.execute(query)
            records = cursor.fetchmany(self.page_size)
            if records:
                for row in records:
                    counter += 1
                    row_data = self.format_get_data(row)
                    row_data.update({'service': self.service})
                    results.append(row_data)
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        data = {'total': counter, 'results': results}
        return {'json': True, 'data': data}


class AbstractListCreateAPIService(AbstractAPIService):
    ALLOWED_METHODS = {'GET', 'POST'}

    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db)
        self.data = data

    def post_response(self, query, fields_order):
        try:
            db_data = self.format_post_data(self.data, fields_order)
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, db_data)
            conn.commit()
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.get_response(getattr(self, 'get').__call__())

    def format_post_data(self, data, order):  # for bool formatting from 1-0 to true-false
        value_list = list()
        need_formatting = getattr(self, 'need_formatting', False)
        if need_formatting:
            for key in order:
                value_list.append('1' if data.get(key) == 'true' else '0')
        else:
            for key in order:
                value_list.append(data.get(key))
        return tuple(value_list)


class AbstractDetailAPIService:
    ALLOWED_METHODS = {'GET', 'PUT', 'DELETE'}

    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        self.method = method
        self.client_id = client_id
        self.db = db
        self.data = data
        self.service = ''

    def get(self):
        table, field_id = self.validate_service_attrs()
        query = f"SELECT * FROM {table} WHERE {field_id} = ?"
        return query

    def delete(self):
        table, field_id = self.validate_service_attrs()
        query = f"DELETE from {table} WHERE {field_id} = ?"""
        return query

    def allowed_method(self):
        if self.method not in self.ALLOWED_METHODS:
            return False
        return True

    def format_get_data(self, data):  # for bool formatting from 1-0 to true-false
        need_formatting = getattr(self, 'need_formatting', False)
        if need_formatting:
            valid_data = dict()
            for key, value in data.items():
                if key != self.field_id:
                    valid_data.update({key: "true"}) if value == 1 else valid_data.update({key: "false"})
                else:
                    valid_data.update({key: value})
            return valid_data
        return data

    def format_put_data(self, data, order):  # for bool formatting from 1-0 to true-false
        value_list = list()
        need_formatting = getattr(self, 'need_formatting', False)
        if need_formatting:
            for key in order:
                value_list.append('1' if data.get(key) == 'true' else '0')
        else:
            for key in order:
                value_list.append(data.get(key))
        return tuple(value_list)

    def response(self):
        if not self.allowed_method():
            return {'error': True, 'method': self.method}
        fields_order = list()
        service_method = getattr(self, self.method.lower())
        response_method = getattr(self, self.method.lower() + '_response')
        if self.method in ('GET', 'DELETE'):
            query = service_method()
        elif self.method == 'PUT':
            query, fields_order = service_method()
        response = response_method(query, fields_order=fields_order)
        return response

    def delete_response(self, query, **kwargs):
        data = dict()
        try:
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, (self.client_id,))
            conn.commit()
            cursor.close()
            logging.info(f"Удаление записи из таблицы БД: {self.table} для {self.field_id} - {self.client_id}")
            data = {'deleted': True, 'client_id': self.client_id}
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.validate_data(data)

    def put_response(self, query, fields_order):
        try:
            db_data = self.format_put_data(self.data, fields_order)
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, (db_data + (str(self.client_id),)))
            conn.commit()
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.get_response(getattr(self, 'get').__call__())

    def get_response(self, query, **kwargs):
        db_data = dict()
        try:
            conn = self.db.get_dict_con()
            cursor = conn.execute(query, (self.client_id,))
            db_data = cursor.fetchone()
            if db_data:
                db_data = self.format_get_data(db_data)
                db_data.update({'service': self.service})
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.validate_data(db_data)

    def validate_data(self, data):
        if not data:
            data = {'error': True, 'client_id': self.client_id}
            logging.error(f"Предупреждение БД: отсутствуют данные для пользователя с id: {self.client_id}")
        return data

    def validate_service_attrs(self):
        try:
            table = getattr(self, 'table')
        except AttributeError:
            raise KeyError(f"Не установлен аттрибут 'table' для {self.__class__.__name__}")  # for debug
        try:
            field_id = getattr(self, 'field_id')
        except AttributeError:
            raise KeyError(f"Не установлен аттрибут 'field_id' для {self.__class__.__name__}")  # for debug
        return table, field_id
