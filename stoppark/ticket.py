# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty, pyqtSlot
from datetime import datetime
from config import DATETIME_FORMAT, DATETIME_USER_FORMAT
from tariff import Tariff
from payment import Payment


class TicketPayment(Payment):
    def __init__(self, ticket, tariff):
        Payment.__init__(self, ticket.payments)

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.ticket = ticket
        self.tariff = tariff

        self.now = datetime.now()
        self.result = tariff.calc(self.ticket.time_in, self.now)

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return self._enabled

    @pyqtProperty(int, constant=True)
    def price(self):
        return self.result.price

    @property
    def paid_until(self):
        return self.ticket.time_in + self.result.paid_time

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return u'!Талон %s.\nНевозможно оплатить по этому тарифу.' % (self.ticket.bar,)
        return u'Оплата по талону %s.\n' \
               u'Время вьезда: %s.\n%s' \
               u'Длительность: %s' % (self.result.interval,) \
               % (self.ticket.bar, self.ticket.time_in.strftime(DATETIME_USER_FORMAT), self.result)

    def vfcd_explanation(self):
        return [
            u'%i грн./%s.' % (self.tariff.cost, self.tariff.intervalStr),
            u'Оплата: %i грн.' % (self.price,)
        ]

    TICKET_QUERY = ('update ticket set typetarif=%i, pricetarif="%s", summ=%i * 100,'
                    'summdopl=0, timecount="%s", status = status | %i where bar="%s"')

    def execute(self, db):
        ticket_args = (self.tariff.id, self.tariff.cost_db, self.result.price,
                       self.paid_until, Ticket.PAID, self.ticket.bar)
        ret = db.query(self.TICKET_QUERY % ticket_args) is None
        if not ret:
            return ret

        return db.generate_payment(ticket_payment=self)

    def check(self, db):
        interval = {Tariff.HOURLY: u'год.', Tariff.DAILY: u'доб.', Tariff.MONTHLY: u'міс.'}[self.tariff.interval]

        return Payment.check(self, db) + u'\n'.join([
            u' в\'їзд: %s' % (self.ticket.time_in.strftime(DATETIME_USER_FORMAT),),
            u'оплата: %s' % (self.now.strftime(DATETIME_USER_FORMAT),),
            u'тариф: %s грн./%s' % (self.tariff.costInfo, interval),
            u'тривалість паркування: %s' % (self.result.interval_u,),
            u'оплачено до: %s' % (self.paid_until.strftime(DATETIME_USER_FORMAT),),
            u'<hr />',
            u'Вартість: %s грн.' % (self.price,),
            u'<hr />',
            u'<<%s>>' % (self.ticket.bar,),
        ])


class TicketExcessPayment(Payment):
    def __init__(self, ticket, tariff, excess=False):
        Payment.__init__(self, ticket.payments)

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.ticket = ticket
        self.tariff = tariff
        self.excess = excess

        self.now = datetime.now()
        self.base_time = self.ticket.time_excess_paid if self.excess else self.ticket.time_paid
        self.result = tariff.calc(self.base_time, self.now)

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return self._enabled

    @pyqtProperty(int, constant=True)
    def price(self):
        return self.result.price

    @property
    def paid_until(self):
        return self.ticket.time_base_time + self.result.paid_time

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return u'!Талон %s.\n невозможно оплатить по этому тарифу.' % (self.ticket.bar,)
        return u'Доплата по талону %s.\n' \
               u'Время вьезда: %s.\n' \
               u'Последняя оплата: %s.\n%s' \
               u'С последней оплаты: %s' % (self.result.interval,) \
               % (self.ticket.bar, self.ticket.time_in.strftime(DATETIME_USER_FORMAT),
                  self.base_time.strftime(DATETIME_USER_FORMAT), self.result)

    def vfcd_explanation(self):
        return [
            u'%s грн./%s' % (self.tariff.costInfo, self.tariff.intervalStr),
            u'Доплата: %i грн.' % (self.price,)
        ]

    TICKET_QUERY = 'update ticket set summdopl = summdopl + %i*100, timedopl="%s", status = status | %i where bar="%s"'

    def execute(self, db):
        args = (self.result.price, self.paid_until, Ticket.PAID, self.ticket.bar)
        ret = db.query(self.TICKET_QUERY % args) is None
        if not ret:
            return ret

        return db.generate_payment(ticket_payment=self)

    def check(self, db):
        interval = {Tariff.HOURLY: u'год.', Tariff.DAILY: u'доб.', Tariff.MONTHLY: u'міс.'}[self.tariff.interval]

        return Payment.check(self, db) + u'\n'.join([
            u'остання оплата: %s' % (self.base_time.strftime(DATETIME_USER_FORMAT),),
            u'       доплата: %s' % (self.now.strftime(DATETIME_USER_FORMAT),),
            u'тариф: %s грн./%s' % (self.tariff.costInfo, interval),
            u'тривалість паркування: %s' % (self.result.interval_u,),
            u'оплачено до: %s' % (self.paid_until.strftime(DATETIME_USER_FORMAT),),
            u'<hr />',
            u'Вартість: %s грн.' % (self.price,),
            u'<hr />',
            u'<<%s>>' % (self.ticket.bar,),
        ])


class TicketPaymentUnsupported(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u'Талон %s\nНевозможно оплатить по этому тарифу.' % (self.ticket.bar,)


class TicketPaymentAlreadyPaid(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u'Талон %s уже оплачен.' % (self.ticket.bar,)


class TicketPaymentAlreadyOut(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u'Талон %s уже выехал.' % (self.ticket.bar,)


class TicketPaymentUndefined(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u'Оплата талона %s не определена.' % (self.ticket.bar,)


class Ticket(QObject):
    IN = 1
    PAID = 5
    OUT = 15

    EXCESS_INTERVAL = 15 * 60  # seconds

    @staticmethod
    def remove(db, bar):
        return db.query('delete from ticket where bar="%s"' % (bar,))

    @staticmethod
    def create(response):
        if response is False:
            return False
        try:
            fields = response[0]
            assert (len(fields) >= 12)
            return Ticket(fields)
        except (TypeError, AssertionError, IndexError, ValueError):
            return None

    @staticmethod
    def parse_bar(bar):
        return datetime.strptime(str(datetime.now().year) + bar[:10], '%Y%m%d%H%M%S')

    @staticmethod
    def register(db, bar):
        query = 'insert into ticket values("%s", NULL, "%s", NULL, NULL, NULL, NULL, "%s", NULL, NULL, NULL, 1)'
        try:
            ticket_time = Ticket.parse_bar(bar).strftime(DATETIME_FORMAT)
        except ValueError:
            return None
        args = ("Ticket", bar, ticket_time)
        return db.query(query % args) is None

    def __init__(self, fields):
        QObject.__init__(self)
        self.fields = fields
        self.payments = []

        self.id = fields[1]
        self._bar = fields[2]
        self.tariff_type = fields[3]
        self.tariff_price = fields[4]
        self.tariff_sum = fields[5]
        self.tariff_sum_excess = fields[6]
        self.time_in = datetime.strptime(fields[7], DATETIME_FORMAT)
        self.time_out = datetime.strptime(fields[8], DATETIME_FORMAT) if fields[8] != 'None' else None
        self.time_paid = datetime.strptime(fields[9], DATETIME_FORMAT) if fields[9] != 'None' else None
        self.time_excess_paid = datetime.strptime(fields[10], DATETIME_FORMAT) if fields[10] != 'None' else None
        self.status = int(fields[11])

    def __del__(self):
        print '~Ticket'

    @pyqtProperty(str)
    def bar(self):
        return self._bar

    @pyqtSlot(QObject, result=QObject)
    def pay(self, tariff):
        if tariff.type not in [Tariff.FIXED, Tariff.DYNAMIC]:
            return TicketPaymentUnsupported(self)

        if self.status == self.IN:
            return TicketPayment(self, tariff)

        if self.status == self.PAID:
            if self.time_excess_paid:
                if (datetime.now() - self.time_excess_paid).total_seconds() > self.EXCESS_INTERVAL:
                    return TicketExcessPayment(self, tariff, excess=True)
                else:
                    return TicketPaymentAlreadyPaid(self)

            if self.time_paid:
                if (datetime.now() - self.time_paid).total_seconds() > self.EXCESS_INTERVAL:
                    return TicketExcessPayment(self, tariff)
                else:
                    return TicketPaymentAlreadyPaid(self)

        if self.status == self.OUT:
            return TicketPaymentAlreadyOut(self)

        return TicketPaymentUndefined(self)

    OUT_QUERY = 'update ticket set timeout="%s", status = status | %i where bar = "%s"'

    def out(self, db):
        return db.query(self.OUT_QUERY % (datetime.now().strftime(DATETIME_FORMAT), self.OUT, self.bar)) is None

    def check(self):
        if self.status == self.IN:
            return False

        if self.status == self.PAID:
            now = datetime.now()

            if self.time_paid:
                if (now - self.time_paid).total_seconds() < self.EXCESS_INTERVAL:
                    return True
                elif self.time_excess_paid and (now - self.time_excess_paid).total_seconds() < self.EXCESS_INTERVAL:
                    return True


if __name__ == '__main__':
    import doctest
    doctest.testmod()