import socket
import os
import sys
import logging

from utils import get_config
from database import DatabaseEngine
from handlers import define_handler


class CustomServer:

    def __init__(self, host='', port=8080, workers=4, document_root=None, db_name='example.db'):
        self.host = host
        self.port = port
        self.workers = workers
        self.document_root = document_root
        self.db_engine = DatabaseEngine(db_name)
        self.sock = None

    def serve_forever(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.workers)
        self.sock = server_socket

        for i in range(self.workers):
            child_pid = os.fork()

            if child_pid == 0:
                worker_pid = os.getpid()
                logging.info(f'[worker {worker_pid}] запуск процесса ')
                try:
                    while True:
                        client_socket, addr = server_socket.accept()
                        request = client_socket.recv(1024)
                        connection = client_socket.getpeername()
                        logging.info(f'[worker {worker_pid}] новое соединение {connection}')  # no need?
                        response = self.process_request(
                            conn=connection,
                            request=request,
                            worker_pid=worker_pid
                        )
                        client_socket.send(response)
                        logging.info(f'[worker {worker_pid}] закрываем соединение {connection}\n')
                        client_socket.close()
                except KeyboardInterrupt:
                    logging.info(f"[worker {worker_pid}] остановка процесса")
                    sys.exit()

    def process_request(self, conn, request, worker_pid):
        handler_class = define_handler(request=request)
        handler = handler_class(
            conn=conn,
            request=request,
            document_root=self.document_root,
            db_engine=self.db_engine
        )
        response_data = handler.response()
        if response_data is None:
            response_data = b'Error: page not found'
        logging.info(f"[worker {worker_pid}] ответ для соединения ('{handler.client_host}', {handler.client_port}): "
                     f"{response_data[:100]}")
        return response_data

    def stop_serving(self):
        self.sock.close()


if __name__ == "__main__":
    config = get_config()
    config_msg = dict()
    if err := config.get('failure'):
        config_msg.update({1: f"{err} - применены настройки по-умолчанию."})
        config = config.get('default')
    config_msg.update(
        {0: f"Запуск сервера: {config.get('HOST')}:{config.get('PORT')} workers:{config.get('WORKER_PROCESSES')}"}
    )
    logging.basicConfig(
        filename=config.get('ACCESS_LOG_FILE'),
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )
    for error, msg in config_msg.items():
        logging.error(msg) if error else logging.info(msg)
    server = CustomServer(
        host=config.get('HOST'),
        port=config.get('PORT'),
        workers=config.get('WORKER_PROCESSES'),
        document_root=config.get('DOCUMENT_ROOT'),
        db_name='backend.db'
    )
    try:
        server.serve_forever()
        try:
            os.waitpid(-1, 0)
        except KeyboardInterrupt:
            logging.info(f"Остановка работы сервера: {config.get('HOST')}:{config.get('PORT')}\n")
            server.stop_serving()
            sys.exit()
    except socket.error as e:
        logging.error(f"Ошибка запуска сервера: {e}")
        sys.exit()


"""
Варианты команд запуска сервера из консоли:
python3 httpd.py -config server_config.json
python3 httpd.py -w 10
python3 httpd.py -w 10 -r /home/dk/PycharmProjects/pyprotus/automatization/documents
###
Завершить процессы из консоли:
pkill -f 'python3 httpd.py -w 10 -r /home/dk/PycharmProjects/pyprotus/automatization/documents'
###
Load benchmark with 'wrk' tool:
docker pull williamyeh/wrk
docker run --network="host" --rm williamyeh/wrk -t12 -c400 -d30s http://127.0.0.1:8080/index.html
"""