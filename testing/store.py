import os
import random
import json
import logging
from time import sleep

import redis
from dotenv import load_dotenv


load_dotenv()


class MyStore:
    """
    Класс для взаимодействия с хранилищем
    """
    GET = 'GET'
    CACHE_GET = 'CACHE_GET'
    CACHE_SET = 'CACHE_SET'
    INTERESTS = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus"]
    TRY_GET = 1
    TRY_CACHE = 5  # may reduce for running tests

    @classmethod
    def get(cls, client):
        interests = cls.cache_get(key=client, name=cls.GET)

        if interests is None:
            random_interests = json.dumps(random.sample(cls.INTERESTS, 2))

            cls.cache_set(key=client, score=random_interests, name=cls.GET)

            interests = random_interests

        return interests

    @classmethod
    def cache_get(cls, key: str, name: str = None) -> float:
        if name is None:
            name = cls.CACHE_GET

        conn = cls.storage_processor(uid=key, name=name)

        if isinstance(conn, redis.Redis):
            value = conn.get(key)

            if value is not None:
                if name == cls.CACHE_GET:
                    value = float(value)
                logging.info(f'Получение данных ({value}) для [{key}] из хранилища')
            else:
                if name == cls.CACHE_GET:
                    logging.info(f'Для [{key}] отсутствуют данные score в хранилище.')
                else:
                    logging.info(f'Отсутствуют данные - рандомные данные interests будут сохранены для [{key}]')

            return value

        if not isinstance(conn, redis.Redis) and name == cls.GET:
            raise ValueError(f'Ошибка подключения к хранилищу: метод GET')

    @classmethod
    def cache_set(cls, key: str, score: int | str, seconds: int = None, name: str = None) -> None:
        if name is None:
            name = cls.CACHE_SET

        conn = cls.storage_processor(uid=key, name=name)

        if isinstance(conn, redis.Redis):
            logging.info(f'Сохранение данных ({score}) для [{key}] в хранилище.')
            conn.set(name=key, value=score, ex=seconds)

    @classmethod
    def storage_processor(cls, uid: str, name: str) -> redis.Redis:
        try_number = cls.TRY_GET if name == cls.GET else cls.TRY_CACHE

        conn_gen = cls.connect(uid=uid, name=name, try_number=try_number)
        conn = next(conn_gen)

        while isinstance(conn, type(None)):
            conn = next(conn_gen)

        if not isinstance(conn, redis.Redis):
            logging.info(conn)
        return conn

    @staticmethod
    def connect(uid: str, name: str, try_number: int) -> redis.Redis:
        counter = 0

        while try_number:
            try:
                redis_client = redis.Redis(
                    host='127.0.0.1',
                    port=6379,
                    password=os.getenv('REDIS_PASSWORD')
                )

                ping = redis_client.ping()

                if ping:
                    logging.info(f'Успешное "{name}"-подключение к хранилищу для [{uid}]')
                    yield redis_client

            except redis.exceptions.ConnectionError:
                counter += 1
                try_number -= 1

                logging.info(f'Попытка {counter} "{name}"-подключения к хранилищу для [{uid}] - осталось '
                             f'попыток: {try_number}')

                if try_number > 0:
                    yield
                sleep(1)

        yield f'Не удалось установить "{name}"-подключение к хранилищу для [{uid}].'
