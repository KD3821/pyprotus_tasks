import unittest
import functools

from api import (
    CharField,
    ArgumentsField,
    EmailField,
    PhoneField,
    DateField,
    BirthDayField,
    GenderField,
    ClientIDsField,
    RequestMeta,
)


def cases(args_list):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in args_list:
                new_args = args + (i if isinstance(i, tuple) else (i,))
                try:
                    func(*new_args)
                except AssertionError as e:
                    print(f'Failed: {func.__doc__}. Result: {e}. Arguments: {new_args[-1]}')
                    raise e
        return wrapper
    return decorator


class TestFieldClass(unittest.TestCase):

    @staticmethod
    def create_abstract_request_class_with_prop(field):
        name = "AbstractRequest"
        bases = (object,)
        class_attributes = {"prop": field()}
        abs_req_cls = RequestMeta(name, bases, class_attributes)
        return abs_req_cls

    @staticmethod
    def assign_value(cls, value):
        obj = cls(method_args={"prop": value})
        return obj.prop

    @cases([
        1,
        0.2,
        True,
        None
    ])
    def test_char_field(self, value):
        """ Test CharField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=CharField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        1,
        0.2,
        True,
        'abcmail.ru'
    ])
    def test_email_field(self, value):
        """ Test EmailField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=EmailField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        7911911445,
        89119114455,
        "7911911445",
        "89119114455",
        "abcdefghijk"
    ])
    def test_phone_field(self, value):
        """ Test PhoneField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=PhoneField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        "01.21.2024",
        "21/01/2024",
        "21-01-2024",
        "21.01.24"
    ])
    def test_date_field(self, value):
        """ Test DateField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=DateField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        "aa.bb.1999",
        "21.01.1969",
        "01.21.2024",
        "21/01/2024",
        "21-01-2024",
        "21.01.24"
    ])
    def test_birthday_field(self, value):
        """ Test BirthDayField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=BirthDayField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        "male",
        "1",
        3,
        True
    ])
    def test_gender_field(self, value):
        """ Test GenderField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=GenderField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)

    @cases([
        [1, 'a', 5],
        {1, 3, 5},
        {1: 1, 3: 3, 5: 5},
        1,
        None,
        True
    ])
    def test_client_ids_field(self, value):
        """ Test ClientIDsField """
        abs_req_cls = self.create_abstract_request_class_with_prop(field=ClientIDsField)
        self.assertRaises(ValueError, self.assign_value, cls=abs_req_cls, value=value)


if __name__ == "__main__":
    unittest.main()


"""
to run tests: python3 -m unittest discover -s tests/unit
"""