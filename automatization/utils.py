import argparse
import json


config = {
    "USER": "www-data",
    "HOST": "127.0.0.1",
    "PORT": 8080,
    "WORKER_PROCESSES": 2,
    "ACCESS_LOG_FILE": "./logs/access.log"
}


def get_config():
    """ считывает (или использует встроенный) конфиг """
    parser = argparse.ArgumentParser(description='Чтение настроек из файла конфигурации (--config=*.json)')
    parser.add_argument("-config", required=False, type=str)
    parser.add_argument("-w", required=False, type=str)
    parser.add_argument("-r", required=False, type=str)

    opts = parser.parse_args()

    if opts.w:
        config.update({"WORKER_PROCESSES": int(opts.w)})

    if opts.r:
        config.update({"DOCUMENT_ROOT": opts.r})

    if opts.config:
        config_file_name = opts.config

        try:
            data = json.load(open(config_file_name))  # Считываем данные конфигурации из файла 'server_config.json'

            config_data = config

            for key, value in data.items():
                if key == "WORKER_PROCESSES" and opts.w:
                    continue
                config_data[key] = value

            return config_data

        except FileNotFoundError:
            return {'failure': 'Файл конфигурации указан, но не найден.', 'default': config}

        except json.decoder.JSONDecodeError:
            return config

    return config


def encoded_url_parse(url):  # Thanks to: 'https://stackoverflow.com/questions/16566069/url-decode-utf-8-in-python'
    """ парсит URL encoded путь запроса и возвращает декодированную строку """
    l = len(url)
    data = bytearray()
    i = 0
    while i < l:
        if url[i] != '%':
            d = ord(url[i])
            i += 1
        else:
            d = int(url[i + 1:i + 3], 16)
            i += 3
        data.append(d)
    return data.decode('utf8')
