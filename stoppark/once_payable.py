# coding=utf-8
from PyQt4.QtCore import QObject, pyqtSlot, pyqtProperty
from tariff import Tariff
from payment import Payment
from datetime import datetime
from config import DATETIME_USER_FORMAT


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
        return u'Разовая оплата'

    def vfcd_explanation(self):
        return [
            u'Разовая оплата',
            u'К оплате: %i грн.' % (self.price,)
        ]

    def execute(self, db):
        return db.generate_payment(once_payment=self)

    def check(self, db):
        return Payment.check(self, db) + u'\n'.join([
            u'дата друку: %s' % (datetime.now().strftime(DATETIME_USER_FORMAT)),
            u'%s: %s грн.' % (self.tariff.title, self.price),
            u'<hr />',
        ])


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