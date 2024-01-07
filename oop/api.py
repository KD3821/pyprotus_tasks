#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from scoring import get_score, get_interests


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class FieldMeta(type):
    INIT_PARAMS = {
        'required': bool,
        'nullable': bool
    }

    def custom_init(self, *args, **kwargs):
        for key, value in self.__class__.INIT_PARAMS.items():
            setattr(self, key, value)

    @staticmethod
    def validate_attr(attr):
        return attr

    def get_validator(self, instance):
        try:
            local_validator = getattr(instance, 'validate_attr')
        except AttributeError:
            return self.__class__.validate_attr
        return local_validator

    def __set_name__(self, owner, name):
        self.name = '_' + name

    def __get__(self, instance, owner):
        return getattr(instance, self.name, '')

    def __set__(self, instance, value):
        validator = self.get_validator(instance)
        valid_value = validator(value)
        setattr(instance, self.name, valid_value)

    def __new__(mcs, name, bases, attrs):
        attrs.update({
            '__init__': mcs.custom_init,
            '__set_name__': mcs.__set_name__,
            '__get__': mcs.__get__,
            '__set__': mcs.__set__,
            'get_validator': mcs.get_validator,
        })
        return type.__new__(mcs, name, bases, attrs)


class MyStr(str):
    def __add__(self, val):
        return MyStr(super().__add__(str(val)))


class RequestMeta(type):
    def custom_init(self, *args, **kwargs):
        m_args = kwargs.get('method_args')
        for key, value in self.class_attrs.items():
            if isinstance(m_args, dict):
                if key in m_args.keys():
                    value = m_args.get(key)
            if isinstance(value, CharField):
                value = MyStr(value)
            setattr(self, key, value)

    def __init__(cls, name, bases, attrs):
        cls.class_attrs = attrs
        cls.__init__ = RequestMeta.custom_init


class CharField(object, metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, field):
        if not isinstance(field, str):
            raise ValueError({cls.__name__: 'Поле должно быть строкой.'})
        return field


class ArgumentsField(object, metaclass=FieldMeta):
    def __get__(self, instance, owner):
        return getattr(instance, self.name, {})

    def __set__(self, instance, args_data={}):
        setattr(instance, self.name, args_data)


class EmailField(CharField):

    @classmethod
    def validate_attr(cls, email):
        if email.__class__ == str:
            if email.find('@') == -1:
                raise ValueError({cls.__name__: 'Ошибка валидации: email должен содержать @ символ.'})
            elif email.count('@') > 1:
                raise ValueError({cls.__name__: 'Ошибка валидации: некорректный email'})
            return email


class PhoneField(object, metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, value):
        if isinstance(value, (int, str)):
            number = str(value)
            if len(number) > 0:
                if number[0] != '7':
                    raise ValueError({cls.__name__: 'Некорректный номер телефона: первая цифра должна быть 7.'})
                elif len(number) != 11:
                    raise ValueError({cls.__name__: 'Некорректный номер телефона: должен содержать 11 символов.'})
                elif not number.isnumeric():
                    raise ValueError({cls.__name__: 'Некорректный номер телефона: должен состоять из цифр.'})
                return value


class DateField(object, metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, date):
        if isinstance(date, str):
            try:
                formatted_date = datetime.datetime.strptime(date, "%d.%m.%Y")
            except Exception as e:
                raise ValueError({cls.__name__: f'Неверный формат даты: {e}'})
            return formatted_date


class BirthDayField(object, metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, value):
        if isinstance(value, str):
            try:
                formatted_date = datetime.datetime.strptime(value, "%d.%m.%Y")
                if formatted_date >= datetime.datetime(1970, 1, 1):
                    return formatted_date
            except Exception as e:
                raise ValueError({cls.__name__: f'Неверный формат даты: {e}'})
            raise ValueError({cls.__name__: 'Дата рождения не может быть ранее 01 января 1970'})


class GenderField(object, metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, gender):
        if gender != '' and gender is not None:
            if isinstance(gender, int):
                if gender not in GENDERS.keys():
                    raise ValueError({cls.__name__: 'Указаны неверный вариант пола.'})
                return gender
            if not isinstance(gender, GenderField):
                raise ValueError({cls.__name__: 'Указатель на пол должен быть числом.'})


class ClientIDsField(object, metaclass=FieldMeta):
    def __init__(self, clients_ids=[], required=True):
        self.required = required
        self.clients_ids = clients_ids

    def __len__(self):
        return len(self.clients_ids)

    @classmethod
    def validate_attr(cls, attr):
        if not isinstance(attr, list) or len(attr) == 0:
            raise ValueError({cls.__name__: 'Значение поля должно являться непустым массивом.'})
        for i in attr:
            if not isinstance(i, int):
                raise ValueError({cls.__name__: 'Массив должен содержать только целые числа.'})
        return attr


class ClientsInterestsRequest(object, metaclass=RequestMeta):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(object, metaclass=RequestMeta):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(object, metaclass=RequestMeta):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

    @is_admin.setter
    def is_admin(self, ADMIN_LOGIN):
        self._is_admin = True if self.login == ADMIN_LOGIN else False


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode()
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode()
        ).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    response, code = None, None
    method_name = request.get('body').get('method')
    if method_name:
        handlers = {
            "online_score": online_score_handler,
            "clients_interests": clients_interests_handler
        }
        response, code = handlers.get(method_name)(request, ctx, store)

    return response, code


def check_mandatory_fields(req_body):
    mandatory_fields = ('login', 'method', 'token', 'arguments')
    for key in mandatory_fields:
        if key not in req_body.keys():
            return f"Отсутствует обязательное для подсчета score поле {key}."
    return None


def check_method_args(arguments):
    has_list = list()
    ok = False
    pairs = [('phone', 'email'), ('first_name', 'last_name'), ('gender', 'birthday')]
    for pair in pairs:
        first = arguments.get(pair[0])
        last = arguments.get(pair[-1])
        if first is not None and last is not None:
            ok = True
        for i in pair:
            interest = arguments.get(i)
            if interest:
                has_list.append(i)
    return {'ok': ok, 'has': has_list}


def online_score_handler(request, ctx, store):
    req_body = request.get('body')

    failed = check_mandatory_fields(req_body)

    if failed:
        return failed, INVALID_REQUEST

    try:
        req = MethodRequest(method_args=req_body)

        if check_auth(req) and req.login == "admin":
            return {"score": 42}, OK

        elif check_auth(req):
            if not isinstance(req.arguments, dict):
                return "Необходимо указать аргументы для подсчета score.", INVALID_REQUEST

            status = check_method_args(req.arguments)

            if not status.get('ok'):
                return ("Необходимо указать минимум одну из пар: phone-email, first name-last name, gender-birthday",
                        INVALID_REQUEST)

            score_req = OnlineScoreRequest(method_args=req.arguments)

            score = get_score(
                store=store,
                phone=score_req.phone,
                email=score_req.email,
                birthday=score_req.birthday,
                gender=score_req.gender,
                first_name=score_req.first_name,
                last_name=score_req.last_name
            )

            ctx.update({'has': status.get('has')})

            return {"score": score}, OK
        else:
            return "Forbidden", FORBIDDEN

    except ValueError as e:
        code = INVALID_REQUEST
        response = f"{e}"

    return response, code


def clients_interests_handler(request, ctx, store):
    req_body = request.get('body')

    failed = check_mandatory_fields(req_body)

    if failed:
        return failed, INVALID_REQUEST

    try:
        req = MethodRequest(method_args=req_body)

        if check_auth(req) and req.login == "admin":
            return {"score": 42}, OK

        elif check_auth(req):
            if not isinstance(req.arguments, dict):
                return "Необходимо указать аргументы для подсчета interests.", INVALID_REQUEST

            if len(req.arguments) == 0:
                return "Необходимо указать массив id клиентов для подсчета interests.", INVALID_REQUEST

            interests_req = ClientsInterestsRequest(method_args=req.arguments)

            response = dict()

            for client in interests_req.client_ids:

                interests = get_interests(
                    store=store,
                    cid=client
                )
                response.update({str(client): interests})

            ctx.update({'nclients': len(interests_req.client_ids)})

            return response, OK

        else:
            return "Forbidden", FORBIDDEN

    except ValueError as e:
        code = INVALID_REQUEST
        response = f"{e}"

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "online_score": online_score_handler,
        "clients_interests": clients_interests_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
