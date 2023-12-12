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


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def get_config():
    return config


def find_log_file(file_name_pattern, dir_name):
    with os.scandir(path=dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, file_name_pattern):
                yield entry


def find_latest_date(log_file, recent_date):
    file_date = int(log_file.name.split('.')[1].split('-')[-1])

    if recent_date is None:
        return file_date, log_file.name

    elif recent_date < file_date:
        return file_date, log_file.name

    return recent_date, None


def get_recent_log_file(file_iterator):
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
    report_file_pattern = 'report' + '-' + str(report_date)[:4] + '.' + str(report_date)[4:6] + '.' \
                          + str(report_date)[-2:] + '.html'

    with os.scandir(path=report_dir_name) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, report_file_pattern):
                return True


def process_logs(file_name, log_dir_name):
    if file_name.endswith(".gz"):
        log = gzip.open(os.path.join(log_dir_name, file_name), 'rt')
    else:
        log = open(os.path.join(log_dir_name, file_name), 'r')

    for line in log:
        yield line

    log.close()


def process_lines(line_iterator):

    total_count = 0
    total_time = 0.0
    urls_data = {}

    while True:
        try:
            line = next(line_iterator)
            log_list = line.split()
            url = log_list[6]
            t = float(log_list[-1])
            total_count += 1
            total_time += t
            first_time = True
            for key, value in urls_data.items():
                if key == url:
                    value['count'] = value.get('count') + 1
                    value['time'] = value.get('time') + t
                    value['med'].append(t)
                    if t > value.get('max'):
                        value['max'] = t
                    first_time = False
                    break
            if first_time:
                urls_data[url] = dict(count=1, time=t, max=t, med=[t])

        except StopIteration:
            break
    return urls_data, total_count, total_time


def finalize_report(urls_data, total_count, total_time, report_size):
    final_data = []

    for key, value in urls_data.items():   # TODO use report_size to take first 1000 with max time_sum:
        tmp = value.get('med')

        if len(tmp) % 2 != 0:
            med = len(tmp) // 2
            time_med = tmp[med]
        else:
            med_1 = len(tmp) // 2
            med_0 = med_1 - 1
            time_med = (tmp[med_0] + tmp[med_1]) / 2

        log_stat = dict(
            url=key,
            count=value.get('count'),
            time_avg=value.get('time') / value.get('count'),
            time_max=value.get('max'),
            time_sum=value.get('time'),
            time_med=time_med,
            time_perc=(value.get('time') / total_time) * 100,
            count_perc=(value.get('count') / total_count) * 100
        )

        final_data.append(log_stat)
    return final_data


def create_report_file(final_data, file_date, dir_path):

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

        with open(file_path, 'w') as f:
            f.write(data)


def main():
    actual_conf = get_config()
    gen_log_file = find_log_file("nginx-access-ui.log*", actual_conf.get("LOG_DIR"))
    log_file_name, report_date = get_recent_log_file(gen_log_file)
    if check_report_exist(report_date, actual_conf.get("REPORT_DIR")):
        sys.exit()
    gen_lines = process_logs(log_file_name, actual_conf.get("LOG_DIR"))
    data, count, time = process_lines(gen_lines)
    final = finalize_report(data, count, time, actual_conf.get("REPORT_SIZE"))
    create_report_file(final, report_date, actual_conf.get("REPORT_DIR"))


if __name__ == "__main__":
    main()
