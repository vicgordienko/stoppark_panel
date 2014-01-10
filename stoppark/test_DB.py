from unittest import TestCase
from db import DB, LocalDB
from collections import namedtuple
from ticket import Ticket


PaymentArgs = namedtuple('PaymentArgs', ['payment', 'tariff', 'id', 'cost', 'units', 'begin', 'end', 'price'])


class LocalDBMock(LocalDB):
    def __init__(self, operator):
        super(LocalDBMock, self).__init__(':memory:')
        self.operator = operator

    def payments(self):
        return self.query('select Payment, Type, Kassa, Operator, TalonID,'
                          'Status, TarifType, Tarif, TarifKol, DTIn, DTOut, Summa from payment')

    def session(self, session_id=None):
        return '1234567890', self.operator, '2013-12-28 13:00', None


class MockDB(DB):
    #noinspection PyMissingConstructor
    def __init__(self, operator):
        self.local = LocalDBMock(operator)

    def query(self, q, local=False):
        with self.local.connection() as c:
            c.execute(q)


class TestDB(TestCase):
    def payment_check(self, args):
        operator = 'Operator'
        console = 0
        db = MockDB(operator)
        db.generate_payment(args)

        args = PaymentArgs(**args)
        self.assertEqual([[k for k in i] for i in db.local.payments()], [[args.payment, args.tariff, console, operator,
                                                                          args.id, Ticket.PAID, args.tariff,
                                                                          args.cost*100, args.units, args.begin,
                                                                          args.end, args.price*100]])

    def test_single_payment(self):
        self.payment_check({
            'payment': 'Single payment',
            'tariff': 0,
            'id': '',
            'cost': 100,
            'units': 1,
            'begin': '',
            'end': '',
            'price': 100
        })

    def test_card_payment(self):
        self.payment_check({
            'payment': 'Card payment',
            'tariff': 1,
            'id': '123',
            'cost': 200,
            'units': 5,
            'begin': '2013-01-01',
            'end': '2013-01-31',
            'price': 1000
        })

    def test_ticket_payment(self):
        self.payment_check({
            'payment': 'Talon payment',
            'tariff': 1,
            'id': '0123456789',
            'cost': 30,
            'units': 10,
            'begin': '2014-01-08 10:51:05',
            'end': '2014-01-08 15:55:10',
            'price': 300
        })
