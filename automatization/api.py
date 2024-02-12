from database import DatabaseEngine
from generics import (
    AbstractDetailAPIService,
    AbstractListCreateAPIService,
)


class InterestsListCreateAPIService(AbstractListCreateAPIService):
    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db, data)
        self.service = "interests_all"
        self.table = "client_interests"
        self.need_formatting = True
        self.skip_formatting_fields = ["client_id"]

    def post(self):
        query = f"INSERT INTO {self.table} (travel, hitech, sport, music) VALUES (?, ?, ?, ?)"
        return query, ['travel', 'hitech', 'sport', 'music']


class InterestsDetailAPIService(AbstractDetailAPIService):
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
    def __init__(self, method: str, db: DatabaseEngine, data: dict = None):
        super().__init__(method, db, data)
        self.service = "scores_all"
        self.table = "client_scores"

    def post(self):
        query = f"INSERT INTO {self.table} (score) VALUES (?)"
        return query, ['score']


class ScoreDetailAPIService(AbstractDetailAPIService):
    def __init__(self, method: str, client_id: int, db: DatabaseEngine, data: dict = None):
        super().__init__(method, client_id, db, data)
        self.service = "scores"
        self.table = "client_scores"
        self.field_id = "client_id"

    def put(self):
        query = f"UPDATE {self.table} SET score = ? WHERE {self.field_id} = ?"
        return query, ['score']
