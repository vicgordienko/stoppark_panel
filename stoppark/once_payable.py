# coding=utf-8
from PyQt4.QtCore import QObject, pyqtSlot, pyqtProperty
from tariff import Tariff


class OncePayment(QObject):
    def __init__(self, payable, tariff):
        QObject.__init__(self)
        payable.payments.append(self)

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


class OncePaymentUnsupported(QObject):
    def __init__(self, payable):
        QObject.__init__(self)
        payable.payments.append(self)

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        return False

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return u''


class OncePayable(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.payments = []

    @pyqtSlot(QObject, result=QObject)
    def pay(self, tariff):
        if tariff.type not in [Tariff.ONCE]:
            return OncePaymentUnsupported(self)

        return OncePayment(self, tariff)