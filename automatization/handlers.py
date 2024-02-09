import os
import logging
from datetime import datetime, timedelta


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
    def __init__(self, conn: tuple, request: bytes = None, document_root: str = None):
        self.client_host = conn[0]
        self.client_port = conn[-1]
        self.data = request.decode()
        self.document_root = document_root

    def response(self):
        response_data = 'ЭХО: ' + self.data.upper()
        return response_data.encode()


class HttpRequestHandler(BaseRequestHandler):
    ALLOWED_METHODS = {'GET', 'HEAD'}
    ALLOWED_FILE_FORMATS = {
        'html': 'text/html',
        'pdf': 'text/pdf',
        'css': 'text/css',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'ico': 'image/x-icon'
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
    BAD_REQ_FIRST = 'HTTP/1.1 405 Method Not Allowed'
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
    BAD_REQ_BODY = '{\n"result": "ОШИБКА ЗАПРОСА",\n"message": "Разрешены только HTTP запросы: GET и HEAD."\n}'

    def __init__(self, conn: tuple, request: bytes = None, document_root: str = None):
        super().__init__(conn, request, document_root)
        self.data = request.decode()
        self.path_params = dict()
        self.queries = dict()
        self.headers = dict()
        self.document = dict()

        data = request.decode().split('\r\n')
        first_line_list = data.pop(0).split(' ')

        params = first_line_list[1].split('/')
        last = params.pop(-1)
        for i, path in enumerate(params):
            if path != '':
                self.path_params.update({i: path})
        if last.find('.') != -1:
            last_list = last.split('.')
            if last_list[-1] in self.ALLOWED_FILE_FORMATS.keys():
                self.document = {
                    'Content-Type': self.ALLOWED_FILE_FORMATS.get(last_list[-1]),
                    'path': os.path.join(self.document_root, last),
                    'Accept-Ranges': 'bytes'
                }
        elif last.find('?') != -1:
            last_list = last.split('?')
            last = last_list[0]
            query = last_list[-1]
            query_list = query.split('&')
            if len(query_list) > 1:
                for pair in query_list:
                    pair_list = pair.split('=')
                    if len(pair_list) > 1:
                        k, v = pair_list
                        self.queries.update({k: v})
        self.path_params.update({len(self.path_params): last})

        self.method = first_line_list[0]
        self.protocol = first_line_list[-1]
        self.body = data.pop(-1)
        self.extras = data.pop(-1)

        for line in data:
            sep_index = line.find(':')
            name = line[:sep_index].strip()
            value = line[sep_index + 1:].strip()
            if name == "Accept-Encoding":
                value = value.split(', ')
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

    def check_method_allowed(self):
        if self.method in self.ALLOWED_METHODS:
            return True
        return False

    def response(self):
        if not self.check_method_allowed():
            bad_req_str = ''
            for key, value in self.BAD_REQ_HEADERS.items():
                bad_req_str += f"{key}: {value}\r\n"
            return f"{self.BAD_REQ_FIRST}\r\n{bad_req_str}\r\n\n{self.BAD_REQ_BODY}".encode()

        if self.document:
            ok_req_str = ''
            for key, value in self.OK_REQ_HEADERS.items():
                if key in self.document.keys():
                    continue
                ok_req_str += f"{key}: {value}\r\n"
            for k, v in self.document.items():
                ok_req_str += f"{k}: {v}\r\n"

            with open(f"{self.document.get('path')}", "rb") as img_file:
                img_bytes = img_file.read()
                ok_req_str += f"Content-Length: {len(img_bytes)}\r\n"

            image_response = f"{self.OK_REQ_FIRST}\r\n{ok_req_str}\n".encode()
            image_response += img_bytes
            return image_response
