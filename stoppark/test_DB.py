from unittest import TestCase
from db import DB
from datetime import datetime
from config import DATETIME_FORMAT_FULL
from ticket import Ticket


class TestDB(TestCase):
    def test_generate_payment(self):

        operator = 'Operator'

        class LocalDBMock(object):
            def session(self):
                return '1234567890', operator, '2013-12-28 13:00', None

        class MockDB(DB):
            def __init__(self):
                self.local = LocalDBMock()
                self.result = None

            def query(self, q, local):
                self.result = q
                return None

         #'insert into payment values(NULL, "{payment}", {tariff}, {console}, "{operator}", ' \
         #           ' "{now}", "{id}", {status}, {tariff}, {cost}*100, {units}, "{begin}", "{end}", {price}*100)'

        def single_test(db_payment_args):
            db = MockDB()
            db.generate_payment(db_payment_args)
            now = datetime.now().strftime(DATETIME_FORMAT_FULL)

            self.assertEqual(db.result, DB.PAYMENT_QUERY.format(console=0, operator=operator, status=Ticket.PAID,
                                                                now=now, **db_payment_args))

        single_test({
            'payment': 'Single payment',
            'tariff': 0,
            'id': '',
            'cost': 100,
            'units': 1,
            'begin': '',
            'end': '',
            'price': 100
        })

        single_test({
            'payment': 'Card payment',
            'tariff': 1,
            'id': '123',
            'cost': 200,
            'units': 5,
            'begin': '2013-01-01',
            'end': '2013-01-31',
            'price': 1000
        })

