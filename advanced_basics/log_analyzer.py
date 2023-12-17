#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import os
import fnmatch
import gzip
import re
import sys
from statistics import median
import logging
import argparse
import json


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def get_config():
    """
    Считываем (или используем встроенный) конфиг
    """
    parser = argparse.ArgumentParser(description='Чтение настроек из файла конфигурации (--config=*.json)')
    parser.add_argument("--config", required=False, type=str)
    config_file = parser.parse_args()

    if config_file.config:
        config_file_name = config_file.config

        try:
            data = json.load(open(config_file_name))  # Считываем данные конфигурации из файла 'config.json'

            config_data = config

            for key, value in data.items():
                config_data[key] = value

            return config_data

        except FileNotFoundError:
            return {'failure': 'Файл конфигурации указан, но не найден.'}

        except json.decoder.JSONDecodeError:
            return config

    return config


def setup_logging(configuration, logging_level='info'):
    """
    Задаем настройки логирования работы скрипта, по-умолчанию используем уровень 'INFO'
    """
    param_set = {'info', 'error'}

    param_data = {
        'error': logging.ERROR,
        'info': logging.INFO
    }

    if logging_level not in param_set:
        logging_level = 'info'

    param_dict = dict(
        level=param_data.get(logging_level),
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )

    if configuration.get('LOG_FILE'):
        out_dict = dict(filename=configuration.get('LOG_FILE'), filemode='a')
    else:
        out_dict = dict(stream=sys.stdout)

    param_dict.update(out_dict)

    logging.basicConfig(**param_dict)


def find_log_file(file_name_pattern, dir_name):
    """
    Поиск в указанной директории файлов с именем, соответствующим шаблону, и их передача в дальнейшую обработку
    """
    with os.scandir(path=dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, file_name_pattern):  # noqa
                yield entry


def find_latest_date(log_file, recent_date):
    """
    Сравнение даты файла с самой поздней датой ранее проверенного файла. Если дата текущего файла новее, возвращается
    его дата и имя, чтобы далее проводить сравнение данных остальных файлов с ними
    """
    file_date = int(log_file.name.split('.')[1].split('-')[-1])

    if recent_date is None:
        return file_date, log_file.name

    elif recent_date < file_date:
        return file_date, log_file.name

    return recent_date, None


def get_recent_log_file(file_iterator):
    """
    Определяем файл с наиболее новой датой
    """
    recent_date = None
    file_name = None
    while True:
        try:
            f = next(file_iterator)
            recent_date, recent_file_name = find_latest_date(f, recent_date)

            if recent_file_name:
                file_name = recent_file_name

        except StopIteration:
            break

    return file_name, recent_date


def check_report_exist(report_date, report_dir_name):
    """
    Проверяем наличие ранее созданного отчета по файлу с самой новой датой. Если в наличии - останавливаем обработку
    """
    if not os.path.exists(report_dir_name):
        return False

    report_file_pattern = 'report' + '-' + str(report_date)[:4] + '.' + str(report_date)[4:6] + '.' \
                          + str(report_date)[-2:] + '.html'

    with os.scandir(path=report_dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, report_file_pattern):  # noqa
                return True

    return False


def process_logs(file_name, log_dir_name):
    """
    Открываем файл и передаем в дальнейшую обработку построчно
    """
    if file_name.endswith(".gz"):
        log = gzip.open(os.path.join(log_dir_name, file_name), 'rt')
    else:
        log = open(os.path.join(log_dir_name, file_name), 'r')

    for line in log:
        yield line

    log.close()


def validate_log(log):
    """
    Валидация формата логирования - проверяем: url содержит '/', код ответа 'is_numeric', время приводится к типу float
    """
    try:
        if not log[8].isnumeric():
            return False
        if log[6].index('/') == -1:
            return False
    except ValueError:
        return False

    try:
        float(log[-1])
        return True
    except ValueError:
        return False


def get_url_time(x):
    """
    Вспомогательная функция для сортировки списка словарей по указанному ключу ('time_sum')
    """
    return x.get('time_sum')


def time_it(func):
    import time
    def wrapper(*args, **kwargs):  # noqa
        t = time.time()
        res = func(*args, **kwargs)
        logging.info(f"Время выполнения анализа: {round(time.time() - t, 3)} секунд.")
        return res
    return wrapper


@time_it
def process_lines(line_iterator, file_name, log_dir_name, report_size, fail_coefficient=20):
    """
    Основная обработка логов.
    """
    try:
        total_count = 0
        total_time = 0.0
        urls_done = []
        urls_data_list = []
        invalid_count = 0

        first_time = True
        logs_validated = True

        while True:
            if not logs_validated:
                break
            try:
                line = next(line_iterator)
                line_list = line.split()

                if not validate_log(line_list):
                    continue

                line_url = line_list[6]

                if line_url in urls_done:
                    continue

                line_count = 0
                line_time_sum = 0.0
                line_time_list = []

                log_iterator = process_logs(file_name, log_dir_name)  # noqa

                while True:
                    try:
                        log = next(log_iterator)
                        log_list = log.split()

                        log_is_valid = validate_log(log_list)

                        if log_is_valid:
                            log_url = log_list[6]
                            log_t = float(log_list[-1])

                            if log_url == line_url:
                                line_count += 1
                                line_time_sum += log_t
                                line_time_list.append(log_t)

                        if first_time:
                            total_count += 1
                            if log_is_valid:
                                total_time += log_t  # noqa
                            else:
                                invalid_count += 1

                    except StopIteration:
                        if first_time:
                            first_time = False
                            logging.info(f"Всего логов, включая невалидные: {total_count} шт.")

                            validity_perc = invalid_count / total_count * 100
                            logging.info(f"Невалидные логи: {validity_perc:.2f} % (допустимо: {fail_coefficient} %).")

                            if validity_perc > fail_coefficient:  # Проверяем превышение порога валидности логов
                                logs_validated = False
                                logging.info(f"Превышен порог погрешности ({fail_coefficient} %).")
                        break

                line_count_perc = line_count / total_count * 100
                line_time_sum_perc = line_time_sum / total_time * 100
                line_time_avg = line_time_sum / line_count
                line_time_max = max(line_time_list)
                line_time_median = median(line_time_list)

                urls_done.append(line_url)

                urls_data_list.append({
                    'url': line_url,
                    'count': line_count,
                    'count_perc': line_count_perc,
                    'time_sum': round(line_time_sum, 3),
                    'time_perc': round(line_time_sum_perc, 3),
                    'time_avg': round(line_time_avg, 3),
                    'time_max': line_time_max,
                    'time_med': round(line_time_median, 3)
                })

            except StopIteration:
                break

        if not logs_validated:
            return None

        urls_data_list.sort(reverse=True, key=get_url_time)

        if len(urls_data_list) >= report_size:
            return urls_data_list[0:report_size]

        return urls_data_list

    except KeyboardInterrupt:
        logging.exception(msg="Обработка логов остановлена.")
        return {'failure': 'Принудительная остановка.'}

    except Exception as e:
        logging.exception(msg=f"Обработка логов прервана.", exc_info=True)
        return {'failure': f'{e}'}


def create_report_file(final_data, file_date, dir_path):
    """
    Создаем файл и записываем текст шаблона + обработанные данные логов
    """

    report_file_name = 'report' + '-' + str(file_date)[:4] + '.' + str(file_date)[4:6] + '.' + str(file_date)[-2:] \
                       + '.html'

    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    file_path = os.path.join(dir_path, report_file_name)

    report_template_path = './report.html'

    data = ''

    with open(report_template_path, 'r', encoding='utf-8') as html_file:
        tmp = html_file.readlines()

        for i in tmp:
            x = re.search(r'\$table_json', i)
            if x:
                data += f'    var table = {final_data};\n'
            else:
                data += i

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)


def main():
    actual_conf = get_config()

    if actual_conf.get('failure'):
        logging.error(f"{actual_conf.get('failure')}")
        sys.exit()

    setup_logging(actual_conf, logging_level='info')

    gen_log_files = find_log_file("nginx-access-ui.log*", actual_conf.get("LOG_DIR"))

    log_file_name, report_date = get_recent_log_file(gen_log_files)

    if check_report_exist(report_date, actual_conf.get("REPORT_DIR")):
        logging.error('Отчет за указанную дату уже создан.')
        sys.exit()

    gen_lines = process_logs(log_file_name, actual_conf.get("LOG_DIR"))

    urls = process_lines(
        gen_lines,
        log_file_name,
        actual_conf.get("LOG_DIR"),
        actual_conf.get("REPORT_SIZE"),
        fail_coefficient=50  # Установить порог валидности логов в %
    )

    if not isinstance(urls, list):
        if not urls:
            logging.error("Обработка логов невозможна. Проверьте формат логирования.")
        else:
            logging.error(f"Причина: {urls.get('failure')}")
        sys.exit()

    create_report_file(urls, report_date, actual_conf.get("REPORT_DIR"))


if __name__ == "__main__":
    main()
