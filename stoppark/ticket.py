# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty, pyqtSlot
from datetime import datetime
from config import DATETIME_FORMAT, DATETIME_FORMAT_FULL, DATETIME_FORMAT_USER
from tariff import Tariff
from payment import Payment
from i18n import language
_ = language.ugettext
_n = language.ungettext


class BaseTicketPayment(Payment):
    def __init__(self, ticket, tariff):
        Payment.__init__(self, ticket.payments)

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.ticket = ticket
        self.tariff = tariff
        self.now = datetime.now()

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return self._enabled

    @pyqtProperty(int, constant=True)
    def price(self):
        return self.result.price

    @property
    def check_interval(self):
        return {
            Tariff.HOURLY: _n('hour_', 'hours_', 1),
            Tariff.DAILY: _n('day_', 'days_', 1),
            Tariff.MONTHLY: _n('month_', 'months_', 1)
        }[self.tariff.interval]

    @property
    def db_payment_args(self):
        return {
            'payment': 'Talon payment',
            'tariff': self.tariff.id,
            'id': self.ticket.bar,
            'cost': self.result.cost,
            'units': self.result.units,
            'begin': self.ticket.time_in.strftime(DATETIME_FORMAT_FULL),
            'end': self.now.strftime(DATETIME_FORMAT_FULL),
            'price': self.result.price
        }


class TicketPayment(BaseTicketPayment):
    def __init__(self, ticket, tariff):
        BaseTicketPayment.__init__(self, ticket, tariff)

        if self._enabled:
            self.result = tariff.calc(self.ticket.time_in, self.now)

    @property
    def paid_until(self):
        return self.ticket.time_in + self.result.paid_time

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return _('Ticket %s.\n'
                     'Not payable with this tariff.') % (self.ticket.bar,)
        return _('Payment for ticket %(bar)s.\n'
                 'Time in: %(time_in)s.\n'
                 '%(details)s') % {
                     'bar': self.ticket.bar,
                     'time_in': self.ticket.time_in.strftime(DATETIME_FORMAT_USER),
                     'details': self.result
                 }

    def vfcd_explanation(self):
        return [
            self.tariff.cost_info,
            self.price_info
        ]

    TICKET_QUERY = ('update ticket set typetarif=%i, pricetarif="%s", summ=%i * 100,'
                    'summdopl=0, timecount="%s", status = status | %i where bar="%s"')

    def execute(self, db):
        ticket_args = (self.tariff.id, self.tariff.cost_db, self.result.price,
                       self.paid_until.strftime(DATETIME_FORMAT), Ticket.PAID, self.ticket.bar)
        ret = db.query(self.TICKET_QUERY % ticket_args) is None
        if not ret:
            return ret

        return db.generate_payment(self.db_payment_args)

    def check(self, db):
        args = {
            'time_in': self.ticket.time_in.strftime(DATETIME_FORMAT_USER),
            'now': self.now.strftime(DATETIME_FORMAT_USER),
            'cost_info': self.tariff.cost_info_check,
            'duration': self.result.check_duration,
            'paid_until': self.paid_until.strftime(DATETIME_FORMAT_USER),
            'price': self.price,
            'bar': self.ticket.bar
        }

        return (Payment.check(self, db) + _('  entry time: %(time_in)s\n'
                                            'payment time: %(now)s\n'
                                            '      tariff: %(cost_info)s\n'
                                            'parking duration: %(duration)s\n'
                                            '  paid until: %(paid_until)s\n'
                                            '<hr />\n'
                                            'Price: $%(price)s\n'
                                            '<hr />\n'
                                            '<<%(bar)s>>') % args)


class TicketExcessPayment(BaseTicketPayment):
    def __init__(self, ticket, tariff, excess=False):
        BaseTicketPayment.__init__(self, ticket, tariff)

        if self._enabled:
            self.excess = excess
            self.base_time = self.ticket.time_excess_paid if self.excess else self.ticket.time_paid
            self.result = tariff.calc(self.base_time, self.now)

    @property
    def paid_until(self):
        return self.base_time + self.result.paid_time

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return _('Ticket %s.\n'
                     'Not payable with this tariff.') % (self.ticket.bar,)
        return _('Extra payment for ticket: %(bar)s.\n'
                 'Time in: %(time_in)s.\n'
                 'Last payment: %(base_time)s.\n'
                 '%(details)s') % {
                     'bar': self.ticket.bar,
                     'time_in': self.ticket.time_in.strftime(DATETIME_FORMAT_USER),
                     'base_time': self.base_time.strftime(DATETIME_FORMAT_USER),
                     'details': self.result
                 }

    def vfcd_explanation(self):
        return [
            self.tariff.cost_info,
            _('Surcharge: $%i') % (self.price,)
        ]

    TICKET_QUERY = 'update ticket set summdopl = summdopl + %i*100, timedopl="%s", status = status | %i where bar="%s"'

    def execute(self, db):
        args = (self.result.price, self.paid_until.strftime(DATETIME_FORMAT), Ticket.PAID, self.ticket.bar)
        ret = db.query(self.TICKET_QUERY % args) is None
        if not ret:
            return ret

        return db.generate_payment(self.db_payment_args)

    def check(self, db):
        args = {
            'base_time': self.base_time.strftime(DATETIME_FORMAT_USER),
            'now': self.now.strftime(DATETIME_FORMAT_USER),
            'cost_info': self.tariff.cost_info_check,
            'duration': self.result.check_duration,
            'paid_until': self.paid_until.strftime(DATETIME_FORMAT_USER),
            'price': self.price,
            'bar': self.ticket.bar
        }

        return (Payment.check(self, db) + _('last payment: %(base_time)s\n'
                                            '   surcharge: %(now)s\n'
                                            '      tariff: %(cost_info)s\n'
                                            'parking duration: %(duration)s\n'
                                            '  paid until: %(paid_until)s\n'
                                            '<hr />\n'
                                            'Price: $%(price)s\n'
                                            '<hr />\n'
                                            '<<%(bar)s>>') % args)


class TicketPaymentUnsupported(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Ticket %s.\n'
                 'Not payable with this tariff.') % (self.ticket.bar,)


class TicketPaymentAlreadyPaid(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Ticket %s already paid.') % (self.ticket.bar,)


class TicketPaymentAlreadyOut(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Ticket %s already out.') % (self.ticket.bar,)


class TicketPaymentUndefined(Payment):
    def __init__(self, ticket):
        Payment.__init__(self, ticket.payments)
        self.ticket = ticket

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Ticket %s payment undefined.') % (self.ticket.bar,)


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
        """
        This method currently implements heuristics for detecting year of barcode date.
        Since there is no information about year on barcode itself, we try to parse barcode as if it has current year
        and if it fails (no such date) or resulting date is greater than current datetime we try to parse it
        again with previous year.
        @param bar: string, barcode from barcode reader
        @return: datetime.datetime, datetime of ticket moving inside
        """
        try:
            probable_date = datetime.strptime(str(datetime.now().year) + bar[:10], '%Y%m%d%H%M%S')
            if probable_date > datetime.now():
                raise ValueError
            return probable_date
        except ValueError:
            return datetime.strptime(str(datetime.now().year - 1) + bar[:10], '%Y%m%d%H%M%S')

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