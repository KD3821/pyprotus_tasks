import socket
import os
import sys
import logging

from utils import get_config
from handlers import define_handler


class CustomServer:

    def __init__(self, host='', port=8080, workers=4, document_root=None):
        self.host = host
        self.port = port
        self.workers = workers
        self.document_root = document_root

    def serve_forever(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.workers)

        for i in range(self.workers):
            child_pid = os.fork()

            if child_pid == 0:
                worker_pid = os.getpid()
                logging.info(f'Запуск worker процесса [pid: {worker_pid}].')
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
                        self.finish_request(conn=connection, worker_pid=worker_pid)
                        client_socket.close()
                except KeyboardInterrupt:
                    sys.exit()

    def process_request(self, conn, request, worker_pid):
        handler_class = define_handler(request=request)
        handler = handler_class(conn=conn, request=request, document_root=self.document_root)
        response_data = handler.response()
        logging.info(f"[worker {worker_pid}] ответ для соединения ('{handler.client_host}', {handler.client_port}): "
                     f"{response_data[:100]}")
        return response_data

    @staticmethod
    def finish_request(conn, worker_pid):
        logging.info(f'[worker {worker_pid}] Закрываем соединение {conn}')


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
        document_root=config.get('DOCUMENT_ROOT')
    )
    try:
        server.serve_forever()
        try:
            os.waitpid(-1, 0)
        except KeyboardInterrupt:
            logging.info(f"Остановка работы сервера: {config.get('HOST')}:{config.get('PORT')}")
            sys.exit()
    except socket.error as e:
        logging.error(f"Ошибка запуска сервера: {e}")
        sys.exit()
