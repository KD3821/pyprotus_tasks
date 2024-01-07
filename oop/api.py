#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    """
    Метакласс, от которого наследуется класс Поля запроса
    """
    def custom_init(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def validate_attr(attr, label):
        # does nothing - may implement some validation here
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
        label = self.name[1:]
        valid_value = validator(value, label)
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
    """
    Вспомогательный класс - добавляет возможность конкатенации строк (для работы авторизации: account + login + SALT)
    """
    def __add__(self, val):
        return MyStr(super().__add__(str(val)))


class RequestMeta(type):
    """
    Метакласс, от которого наследуется класс Запроса
    """
    def custom_init(self, *args, **kwargs):
        m_args = kwargs.get('method_args')
        m_args_are_valid = isinstance(m_args, dict)
        for key, value in self.class_attrs.items():
            if m_args_are_valid:
                if key in m_args.keys():
                    value = m_args.get(key)
            if isinstance(value, CharField):
                value = MyStr(value)
            setattr(self, key, value)

    def __init__(cls, name, bases, attrs):
        cls.class_attrs = attrs
        cls.__init__ = RequestMeta.custom_init


class CharField(metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, field, label):
        if not isinstance(field, str):
            raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: поле должно быть строкой.')
        return field


class ArgumentsField(metaclass=FieldMeta):

    def __get__(self, instance, owner):
        return getattr(instance, self.name, {})

    def __set__(self, instance, args_data={}):
        setattr(instance, self.name, args_data)


class EmailField(CharField):

    @classmethod
    def validate_attr(cls, email, label):
        if email.__class__ == str:
            if email.find('@') == -1:
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: email должен содержать @ символ.')
            elif email.count('@') > 1:
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: некорректный email')
            return email


class PhoneField(metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, value, label):
        if isinstance(value, (int, str)):
            number = str(value)
            if len(number) > 0:
                if number[0] != '7':
                    raise ValueError(f'{label} - {cls.__name__}: Некорректный номер телефона: начинается не с 7.')
                elif len(number) != 11:
                    raise ValueError(f'{label} - {cls.__name__}: Некорректный номер телефона: не содержит 11 символов.')
                elif not number.isnumeric():
                    raise ValueError(f'{label} - {cls.__name__}: Некорректный номер телефона: должен состоять из цифр.')
                return value


class DateField(metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, date, label):
        if isinstance(date, str):
            try:
                formatted_date = datetime.datetime.strptime(date, "%d.%m.%Y")
            except Exception as e:
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: неверный формат даты: {e}')
            return formatted_date


class BirthDayField(metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, value, label):
        if isinstance(value, str):
            try:
                formatted_date = datetime.datetime.strptime(value, "%d.%m.%Y")
                if formatted_date >= datetime.datetime(1970, 1, 1):
                    return formatted_date
            except Exception as e:
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: неверный формат даты: {e}')
            raise ValueError(f'{label} - {cls.__name__}: Дата рождения не может быть ранее 01 января 1970')


class GenderField(metaclass=FieldMeta):

    @classmethod
    def validate_attr(cls, gender, label):
        if gender != '' and gender is not None:
            if isinstance(gender, int):
                if gender not in GENDERS.keys():
                    raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: указан неверный вариант пола.')
                if gender == 0:
                    gender = '0 is not False'
                return gender
            if not isinstance(gender, GenderField):
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: указатель на пол должен быть числом.')


class ClientIDsField(metaclass=FieldMeta):
    def __init__(self, clients_ids=[], required=True):
        self.required = required
        self.clients_ids = clients_ids

    def __len__(self):
        return len(self.clients_ids)

    @classmethod
    def validate_attr(cls, attr, label):
        if not isinstance(attr, list) or len(attr) == 0:
            raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: поле должно являться непустым массивом.')
        for i in attr:
            if not isinstance(i, int):
                raise ValueError(f'{label} - {cls.__name__}: Ошибка валидации: массив должен содержать целые числа.')
        return attr


class ClientsInterestsRequest(metaclass=RequestMeta):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(metaclass=RequestMeta):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(metaclass=RequestMeta):
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
    """
    Используется для тестирования
    """
    response, code = {'error': 'Default Error Message'}, INVALID_REQUEST
    method_name = request.get('body').get('method')
    if method_name:
        handlers = {
            "online_score": online_score_handler,
            "clients_interests": clients_interests_handler
        }
        response, code = handlers.get(method_name)(request, ctx, store)

    return response, code


def check_mandatory_fields(req_body):
    """
    Проверка, что в теле запроса присутствуют все обязательные поля ( required = True )
    """
    failed_list = list()
    for k, v in MethodRequest.class_attrs.items():
        required = getattr(v, 'required', None)
        if required and k not in req_body.keys():
            failed_list.append(k)
    if failed_list:
        msg = 'Заполните обязательное(ые) поле(я) для подсчета score:'
        for i in failed_list:
            msg += f' {i},'
        return msg.rstrip(',') + '.'
    return None


def check_method_args(arguments):
    """
    Проверяем, что в аргументах запроса присутствует хотя бы одна пара полей, необходимая для расчета score
    """
    has_list = list()
    ok = False
    pairs = [('phone', 'email'), ('first_name', 'last_name'), ('gender', 'birthday')]
    for pair in pairs:
        first = arguments.get(pair[0])
        last = arguments.get(pair[-1])
        if first is not None and last is not None:
            ok = True
        for i in pair:
            field = arguments.get(i)
            if field is not None:
                has_list.append(i)
    return {'ok': ok, 'has': has_list}


def online_score_handler(request, ctx, store):
    """
    Обрабатываем запрос 'online_score'
    """
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
    """
    Обрабатываем запрос 'clients_interests'
    """
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
