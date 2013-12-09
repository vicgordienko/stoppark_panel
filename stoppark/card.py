# coding=utf-8
from PyQt4.QtCore import QObject, pyqtSlot, pyqtProperty
from datetime import datetime, date
from tariff import Tariff
from payment import Payment
from config import DATETIME_FORMAT, DATE_FORMAT, DATE_USER_FORMAT


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
        base = u'Карточка %s\n%s.\n' \
               u'Действительна от %s до %s\n' % (self.card.sn, self.card.fio,
                                                 self.card.date_reg.strftime(DATE_USER_FORMAT),
                                                 self.card.date_end.strftime(DATE_USER_FORMAT))
        if self._enabled:
            return base + unicode(self.result)
        else:
            return base + u'Невозможно оплатить по этому тарифу.'

    def vfcd_explanation(self):
        return [
            u'%s - %s' % (self.result.begin.strftime(DATE_USER_FORMAT),
                          self.result.end.strftime(DATE_USER_FORMAT)),
            u'Оплата: %s грн.' % (self.price,)
        ]

    CARD_QUERY = 'update card set DTreg="%s",DTend="%s", TarifType=%i, TarifPrice=%i*100, TarifSumm=%i*100 ' \
                 'where CardID="%s"'

    def execute(self, db):
        args = (self.result.begin.strftime(DATE_FORMAT), self.result.end.strftime(DATE_FORMAT),
                self.tariff.id, self.result.cost, self.result.price, self.card.sn)
        ret = db.query(self.CARD_QUERY % args) is None
        if not ret:
            return ret

        return db.generate_payment(card_payment=self)


class CardPaymentUnsupported(Payment):
    def __init__(self, card):
        Payment.__init__(self, card.payments)
        self.card = card

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u'Карточка %s\n%s.\nНевозможно оплатить по этому тарифу.' % (self.card.sn, self.card.fio)


class Card(QObject):
    STAFF = 0
    ONCE = 1
    CLIENT = 2
    CASHIER = 3
    ADMIN = 4

    ALLOWED_TYPE = [ONCE, CLIENT]

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
        except (ValueError, TypeError, AssertionError):
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

        self.id = fields[1]
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
        self.number = fields[12]
        self.model = fields[13]
        self.color = fields[14]
        self.status = int(fields[15])
        self.tariff_type = fields[16]
        self.tariff_price = fields[17]
        self.tariff_sum = fields[18]

    def check(self, direction):
        if self.type not in [Card.STAFF, Card.CLIENT]:
            return False
        if self.status not in self.ALLOWED_STATUS[direction]:
            return False
        if self.type not in self.ALLOWED_TYPE:
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