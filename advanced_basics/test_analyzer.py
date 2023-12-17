import unittest
from typing import Iterable

from log_analyzer import (
    find_log_file,
    get_recent_log_file,
    process_logs,
    process_lines,
    check_report_exist,
)


test_dir_name = 'testing_logs'
test_file_name_pattern = 'nginx-test-access-ui.log*'
test_report_size = 15

correct_log_file_name = 'nginx-test-access-ui.log-20231217'
correct_latest_date = '20231217'
already_exist_report_date = '20231216'

invalid_log_25_perc_file_name = 'nginx-test-access-ui.log-20231216'  # файл содержит 20 логов - 5 из них невалидные


class Testing(unittest.TestCase):
    def test_find_log_file(self):
        """
        Тестируем ф-цию поиска файлов по шаблону имени файла и имени директории, ф-ция должна вернуть генератор файлов
        """
        gen_log_file = find_log_file(
            file_name_pattern=test_file_name_pattern,
            dir_name=test_dir_name
        )
        self.assertIsInstance(gen_log_file, Iterable)

    def test_get_recent_log_file(self):
        """
        Тестируем поиск САМОГО НОВОГО файла по шаблону имени файла и имени директории - возвращает имя файла и дату
        """
        gen_log_file = find_log_file(
            file_name_pattern=test_file_name_pattern,
            dir_name=test_dir_name
        )
        file, date = get_recent_log_file(gen_log_file)
        self.assertEqual(file, correct_log_file_name) and self.assertEqual(date, correct_latest_date)

    def test_process_lines_fail_coeff_error(self):
        """
        Тестируем порог 'валидности' логов на файле, в котором кол-во НЕ валидных логов > запрошенного коэффициента
        """
        gen_lines = process_logs(
            file_name=invalid_log_25_perc_file_name,
            log_dir_name=test_dir_name
        )
        urls = process_lines(
            line_iterator=gen_lines,
            file_name=invalid_log_25_perc_file_name,
            log_dir_name=test_dir_name,
            report_size=test_report_size,
            fail_coefficient=24  # запрашиваемый коэффициент
        )
        self.assertIsInstance(urls, type(None))

    def test_process_lines_fail_coeff_ok(self):
        """
        Тестируем порог 'валидности' логов на файле, в котором кол-во НЕ валидных логов <= запрошенного коэффициента
        """
        gen_lines = process_logs(
            file_name=invalid_log_25_perc_file_name,
            log_dir_name=test_dir_name
        )
        urls = process_lines(
            line_iterator=gen_lines,
            file_name=invalid_log_25_perc_file_name,
            log_dir_name=test_dir_name,
            report_size=test_report_size,
            fail_coefficient=25  # запрашиваемый коэффициент
        )
        self.assertIsInstance(urls, list)

    def test_check_report_exist(self):
        """
        Тестируем функцию, которая проверяет, что файл с анализом логов за указанную дату уже существует в директории
        """
        res = check_report_exist(
            report_date=already_exist_report_date,
            report_dir_name=test_dir_name
        )
        self.assertEqual(res, True)


if __name__ == '__main__':
    unittest.main()
