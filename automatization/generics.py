import logging
import sqlite3

from database import DatabaseEngine


class AbstractAPIService:
    """
    Базовый класс работы с API сервисом
    """
    ALLOWED_METHODS = {'GET'}

    def __init__(self, method: str, db: DatabaseEngine):
        self.method = method
        self.db = db
        self.service = ''
        self.need_formatting = False
        self.skip_formatting_fields = list()
        self.page_size = 10

    def get(self):
        table = self.validate_service_props()
        query = f"SELECT * FROM {table}"
        return query

    def validate_service_props(self):  # check mandatory props
        try:
            table = getattr(self, 'table')
        except AttributeError:
            raise KeyError(f"Не установлено свойство 'table' для {self.__class__.__name__}")  # for debug
        return table

    def allowed_method(self):
        if self.method not in self.ALLOWED_METHODS:
            return False
        return True

    def format_get_data(self, data):  # format data from 1-0 to true-false (from db_records to repr) for 'GET'
        need_formatting = getattr(self, 'need_formatting')
        skip_fields = getattr(self, 'skip_formatting_fields')
        if need_formatting:
            valid_data = dict()
            for key, value in data.items():
                if key not in skip_fields:
                    valid_data.update({key: "true"}) if value == 1 else valid_data.update({key: "false"})
                else:
                    valid_data.update({key: value})
            return valid_data
        return data

    def get_response(self, query, **kwargs):  # for 'GET' request (fetch data from db)
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

    def response(self):  # calling 'METHOD'_response and response
        if not self.allowed_method():
            return {'error': True, 'method': self.method}
        fields_order = list()
        service_method = getattr(self, self.method.lower())
        response_method = getattr(self, self.method.lower() + '_response')
        if self.method in ('PUT', 'POST'):
            query, fields_order = service_method()
        else:
            query = service_method()
        response = response_method(query, fields_order=fields_order)
        return response


class AbstractListCreateAPIService(AbstractAPIService):
    """
    Класс для создания сущности или вывода списка всех сущностей
    """
    ALLOWED_METHODS = {'GET', 'POST'}

    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db)
        self.data = data

    def format_post_data(self, data, order):  # format data from true-false to 1-0 (from repr to db_records) for 'POST'
        value_list = list()
        need_formatting = getattr(self, 'need_formatting')
        if need_formatting:
            for key in order:
                value_list.append('1' if data.get(key) == 'true' else '0')
        else:
            for key in order:
                value_list.append(data.get(key))
        return tuple(value_list)

    def post_response(self, query, fields_order):  # for 'POST' request
        try:
            db_data = self.format_post_data(self.data, fields_order)
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, db_data)
            logging.info(f"Добавлена новая запись в таблицу БД - {self.table} - с id: {cursor.lastrowid}")
            conn.commit()
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.get_response(getattr(self, 'get').__call__())


class AbstractDetailAPIService(AbstractAPIService):
    """
    Класс для получения/редактирования/удаления сущности
    """
    ALLOWED_METHODS = {'GET', 'PUT', 'DELETE'}

    def __init__(self,  method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db)
        self.client_id = client_id
        self.data = data

    def get(self):  # overridden 'get' method for detail repr
        table, field_id = self.validate_service_props()
        query = f"SELECT * FROM {table} WHERE {field_id} = ?"
        return query

    def delete(self):
        table, field_id = self.validate_service_props()
        query = f"DELETE from {table} WHERE {field_id} = ?"""
        return query

    def validate_service_props(self):  # overridden 'validate_service_props' for detail repr
        try:
            table = getattr(self, 'table')
        except AttributeError:
            raise KeyError(f"Не установлено свойство 'table' для {self.__class__.__name__}")  # for debug
        try:
            field_id = getattr(self, 'field_id')
        except AttributeError:
            raise KeyError(f"Не установлено свойство 'field_id' для {self.__class__.__name__}")  # for debug
        return table, field_id

    def validate_data(self, data):
        if not data:
            data = {'error': True, 'client_id': self.client_id}
            logging.error(f"Предупреждение БД: отсутствуют данные для пользователя с id: {self.client_id}")
        return data

    def format_put_data(self, data, order):  # format data from true-false to 1-0 (from repr to db_records) for 'PUT'
        value_list = list()
        need_formatting = getattr(self, 'need_formatting', False)
        if need_formatting:
            for key in order:
                value_list.append('1' if data.get(key) == 'true' else '0')
        else:
            for key in order:
                value_list.append(data.get(key))
        return tuple(value_list)

    def get_response(self, query, **kwargs):  # overridden 'get_response' for detail repr
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

    def put_response(self, query, fields_order):  # for 'PUT' request
        try:
            db_data = self.format_put_data(self.data, fields_order)
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, (db_data + (str(self.client_id),)))
            logging.info(f"Изменена запись в таблице БД - {self.table} - для {self.field_id} c id: {self.client_id}")
            conn.commit()
            cursor.close()
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.get_response(getattr(self, 'get').__call__())

    def delete_response(self, query, **kwargs):  # for 'DELETE' request
        data = dict()
        try:
            conn = self.db.get_reg_con()
            cursor = conn.cursor()
            cursor.execute(query, (self.client_id,))
            conn.commit()
            cursor.close()
            logging.info(f"Удаление записи из таблицы БД: - {self.table} - для {self.field_id} c id: {self.client_id}")
            data = {'deleted': True, 'client_id': self.client_id}
        except sqlite3.Error as e:
            logging.error(f"нет соединения с БД: {e}")
        finally:
            if conn:
                conn.close()
        return self.validate_data(data)
