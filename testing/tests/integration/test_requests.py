import os
import unittest
import functools
import datetime
import hashlib

import redis
from dotenv import load_dotenv

import api
from store import MyStore


load_dotenv()


def cases(args_list):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in args_list:
                new_args = args + (i if isinstance(i, tuple) else (i,))
                try:
                    func(*new_args)
                except AssertionError as e:
                    print(f'Failed: {func.__doc__}. Result: {e}. Arguments: {new_args[-1]}')
                    raise e
        return wrapper
    return decorator


class TestSuite(unittest.TestCase):
    store_conn_ok = False

    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = MyStore()

    def tearDown(self):
        self.context = {}
        self.headers = {}
        self.store = None

    @classmethod
    def setUpClass(cls):
        cls.store_conn_ok = cls.store_connected()

    @classmethod
    def tearDownClass(cls):
        cls.store_conn_ok = False

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    @staticmethod
    def set_valid_auth(request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode()
            ).hexdigest()
        else:
            msg = request.get("account", "") + request.get("login", "") + api.SALT
            request["token"] = hashlib.sha512(msg.encode()).hexdigest()

    @staticmethod
    def store_connected():
        try:
            redis_client = redis.Redis(
                host='127.0.0.1',
                port=6379,
                password=os.getenv('REDIS_PASSWORD')
            )
            return redis_client.ping()
        except redis.exceptions.ConnectionError:
            return False

    def test_empty_request(self):
        """ Test Empty Request """
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    def test_redis_available(self):
        """ Test Redis is Running"""
        if not self.store_conn_ok:
            raise unittest.SkipTest('No connection to store')
        redis_client = redis.Redis(
            host='127.0.0.1',
            port=6379,
            password=os.getenv('REDIS_PASSWORD')
        )
        self.assertTrue(redis_client.ping(), "Redis Connection Failed")

    @cases([
        {"account": "HiTech", "login": "admin", "method": "online_score", "token": "d525aa76873156b", "arguments": {}},
        {"account": "HiTech", "login": "", "method": "online_score", "token": "", "arguments": {}},
        {"account": "HiTech", "login": "", "method": "online_score", "token": "asdfdfdfda", "arguments": {}},
        {"account": "HiTech", "login": "den", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, request):
        """ Test Bad Credentials """
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "HiTech", "login": "den", "method": "online_score"},
        {"account": "HiTech", "login": "den", "arguments": {}},
        {"account": "HiTech", "method": "online_score", "arguments": {}},
        {"account": "HiTech", "login": "den", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        """ Test Invalid Request Method """
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases([
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "python@otus.ru"},
        {"phone": "79175002040", "email": "pythonotus.ru"},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "spython@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        """ Test Invalid Score """
        request = {"account": "HiTech", "login": "den", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        {"phone": "79175002040", "email": "python@otus.ru"},
        {"phone": 79175002040, "email": "python@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "python@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        """ Test OK Score """
        request = {"account": "HiTech", "login": "den", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        """ Test OK Score Admin """
        arguments = {"phone": "79175002040", "email": "python@otus.ru"}
        request = {"account": "HiTech", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        """ Test Invalid Interests """
        if not self.store_conn_ok:
            raise unittest.SkipTest('No connection to store')
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
    ])
    def test_ok_interests_request(self, arguments):
        """ Test OK Interests """
        if not self.store_conn_ok:
            raise unittest.SkipTest('No connection to store')
        request = {"account": "HiTech", "login": "den", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, str) for i in v)
                            for v in response.values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))


if __name__ == "__main__":
    unittest.main()

"""
to run tests:  python3 -m unittest discover -s tests/integration
"""