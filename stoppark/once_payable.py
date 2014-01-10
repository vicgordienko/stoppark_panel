# coding=utf-8
from PyQt4.QtCore import QObject, pyqtSlot, pyqtProperty
from tariff import Tariff
from payment import Payment
from datetime import datetime
from config import DATETIME_FORMAT_USER
from i18n import language
_ = language.ugettext
_n = language.ungettext


class OncePayment(Payment):
    def __init__(self, payable, tariff):
        Payment.__init__(self, payable.payments)
        self.tariff = tariff

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return True

    @pyqtProperty(int, constant=True)
    def price(self):
        return self.tariff.cost

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return _('Single payment')

    def vfcd_explanation(self):
        return [
            _('Single payment'),
            _('Price: $%i') % (self.price,)
        ]

    @property
    def db_payment_args(self):
        return {
            'payment': 'Single payment',
            'tariff': self.tariff.id,
            'id': '',
            'cost': self.price,
            'units': 1,
            'begin': '',
            'end': '',
            'price': self.price
        }

    def execute(self, db):
        return db.generate_payment(self.db_payment_args)

    def check(self, db):
        return Payment.check(self, db) + _('date: %(now)s\n'
                                           '%(tariff)s: $%(price)s\n'
                                           '<hr />') % {
                                               'now': datetime.now().strftime(DATETIME_FORMAT_USER),
                                               'tariff': self.tariff.title,
                                               'price': self.price
                                           }


class OncePaymentUnsupported(Payment):
    def __init__(self, payable):
        Payment.__init__(self, payable.payments)

    @pyqtProperty(str, constant=True)
    def explanation(self):
        """
        When OncePayable doesn't support given tariff, no message should be present.
        """
        return u''


class OncePayable(QObject):
    """
    Its a default Payable concept, used when there is no other Payables present.
    """
    def __init__(self):
        QObject.__init__(self)
        self.payments = []

    @pyqtSlot(QObject, result=QObject)
    def pay(self, tariff):
        if tariff.type not in [Tariff.ONCE]:
            return OncePaymentUnsupported(self)

        return OncePayment(self, tariff)