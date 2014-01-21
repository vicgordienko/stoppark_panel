# coding=utf-8
from PyQt4.QtCore import QObject, pyqtSlot, pyqtProperty
from datetime import datetime, date
from tariff import Tariff
from payment import Payment
from config import DATETIME_FORMAT, DATE_FORMAT, DATE_USER_FORMAT
from i18n import language
_ = language.ugettext
_n = language.ungettext


class CardPayment(Payment):
    def __init__(self, card, tariff):
        Payment.__init__(self, card.payments)
        self.card = card

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.tariff = tariff
        self.result = self.tariff.calc(self.card.date_reg, self.card.date_end)
        if self.result is None:
            self._enabled = False

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return self._enabled

    @pyqtProperty(int, constant=True)
    def price(self):
        return self.result.price

    @pyqtProperty(str, constant=True)
    def explanation(self):
        base = _('%(fio)s.\n'
                 '[%(make)s] [%(number)s] [%(status)s]\n'
                 'Valid from %(begin)s to %(end)s\n') % {
                     'sn': self.card.sn,
                     'status': {
                         Card.INSIDE: _('inside'),
                         Card.OUTSIDE: _('outside')
                     }.get(self.card.status, _('unknown status')),
                     'fio': self.card.fio,
                     'begin':  self.card.date_reg.strftime(DATE_USER_FORMAT),
                     'end': self.card.date_end.strftime(DATE_USER_FORMAT),
                     'make': self.card.make,
                     'number': self.card.number
                 }

        if self._enabled:
            return u'%s%s\n%s' % (base, _('Refill for ') + self.tariff.interval_str(self.result.units, True),
                                  self.result)
        else:
            return base + _('Cannot be refilled by this tariff.')

    def vfcd_explanation(self):
        return [
            _('%(begin)s - %(end)s') % {
                'begin':  self.card.date_reg.strftime(DATE_USER_FORMAT),
                'end': self.card.date_end.strftime(DATE_USER_FORMAT)
            },
            _('Price: $%i') % (self.price,)
        ]

    @property
    def db_payment_args(self):
        return {
            'payment': 'Card payment',
            'tariff': self.tariff.id,
            'id': self.card.sn,
            'cost': self.result.cost,
            'units': self.result.units,
            'begin': self.result.begin,
            'end': self.result.end,
            'price': self.result.price
        }

    CARD_QUERY = 'update card set DTreg="%s",DTend="%s", TarifType=%i, TarifPrice=%i*100, TarifSumm=%i*100 ' \
                 'where CardID="%s"'

    def execute(self, db):
        args = (self.result.begin.strftime(DATE_FORMAT), self.result.end.strftime(DATE_FORMAT),
                self.tariff.id, self.result.cost, self.result.price, self.card.sn)
        ret = db.query(self.CARD_QUERY % args) is None
        if not ret:
            return ret

        return db.generate_payment(self.db_payment_args)

    def check(self, db):
        args = {
            'sn': self.card.sn,
            'tariff': self.tariff.title,
            'cost_info': self.tariff.cost_info_check,
            'begin': self.card.date_reg.strftime(DATE_USER_FORMAT),
            'end': self.card.date_end.strftime(DATE_USER_FORMAT),
            'refill': _('_Refill for ') + self.tariff.interval_str_check(self.result.units, True),
            'new_begin': self.result.begin.strftime(DATE_USER_FORMAT),
            'new_end': self.result.end.strftime(DATE_USER_FORMAT),
            'price': self.price
        }

        return Payment.check(self, db) + _('Card %(sn)s\n'
                                           '%(tariff)s: %(cost_info)s\n'
                                           'Before refill: from %(begin)s to %(end)s\n'
                                           '%(refill)s\n'
                                           'After refill: from %(new_begin)s to %(new_end)s\n'
                                           '<hr />\n'
                                           'Price: %(price)s\n'
                                           '<hr />') % args


class CardPaymentUnsupported(Payment):
    def __init__(self, card):
        Payment.__init__(self, card.payments)
        self.card = card

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Card %(sn)s\n'
                 '%(fio)s\n') % {
                     'sn': self.card.sn, 'fio': self.card.fio
                 } + _('Cannot be refilled by this tariff.')


class Card(QObject):
    """
    This is a Card class that represents contactless card from remote database.
    There are many card types, and every one of them is subject to a set of rules.

    Only CLIENT cards can generate payments.
    CLIENT and STAFF cards can pass through parking gates (if check method considers their state appropriate).

    Only CASHIER cards can open sessions and only same CASHIER (or ADMIN, if there is no cashier nearby) can close it.
    """

    STAFF = 0
    ONCE = 1
    CLIENT = 2
    CASHIER = 3
    ADMIN = 4

    ALLOWED_TYPE = [ONCE, CLIENT, STAFF]

    ALLOWED = 1
    LOST = 2
    EXPIRED = 3
    DENIED = 4
    OUTSIDE = 5
    INSIDE = 6

    ALLOWED_STATUS = [
        [ALLOWED, OUTSIDE],  # 0, directed inside
        [ALLOWED, INSIDE]    # 1, directed outside
    ]

    @staticmethod
    def create(response):
        if response is False:
            return False
        try:
            fields = response[0]
            assert(len(fields) >= 19)
            return Card(fields)
        except (TypeError, AssertionError, IndexError, ValueError):
            return None

    @staticmethod
    def parse_date(value):
        try:
            return datetime.strptime(value, DATE_FORMAT).date()
        except ValueError:
            return None

    def __init__(self, fields):
        QObject.__init__(self)
        self.payments = []

        self.fields = fields

        self.id = int(fields[1])
        self.type = int(fields[2])
        self.sn = fields[3]
        self.date_reg = self.parse_date(fields[4])
        self.date_end = self.parse_date(fields[5])
        self.date_in = fields[6]
        self.date_out = fields[7]
        self.drive_name = fields[8]
        self.drive_sname = fields[9]
        self.drive_fname = fields[10]
        self.drive_phone = fields[11]
        self.number = fields[12].decode('utf8', errors='replace') if fields[12] != 'None' else u'?'
        self.make = fields[13].decode('utf8', errors='replace') if fields[13] != 'None' else u'?'
        self.color = fields[14]
        self.status = int(fields[15])
        self.tariff_type = int(fields[16]) if fields[16] != 'None' else None
        self.tariff_price = fields[17]
        self.tariff_sum = fields[18]

    def check(self, direction):
        if self.type not in self.ALLOWED_TYPE:
            return False
        if self.status not in self.ALLOWED_STATUS[direction]:
            return False

        if self.date_reg is None or self.date_end is None:
            return None

        return self.date_reg <= date.today() <= self.date_end

    @pyqtSlot(QObject, result=QObject)
    def pay(self, tariff):
        if tariff.type not in [Tariff.PREPAID, Tariff.SUBSCRIPTION]:
            return CardPaymentUnsupported(self)

        return CardPayment(self, tariff)

    @pyqtProperty(str, constant=True)
    def fio(self):
        return ('%s %s %s' % (self.drive_fname, self.drive_name, self.drive_sname)).decode('utf8', errors='replace')

    @pyqtProperty(int, constant=True)
    def tariff(self):
        return self.tariff_type

    @pyqtProperty(str, constant=True)
    def fio_short(self):
        return u'%s %s.%s.' % (self.drive_fname.decode('utf8', errors='replace'),
                               self.drive_name.decode('utf8', errors='replace')[0],
                               self.drive_sname.decode('utf8', errors='replace')[0])

    def moved(self, db, addr, inside):
        status = Card.INSIDE if inside else Card.OUTSIDE
        datetime_update = ('DTIn = "%s"' if inside else 'DTOut = "%s"') % (datetime.now().strftime(DATETIME_FORMAT))
        db.query('update card set status = %i, %s where cardid = \"%s\"' % (status, datetime_update, self.sn))
        return db.generate_pass_event(addr, inside, self.sn)


if __name__ == '__main__':
    import doctest
    doctest.testmod()