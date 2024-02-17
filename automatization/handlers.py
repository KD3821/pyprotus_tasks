import os
import logging
import json
from datetime import datetime, timedelta

from routers import get_api_service
from database import DatabaseEngine
from utils import encoded_url_parse


def define_handler(request):
    """ Определяем является ли запрос HTTP-запросом """
    request_data = request.decode().split('\r\n')
    first_line_list = request_data[0].split(' ')
    protocol = first_line_list[-1]
    try:
        if protocol.index('HTTP') != -1 and len(request_data) > 1:  # add more verification
            return HttpRequestHandler
    except ValueError:
        return BaseRequestHandler


class BaseRequestHandler:
    """ Базовый обработчик запросов - отвечает на запросы от TCP-соединений (тест в терминале: nc 127.0.0.1 8080)"""
    def __init__(self, conn: tuple, request: bytes = None, **kwargs):
        self.client_host = conn[0]
        self.client_port = conn[-1]
        self.data = request.decode()

    def response(self):  # response with echo in upper case (just simple example)
        response_data = 'ЭХО: ' + self.data.upper()
        return response_data.encode()


class HttpRequestHandler(BaseRequestHandler):
    """
    ALLOWED_METHODS - разрешенные типы HTTP запросов
    CREATE_UPDATE_METHODS - для методов из этого списка парсит тело HTTP запроса в JSON-формате
    ALLOWED_FILE_FORMATS - словарь разрешенных форматов файлов и соответствующих им значений для заголовков ответа
    Обработчик HTTP запросов - обрабатывает запросы к API, раздает статику, перенаправляет запросы.
    ТипОтвета_FIRST - первая часть заголовков ответа
    ТипОтвета_HEADERS - средняя часть заголовков ответа
    ТипОтвета_BODY - тело ответа
    MOVED_PERMANENTLY - пары для редиректа (откуда-куда)
    """
    ALLOWED_METHODS = {'GET', 'HEAD'}  # for full consuming of API add other methods: 'POST', 'PUT', 'DELETE'
    CREATE_UPDATE_METHODS = {'POST', 'PUT'}
    ALLOWED_FILE_FORMATS = {
        'html': 'text/html',
        'pdf': 'text/pdf',
        'css': 'text/css',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'ico': 'image/x-icon',
        'gif': 'image/gif',
        'js': 'application/javascript',
        'swf': 'application/x-shockwave-flash',
        'txt': 'text/plain'
    }

    OK_REQ_FIRST = 'HTTP/1.1 200 OK'

    REDIRECT_FIRST = 'HTTP/1.1. 301 Moved Permanently'

    DELETE_OK_FIRST = 'HTTP/1.1 204 No Content'

    OK_REQ_HEADERS = {
        'Server': 'denserv/1.18.0 (Subuntu)',
        'Date': datetime.strftime(datetime.utcnow(), "%a, %d %b %Y %H:%M:%S GMT"),
        'Content-Type': 'application/json',
        'Last-Modified': datetime.strftime((datetime.utcnow() - timedelta(days=1)), "%a, %d %b %Y %H:%M:%S GMT"),
        'Connection': 'keep-alive'
    }

    NOT_FOUND_FIRST = 'HTTP/1.1 404 Not Found'
    NOT_FOUND_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Страница не найдена."\n}'

    BAD_PARAM_FIRST = 'HTTP/1.1 403 Forbidden'  # can be 'HTTP/1.1 404 Not Found'
    BAD_PARAM_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Невалидные параметры запроса."\n}'

    BAD_METHOD_FIRST = 'HTTP/1.1 405 Method Not Allowed'
    BAD_METHOD_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Данный метод не разрешен."\n}'

    BAD_REQ_HEADERS = {
        'Server': 'denserv/1.18.0 (Subuntu)',
        'Date': datetime.strftime(datetime.utcnow(), "%a, %d %b %Y %H:%M:%S GMT"),
        'Content-Type': 'application/json',
        'Allow': 'GET, HEAD',
        'Vary': 'Accept, Origin',
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'same-origin',
        'Cross-Origin-Opener-Policy': 'same-origin'
    }

    MOVED_PERMANENTLY = {
        'directory1/directory2/index.html': 'index.html',
        'main/directory1/price.html': 'file 5.html'
    }

    def __init__(self, conn: tuple, db_engine: DatabaseEngine, request: bytes = None, document_root: str = None):
        super().__init__(conn, request)
        self.db_engine = db_engine
        self.document_root = document_root
        self.path_params = dict()
        self.queries = dict()
        self.headers = dict()
        self.document = dict()
        self.body = dict()
        self.extras = dict()
        self.method = ''
        self.protocol = ''

    def parse_request_data(self):
        data = self.data.split('\r\n')

        first_line_list = data.pop(0).split(' ')  # method - path - version of HTTP protocol

        params = first_line_list[1].split('/')  # parsing path
        if params[0] == '':
            params.pop(0)

        last = params.pop(-1)  # get 'index.html?search=black'

        for i, path in enumerate(params):  # path without last
            if path != '':
                self.path_params.update({i: path})

        if last.find('%') != -1:  # if url encoding present
            last = encoded_url_parse(last)

        if last.find('.') != -1:   # file.extension
            file = last
            dots = file.count('.')  # if few dots
            if dots > 1:
                reversed_last = file[::-1]
                rev_dot_index = reversed_last.find('.')
                f_ext = file[-rev_dot_index:]
            else:
                f_list = file.split('.')
                f_ext = f_list[-1]

            if f_ext.find('?') != -1:  # if query present
                ext_list = f_ext.split('?')
                f_ext = ext_list[0]
                file_list = file.split('?')
                file = file_list[0]

            if f_ext in self.ALLOWED_FILE_FORMATS.keys():
                param_str = ''
                for param in self.path_params.values():
                    param_str += f'{param}/'
                param_str += file
                self.document = {
                    'Content-Type': self.ALLOWED_FILE_FORMATS.get(f_ext),
                    'path': os.path.join(self.document_root, param_str),
                    'Accept-Ranges': 'bytes'
                }

        if last.find('?') != -1:  # query param
            last_list = last.split('?')
            last = last_list[0]
            query = last_list[-1]
            query_list = query.split('&')
            for pair in query_list:
                pair_list = pair.split('=')
                if len(pair_list) > 1:
                    k, v = pair_list
                    self.queries.update({k: v})

        if last != '':
            self.path_params.update({len(self.path_params): last})

        self.method = first_line_list[0]     # parsing method
        self.protocol = first_line_list[-1]  # parsing protocol

        body = data.pop(-1)  # parsing body
        if body != '':
            if self.method in self.CREATE_UPDATE_METHODS:  # for json request body (for API)
                try:
                    self.body = json.loads(body)
                except json.decoder.JSONDecodeError:
                    pass
            else:
                sep_index = body.find(':')  # can be Cookie
                name = body[:sep_index].strip()
                value = body[sep_index + 1:].strip()
                self.body.update({name: value})

        extras = data.pop(-1)  # can be Accept-Language
        if extras != '':
            try:
                self.extras = json.loads(extras)
            except json.decoder.JSONDecodeError:
                sep_index = extras.find(':')
                name = extras[:sep_index].strip()
                value = extras[sep_index + 1:].strip()
                self.extras.update({name: value})

        for line in data:  # parsing what's left - can be Accept-Encoding
            sep_index = line.find(':')
            name = line[:sep_index].strip()
            value = line[sep_index + 1:].strip()
            self.headers.update({name: value})

        logging.info(
            f"Данные запроса от ('{self.client_host}', {self.client_port}):\n"
            f"path: {self.path_params}\n"
            f"queries: {self.queries}\n"
            f"method: {self.method}\n"
            f"protocol: {self.protocol}\n"
            f"body: {self.body}\n"
            f"extras: {self.extras}\n"
            f"headers: {self.headers}\n"
            f"file: {self.document}"
        )

    def bad_response(self, first, body):
        bad_req_str = ''
        for key, value in self.BAD_REQ_HEADERS.items():
            bad_req_str += f"{key}: {value}\r\n"
        return f"{first}\r\n{bad_req_str}\r\n\n{body}".encode()

    def check_method_allowed(self):
        if self.method in self.ALLOWED_METHODS:
            return True
        return False

    def proxy_to_backend(self):
        api_service_handler = get_api_service(
            path_params=self.path_params,
            method=self.method,
            data=self.body,
            db=self.db_engine
        )

        if api_service_handler is None:
            return self.bad_response(self.BAD_PARAM_FIRST, self.BAD_PARAM_BODY)

        data = api_service_handler.response()

        if data.get('error'):
            if data.get('method') is not None:
                return self.bad_response(self.BAD_METHOD_FIRST, self.BAD_METHOD_BODY)
            return self.bad_response(self.NOT_FOUND_FIRST, self.NOT_FOUND_BODY)

        if data.get('deleted'):
            db_req_str = ''
            for key, value in self.OK_REQ_HEADERS.items():
                db_req_str += f"{key}: {value}\r\n"
            return f"{self.DELETE_OK_FIRST}\r\n{db_req_str}\r\n".encode()

        if data.get('json'):
            db_req_body = json.dumps(data.get('data'))
            db_req_str = ''
            for key, value in self.OK_REQ_HEADERS.items():
                db_req_str += f"{key}: {value}\r\n"
            return f"{self.OK_REQ_FIRST}\r\n{db_req_str}\r\n\n{db_req_body}".encode()

        else:
            db_req_body = '{'
            for key, value in data.items():
                db_req_body += f'\n"{key}": "{value}",'
            db_req_body = db_req_body.rstrip(',') + '\n}'
            db_req_str = ''
            for key, value in self.OK_REQ_HEADERS.items():
                db_req_str += f"{key}: {value}\r\n"
            return f"{self.OK_REQ_FIRST}\r\n{db_req_str}\r\n\n{db_req_body}".encode()

    def response_file(self, file_path):
        ok_req_str = ''
        for key, value in self.OK_REQ_HEADERS.items():
            if key in self.document.keys():
                continue
            ok_req_str += f"{key}: {value}\r\n"
        for k, v in self.document.items():
            ok_req_str += f"{k}: {v}\r\n"
        try:
            with open(f"{file_path}", "rb") as img_file:
                img_bytes = img_file.read()
                ok_req_str += f"Content-Length: {len(img_bytes)}\r\n"

                if self.body and self.method != 'HEAD':
                    for k, v in self.body.items():
                        ok_req_str += f"{k}: {v}\r\n"

                if self.extras and self.method != 'HEAD':
                    for k, v in self.extras.items():
                        ok_req_str += f"{k}: {v}\r\n"

            image_response = f"{self.OK_REQ_FIRST}\r\n{ok_req_str}\r\n".encode()

            if self.method != 'HEAD':
                image_response += img_bytes

            return image_response

        except FileNotFoundError:
            return self.bad_response(self.NOT_FOUND_FIRST, self.NOT_FOUND_BODY)

    def redirect(self, path):
        redirect_str = ''
        for key, value in self.OK_REQ_HEADERS.items():
            redirect_str += f"{key}: {value}\r\n"
        redirect_str += f"Location: /{path}"
        return f"{self.REDIRECT_FIRST}\r\n{redirect_str}\r\n".encode()

    def response(self):
        self.parse_request_data()

        if not self.check_method_allowed():
            return self.bad_response(self.BAD_METHOD_FIRST, self.BAD_METHOD_BODY)

        if self.path_params.get(0) == 'api':
            return self.proxy_to_backend()

        dir_str = ''
        for directory in self.path_params.values():  # concat path_params
            dir_str += f'{directory}/'

        for moved_from, moved_to in self.MOVED_PERMANENTLY.items():  # added for 301 redirect for moved files
            sub_str = dir_str.find(moved_from)  # check if path need redirect
            if sub_str != -1:
                return self.redirect(moved_to)

        if self.document:  # if document was defined while parsing 'last'
            doc_path = self.document.get('path')
            return self.response_file(doc_path)

        if dir_str != '' and os.path.exists(f'{self.document_root}/{dir_str}'):  # then try default folder 'index.html'
            dir_str += 'index.html'
            self.document = {
                'Content-Type': 'text/html',
                'path': os.path.join(self.document_root, dir_str),
                'Accept-Ranges': 'bytes'
            }
            return self.response_file(self.document.get('path'))

        return self.bad_response(self.NOT_FOUND_FIRST, self.NOT_FOUND_BODY)  # otherwise Not Found response
