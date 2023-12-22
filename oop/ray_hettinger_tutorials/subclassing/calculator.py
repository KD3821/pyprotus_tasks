class Operation:
    def __init__(self, base: bytes = 0, arg: bytes = 0):
        self.base = float(base)
        self.arg = float(arg)
        self.__base = base
        self.__arg = arg

    def ops(self, operation):
        try:
            func = getattr(self, 'do_' + operation)
            if operation == 'divide':
                return func(self.arg)
            return func()
        except AttributeError:
            return self.default()

    def check_float(self):
        if (
                self.__base.decode('utf-8').find('.') != -1
                or self.__arg.decode('utf-8').find('.') != -1
        ):
            base = round(self.base)
            power = round(self.arg)
            print(f"Округление до целых чисел в возведение в степень {base} ** {power}:")
            return base ** power

    def default(self):
        res = self.do_multiply(default_arg=3.3)
        print(f"Неверная команда.\nВызвана команда по-умолчанию: умножение чисел (все 0 заменятся на 3.3) - результат:")
        return res

    def do_add(self):
        return self.base + self.arg

    def do_subtract(self):
        return self.base - self.arg

    def do_multiply(self, default_arg=None):
        if default_arg:
            if self.base == 0.0 and self.arg != 0.0:
                return self.arg * default_arg
            if self.arg == 0.0 and self.base != 0.0:
                return self.base * default_arg
            else:
                return 0.0
        return self.base * self.arg

    def do_zero_divide(self):
        print(f"Вызов команды 'divide' со вторым аргументом равным {self.__arg.decode('utf-8')} невозможен.")
        return 'Деление на 0 запрещено.'

    def do_show_inputs(self):
        return f"{self.__base.decode('utf-8')} и {self.__arg.decode('utf-8')}"


class Calculator(Operation):
    def do_divide(self, arg):
        if arg != 0:
            return self.base / float(arg)
        return super().do_zero_divide()

    def do_raise_to_power(self):
        res = self.check_float()
        if not res:
            res = int(self.base ** self.arg)
        return res


print('Доступные операции:\nadd (+)\nsubtract (-)\nmultiply (*)\ndivide (/)\nraise_to_power (**)\nshow_inputs')
cmd = input('введите название операции: ')
x = input('введите первый аргумент: ').encode('utf-8')
y = input('введите второй аргумент: ').encode('utf-8')

calc = Calculator(base=x, arg=y)
print(calc.ops(cmd))

