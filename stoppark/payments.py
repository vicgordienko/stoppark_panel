# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt4.QtGui import QWidget, QDialog
from PyQt4.QtDeclarative import QDeclarativeView
from keyboard import TicketInput
from once_payable import OncePayable
from i18n import language
_ = language.ugettext


class Payments(QWidget):
    tariff_update_requested = pyqtSignal()
    display_requested = pyqtSignal(object)
    notify_requested = pyqtSignal(str, str)

    manual_ticket_inputted = pyqtSignal(str)

    payable_accepted = pyqtSignal()
    payment_initiated = pyqtSignal(QObject)
    payment_completed = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.tariffs = None
        self.payment = None
        self.payable = None
        self.accept_payable = True

        self.ui = uic.loadUiType('payments.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.ui.keyboard.clicked.connect(self.manual_ticket_input)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

        self.ui.tariffs.setSource(QUrl('view.qml'))
        self.ui.tariffs.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        self.ui.tariffs.rootObject().new_payment.connect(self.handle_payment)

    def localize(self):
        self.ui.pay.setText(_('Pay'))
        self.ui.cancel.setText(_('Cancel'))

    def begin_session(self, fio, access):
        if access in ['operator']:
            self.tariff_update_requested.emit()
            self.ui.tariffs.rootObject().set_message(_('No tariffs to display'))
            return True
        return False

    def end_session(self):
        self.accept_payable = False
        self.ui.progress.setVisible(False)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.update_tariffs(None)
        self.ui.tariffs.rootObject().set_message(_('Waiting for operator card...'))
        return False

    def manual_ticket_input(self):
        self.accept_payable = False
        ticket_input = TicketInput()
        if ticket_input.exec_() == QDialog.Accepted:
            self.manual_ticket_inputted.emit(ticket_input.bar)
        self.accept_payable = True

    def update_tariffs(self, tariffs):
        if self.tariffs is None and tariffs is not None:
            self.tariffs = tariffs
            self.ready_to_accept()
        else:
            self.tariffs = tariffs
            self.ui.tariffs.rootObject().set_tariffs_with_payable(self.tariffs, self.payable)

    def ready_to_accept(self):
        if self.payable:
            self.payable.payments = None
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(True)

        self.payable = OncePayable()
        self.ui.tariffs.rootObject().set_tariffs_with_payable(self.tariffs, self.payable)
        self.accept_payable = True

    def ready_to_pay(self):
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    @pyqtSlot(QObject, list)
    def handle_payable(self, payable, tariffs):
        if not self.accept_payable:
            print 'payable rejected'
            return

        self.accept_payable = False
        self.payable_accepted.emit()

        self.tariffs = tariffs
        self.payable = payable
        self.ui.cancel.setEnabled(True)
        self.ui.keyboard.setEnabled(False)

        self.ui.tariffs.rootObject().set_tariffs_with_payable(self.tariffs, self.payable)

    def handle_payment(self, payment):
        payment = payment.toPyObject()
        print 'handle_payment', payment
        if payment:
            self.payment = payment
            self.ui.pay.setEnabled(payment.enabled)
            if payment.enabled:
                self.display_requested.emit(payment.vfcd_explanation())
            else:
                self.display_requested.emit(None)
        else:
            self.display_requested.emit(None)
            self.ui.pay.setEnabled(False)

    def cancel(self):
        self.ready_to_accept()

    def pay(self):
        self.payment_initiated.emit(self.payment)
        self.ui.pay.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.ui.tariffs.setEnabled(False)
        self.ui.progress.setVisible(True)

    def handle_payment_processed(self):
        self.payment = None
        self.ui.progress.setVisible(False)
        self.notify_requested.emit(_('Payment'), _('Payment has been successful'))
        self.ui.tariffs.setEnabled(True)
        self.ready_to_accept()
        self.payment_completed.emit()


if __name__ == '__main__':
    import doctest
    doctest.testmod()