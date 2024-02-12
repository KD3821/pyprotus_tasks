import os
import logging
from datetime import datetime, timedelta
import json

from routers import get_api_service
from database import DatabaseEngine


def confirm_http_protocol(request):
    request_data = request.decode().split('\r\n')
    first_line_list = request_data[0].split(' ')
    protocol = first_line_list[-1]
    try:
        if protocol.index('HTTP') != -1 and len(request_data) > 1:  # add more verification
            return True
    except ValueError:
        return False


def define_handler(request):
    if confirm_http_protocol(request):
        return HttpRequestHandler
    return BaseRequestHandler


class BaseRequestHandler:
    def __init__(self, conn: tuple, db_engine: DatabaseEngine, request: bytes = None, document_root: str = None):
        self.client_host = conn[0]
        self.client_port = conn[-1]
        self.data = request.decode()
        self.db_engine = db_engine
        self.document_root = document_root

    def response(self):
        response_data = 'ЭХО: ' + self.data.upper()
        return response_data.encode()


class HttpRequestHandler(BaseRequestHandler):
    ALLOWED_METHODS = {'GET', 'HEAD', 'PUT', 'DELETE', 'POST'}  # can add more methods
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
        'swf': 'application/x-shockwave-flash'
    }
    HEADER_FIELDS = {
        'Host',
        'Content-Type',
        'Authorization',
        'User-Agent',
        'Accept',
        'Host',
        'Accept-Encoding',
        'Connection',
        'Content-Length',
        'Cookie'
    }

    OK_REQ_FIRST = 'HTTP/1.1 200 OK'

    OK_REQ_HEADERS = {
        'Server': 'denserv/1.18.0 (Subuntu)',
        'Date': datetime.strftime(datetime.utcnow(), "%H:%m:%s, %d/%m/%Y GMT"),
        'Content-Type': 'application/json',
        'Last-Modified': datetime.strftime((datetime.utcnow() - timedelta(days=1)), "%H:%m:%s, %d/%m/%Y GMT"),
        'Connection': 'keep-alive'
    }

    NOT_FOUND_FIRST = 'HTTP/1.1 404 Not Found'
    NOT_FOUND_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Отсутствуют данные для пользователя."\n}'

    BAD_PARAM_FIRST = 'HTTP/1.1 404 Not Found'
    BAD_PARAM_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Невалидные параметры запроса."\n}'

    BAD_METHOD_FIRST = 'HTTP/1.1 405 Method Not Allowed'
    BAD_METHOD_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Данный метод не разрешен."\n}'

    BAD_REQ_HEADERS = {
        'Server': 'denserv/1.18.0 (Subuntu)',
        'Date': datetime.strftime(datetime.utcnow(), "%H:%m:%s, %d/%m/%Y GMT"),
        'Content-Type': 'application/json',
        'Allow': 'GET, HEAD',
        'Vary': 'Accept, Origin',
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'same-origin',
        'Cross-Origin-Opener-Policy': 'same-origin'
    }

    DELETE_OK_FIRST = 'HTTP/1.1 204 No Content'

    def __init__(self, conn: tuple, db_engine: DatabaseEngine, request: bytes = None, document_root: str = None):
        super().__init__(conn, db_engine, request, document_root)
        self.path_params = dict()
        self.queries = dict()
        self.headers = dict()
        self.document = dict()
        self.body = dict()
        self.extras = dict()

        data = request.decode().split('\r\n')
        first_line_list = data.pop(0).split(' ')  # method - path - version of HTTP protocol

        params = first_line_list[1].split('/')  # parsing path
        if params[0] == '':
            params.pop(0)
        last = params.pop(-1)
        for i, path in enumerate(params):
            if path != '':
                self.path_params.update({i: path})
        if last.find('.') != -1:   # file.extension
            last_list = last.split('.')
            if last_list[-1] in self.ALLOWED_FILE_FORMATS.keys():
                self.document = {
                    'Content-Type': self.ALLOWED_FILE_FORMATS.get(last_list[-1]),
                    'path': os.path.join(self.document_root, last),
                    'Accept-Ranges': 'bytes'
                }
        elif last.find('?') != -1:  # query param
            last_list = last.split('?')
            last = last_list[0]
            query = last_list[-1]
            query_list = query.split('&')
            for pair in query_list:
                pair_list = pair.split('=')
                if len(pair_list) > 1:
                    k, v = pair_list
                    self.queries.update({k: v})
        self.path_params.update({len(self.path_params): last})

        self.method = first_line_list[0]     # parsing method
        self.protocol = first_line_list[-1]  # parsing protocol
        body = data.pop(-1)                  # parsing body
        if body != '':
            if self.method in self.CREATE_UPDATE_METHODS:  # for json request body
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

        for line in data:  # parsing Accept-Encoding
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

    def pass_to_backend(self):
        if self.path_params.get(0) == 'api':
            return True
        return False

    def response(self):
        if not self.check_method_allowed():
            return self.bad_response(self.BAD_METHOD_FIRST, self.BAD_METHOD_BODY)

        if self.pass_to_backend():
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

        if self.document:
            ok_req_str = ''
            for key, value in self.OK_REQ_HEADERS.items():
                if key in self.document.keys():
                    continue
                ok_req_str += f"{key}: {value}\r\n"
            for k, v in self.document.items():
                ok_req_str += f"{k}: {v}\r\n"

            try:
                with open(f"{self.document.get('path')}", "rb") as img_file:
                    img_bytes = img_file.read()
                    ok_req_str += f"Content-Length: {len(img_bytes)}\r\n"

                    if self.body:
                        for k, v in self.body.items():
                            if k == 'Cookie':  # if cookie was sent in request then add our cookies (just for practice)
                                timestamp = datetime.timestamp(datetime.utcnow())
                                ok_req_str += f"Set-Cookie: user=CoolUser-{timestamp}\r\n"
                                ok_req_str += "Access-Control-Expose-Headers: Set-Cookie\r\n"
                                continue
                            ok_req_str += f"{k}: {v}\r\n"

                    if self.extras:
                        for k, v in self.extras.items():
                            ok_req_str += f"{k}: {v}\r\n"

                image_response = f"{self.OK_REQ_FIRST}\r\n{ok_req_str}\n".encode()
                image_response += img_bytes
                return image_response

            except FileNotFoundError:
                return self.bad_response(self.NOT_FOUND_FIRST, self.NOT_FOUND_BODY)

        return self.bad_response(self.BAD_PARAM_FIRST, self.BAD_PARAM_BODY)
