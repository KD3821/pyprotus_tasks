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


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOG_FILE": "log_analyzer.log"
}


def get_config():
    return config


logging.basicConfig(
        level=logging.ERROR,
        filename=get_config().get('LOG_FILE'),
        filemode='w',
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )


def find_log_file(file_name_pattern, dir_name):
    """
    Поиск в указанной директории файлов с именем, соответствующим шаблону, и их передача в дальнейшую обработку
    """
    with os.scandir(path=dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, file_name_pattern):
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
    report_file_pattern = 'report' + '-' + str(report_date)[:4] + '.' + str(report_date)[4:6] + '.' \
                          + str(report_date)[-2:] + '.html'

    with os.scandir(path=report_dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, report_file_pattern):
                return True


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


def get_url_time(x):
    """
    Вспомогательная функция для сортировки списка словарей по указанному ключу ('time_sum')
    """
    return x.get('time_sum')


def process_lines(line_iterator, file_name, log_dir_name, report_size):
    """
    Основная обработка логов.
    """

    total_count = 0
    total_time = 0.0
    urls_done = []
    urls_data_list = []

    first_time = True

    while True:
        try:
            line = next(line_iterator)
            line_list = line.split()
            line_url = line_list[6]

            if line_url in urls_done:
                continue

            line_count = 0
            line_time_sum = 0.0
            line_time_list = []

            log_iterator = process_logs(file_name, log_dir_name)

            while True:
                try:
                    log = next(log_iterator)
                    log_list = log.split()
                    log_url = log_list[6]
                    log_t = float(log_list[-1])

                    if first_time:
                        total_count += 1
                        total_time += log_t

                    if log_url == line_url:
                        line_count += 1
                        line_time_sum += log_t
                        line_time_list.append(log_t)

                except StopIteration:
                    if first_time:
                        first_time = False
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
                'time_sum': line_time_sum,
                'time_perc': line_time_sum_perc,
                'time_avg': line_time_avg,
                'time_max': line_time_max,
                'time_med': line_time_median
            })

        except StopIteration:
            break

    urls_data_list.sort(reverse=True, key=get_url_time)

    if len(urls_data_list) >= report_size:
        return urls_data_list[0:report_size]

    return urls_data_list


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
                data += f'    var table = {final_data};'
            else:
                data += i

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)


def main():
    actual_conf = get_config()
    gen_log_file = find_log_file("nginx-access-ui.log*", actual_conf.get("LOG_DIR"))
    log_file_name, report_date = get_recent_log_file(gen_log_file)
    if check_report_exist(report_date, actual_conf.get("REPORT_DIR")):
        logging.error('Отчет за указанную дату уже создан.')
        sys.exit()
    gen_lines = process_logs(log_file_name, actual_conf.get("LOG_DIR"))
    urls = process_lines(gen_lines, log_file_name, actual_conf.get("LOG_DIR"), actual_conf.get("REPORT_SIZE"))
    create_report_file(urls, report_date, actual_conf.get("REPORT_DIR"))


if __name__ == "__main__":
    main()
