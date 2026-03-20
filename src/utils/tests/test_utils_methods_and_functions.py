import datetime as dt
import string

from django.test import TestCase

from utils import (
    DateRange,
    chunkify,
    get_random_datetime,
    get_random_path,
    get_random_qualifier,
    get_random_string,
    get_random_value,
    has_unsupported_entity,
    keyfy,
    namefy,
    validate_entity,
)


class UtilsMethodAndFunctionsTestCase(TestCase):
    def test_chunkify(self):
        l_100 = list(range(100))
        self.assertEqual(
            chunkify(l_100, 10),
            [
                tuple(range(10)),
                tuple(range(10, 20)),
                tuple(range(20, 30)),
                tuple(range(30, 40)),
                tuple(range(40, 50)),
                tuple(range(50, 60)),
                tuple(range(60, 70)),
                tuple(range(70, 80)),
                tuple(range(80, 90)),
                tuple(range(90, 100)),
            ],
        )

    def test_get_random_datetime(self):
        start_date = get_random_datetime(
            dt.datetime(2019, 1, 1), dt.datetime(2019, 1, 2)
        )
        end_date = get_random_datetime(
            dt.datetime(2019, 1, 2), dt.datetime(2019, 1, 3)
        )
        self.assertTrue(start_date < end_date)
        self.assertTrue(start_date.date() == dt.date(2019, 1, 1))
        self.assertTrue(end_date.date() == dt.date(2019, 1, 2))

    def test_namefy(self):
        self.assertEqual(namefy('hello_world'), 'Hello World')
        self.assertEqual(namefy('hello_world_2'), 'Hello World 2')
        self.assertEqual(namefy('hello_world_2_3'), 'Hello World 2 3')

    def test_keyfy(self):
        self.assertEqual(keyfy('Hello World'), 'hello_world')
        self.assertEqual(keyfy('Hello World 2'), 'hello_world_2')
        self.assertEqual(keyfy('Hello World 2 3'), 'hello_world_2_3')

    def test_get_random_string(self):
        s = get_random_string()

        self.assertEqual(len(s), 100)
        self.assertIsInstance(s, str)

        alphabet = string.ascii_uppercase + string.digits

        for c in s:
            self.assertIn(c, alphabet)

    def test_get_random_path(self):
        p = get_random_path()
        self.assertIsInstance(p, str)
        self.assertGreater(len(p), 0)
        self.assertIn('/', p)
        self.assertIn('.', p)

    def test_get_random_qualifier(self):
        q = get_random_qualifier()
        self.assertIsInstance(q, str)
        self.assertGreater(len(q), 0)
        self.assertIn(q, ['UTS', 'FIL', 'DIR'])

    def test_get_random_value(self):
        valid_metrics_types = {
            'INT': int,
            'FLOAT': float,
            'PERCENT': float,
            'BOOL': bool,
            'STRING': float,
            'DATA': int,
            'WORK_DUR': int,
            'DISTRIB': int,
            'RATING': int,
            'LEVEL': bool,
            'MILLISEC': float,
        }

        for metric_type, metric_type_class in valid_metrics_types.items():
            v = get_random_value(metric_type)
            self.assertIsInstance(
                v,
                metric_type_class,
                msg=f'[{metric_type}] - Expected {metric_type_class} but got {type(v)}',
            )

    def test_create_from_today_static_method(self):
        start_date = dt.datetime(2019, 1, 1)
        end_date = dt.datetime(2019, 1, 2)

        dr = DateRange(start_date, end_date)

        self.assertEqual(dr.start, start_date)
        self.assertEqual(dr.end, end_date)

        days = 7
        dr2 = DateRange.create_from_today(days)

        end_day = dt.datetime.today()

        self.assertEqual(dr2.end.day, end_day.day)
        self.assertEqual(dr2.end.month, end_day.month)
        self.assertEqual(dr2.end.year, end_day.year)

        start_day = dt.datetime.today() - dt.timedelta(days=days)

        self.assertEqual(dr2.start.day, start_day.day)
        self.assertEqual(dr2.start.month, start_day.month)
        self.assertEqual(dr2.start.year, start_day.year)
