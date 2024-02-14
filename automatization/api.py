from database import DatabaseEngine
from generics import (
    AbstractDetailAPIService,
    AbstractListCreateAPIService,
)


class InterestsListCreateAPIService(AbstractListCreateAPIService):
    """
    service - добавляется в ответ от API - для информации
    table - таблица в БД
    need_formatting - нужно ли форматировать true-false в 1-0 для работы с БД (по-умолчанию: False)
    skip_formatting_fields - список полей, которые будут пропускаться при форматировании, если need_formatting=True
    page_size - задается кол-во записей в ответе от сервиса при запросе списка сущностей (по-умолчанию: 10)

    В данном классе нужно реализовать метод 'post' - если необходимо переопределить метод 'get'
    """
    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db, data)
        self.service = "interests_all"
        self.table = "client_interests"
        self.need_formatting = True
        self.skip_formatting_fields = ["client_id"]
        self.page_size = 20

    def post(self):
        query = f"INSERT INTO {self.table} (travel, hitech, sport, music) VALUES (?, ?, ?, ?)"
        return query, ['travel', 'hitech', 'sport', 'music']


class InterestsDetailAPIService(AbstractDetailAPIService):
    """
    service - добавляется в ответ от API - для информации
    table - таблица в БД
    need_formatting - нужно ли форматировать true-false в 1-0 для работы с БД (по-умолчанию: False)
    skip_formatting_fields - список полей, которые будут пропускаться при форматировании, если need_formatting=True
    field_id - название колонки таблицы БД, которая является Первичным Ключом

    В данном классе нужно реализовать метод 'put' - если необходимо, переопределить методы 'get', 'delete'
    """
    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, client_id, db, data)
        self.service = "interests"
        self.table = "client_interests"
        self.field_id = "client_id"
        self.need_formatting = True
        self.skip_formatting_fields = ["client_id"]

    def put(self):
        query = f"UPDATE {self.table} SET travel = ?, hitech = ?, sport = ?, music = ? WHERE {self.field_id} = ?"
        return query, ['travel', 'hitech', 'sport', 'music']


class ScoreListCreateAPIService(AbstractListCreateAPIService):
    """
    service - добавляется в ответ от API - для информации
    table - таблица в БД
    need_formatting - нужно ли форматировать true-false в 1-0 для работы с БД (по-умолчанию: False)
    skip_formatting_fields - список полей, которые будут пропускаться при форматировании, если need_formatting=True
    page_size - задается кол-во записей в ответе от сервиса при запросе списка сущностей (по-умолчанию: 10)

    В данном классе нужно реализовать метод 'post' - если необходимо переопределить метод 'get'
    """
    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db, data)
        self.service = "scores_all"
        self.table = "client_scores"

    def post(self):
        query = f"INSERT INTO {self.table} (score) VALUES (?)"
        return query, ['score']


class ScoreDetailAPIService(AbstractDetailAPIService):
    """
    service - добавляется в ответ от API - для информации
    table - таблица в БД
    need_formatting - нужно ли форматировать true-false в 1-0 для работы с БД (по-умолчанию: False)
    skip_formatting_fields - список полей, которые будут пропускаться при форматировании, если need_formatting=True
    field_id - название колонки таблицы БД, которая является Первичным Ключом

    В данном классе нужно реализовать метод 'put' - если необходимо, переопределить методы 'get', 'delete'
    """
    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, client_id, db, data)
        self.service = "scores"
        self.table = "client_scores"
        self.field_id = "client_id"

    def put(self):
        query = f"UPDATE {self.table} SET score = ? WHERE {self.field_id} = ?"
        return query, ['score']
