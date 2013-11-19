# -*- coding: utf-8 -*-
import re
from threading import Thread
from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, QUrl
from PyQt4.QtGui import QWidget, QIcon, QSystemTrayIcon, QDialog
from PyQt4.QtDeclarative import QDeclarativeView
from keyboard import TicketInput
from gevent import socket, spawn, sleep
from gevent.queue import Queue
from db import DB, Ticket


class Reader(QObject):
    new_ticket = pyqtSignal(Ticket)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)
    notify = pyqtSignal(str, str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.db = None
        self.sock = None
        self.queue = None
        self._ticket = None

    def _reader(self):
        bar_regex = re.compile(r'(;(\d+)\?\r\n)')
        buf = ''
        try:
            while True:
                new_portion = self.sock.recv(128)
                if new_portion == '':
                    print 'fukoda'
                    self.sock.close()
                    return
                buf += new_portion
                print 'buf', buf

                last_index = 0
                for match in bar_regex.finditer(buf):
                    last_index = match.span()[1]
                    bar = match.group(2)
                    if len(bar) < 18:
                        continue

                    self._handle_bar(bar)

                buf = buf[last_index:]
        except socket.error:
            print 'reader completed'

    def _handle_bar(self, bar):
        print '_handle_bar'
        self._ticket = self.db.get_ticket(bar)
        if not self._ticket:
            print 'registering ticket'
            if Ticket.register(self.db, str(bar)):
                self._ticket = self.db.get_ticket(bar)
        self.new_ticket.emit(self._ticket)

    def _process_payment(self, payment):
        payment.execute(self.db)
        self.payment_processed.emit()

    @staticmethod
    def _job():
        while True:
            sleep(2)

    def _tariff_updater(self):
        while True:
            self.tariffs_updated.emit(self.db.get_tariffs())
            sleep(60)

    def _update_tariffs(self):
        self.tariffs_updated.emit(self.db.get_tariffs())

    def _loop(self):
        self.queue = Queue()
        self.db = DB(notify=lambda title, msg: self.notify.emit(title, msg))

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect('/tmp/bar')

        spawn(self._job)
        spawn(self._reader)
        #spawn(self._tariff_updater)

        self._update_tariffs()

        while True:
            action = self.queue.get()

            if action is not None:
                if isinstance(action, str):
                    if action == 'tariffs':
                        self._update_tariffs()
                    if action.startswith('bar:'):
                        self._handle_bar(action[4:])
                else:
                    self._process_payment(action)
            else:
                print 'got None'
                #[greenlet.kill() for greenlet in greenlets]
                break

        print 'reader loop completed'

    def start(self):
        self.thread.start()

    def handle_bar(self, bar):
        if self.queue:
            self.queue.put('bar:' + bar)
        else:
            print 'There is no queue to handle barcode.'

    def update_tariffs(self):
        if self.queue:
            self.queue.put('tariffs')
        else:
            print 'There is no queue to update tariffs.'

    def pay(self, payment):
        if self.queue:
            self.queue.put(payment)
        else:
            print 'There is no queue to put payments.'

    def stop(self):
        if self.queue is not None:
            self.queue.put(None)
        else:
            print 'Already stopped'


class Payments(QWidget):
    new_payment = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.tariffs = None
        self.payment = None
        self.ticket = None

        self.notifier = QSystemTrayIcon(QIcon('arrow-up-icon.png'), self)
        self.notifier.show()

        self.ui = uic.loadUiType('payments.ui')[0]()
        self.ui.setupUi(self)
        self.ui.progress.setVisible(False)
        self.ui.cancel.setEnabled(True)

        self.reader = Reader(self)
        self.reader.notify.connect(lambda title, msg: self.notifier.showMessage(title, msg))
        self.reader.tariffs_updated.connect(self.update_tariffs)
        self.reader.start()

        self.ui.keyboard.clicked.connect(self.manual_ticket_input)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

        self.ui.tariffs.setSource(QUrl('view.qml'))
        self.ui.tariffs.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        self.ui.tariffs.rootObject().new_payment.connect(self.handle_payment)

    def manual_ticket_input(self):
        self.reader.new_ticket.disconnect()
        ticket_input = TicketInput()
        if ticket_input.exec_() == QDialog.Accepted:
            self.reader.handle_bar(ticket_input.bar)
        self.reader.new_ticket.connect(self.handle_ticket)

    def update_tariffs(self, tariffs):
        if self.tariffs is None:
            self.ready_to_accept()
        self.tariffs = tariffs
        self.ui.tariffs.rootObject().set_tariffs(self.tariffs)

    def ready_to_accept(self):
        if self.ticket:
            self.ticket.payments = None
        self.ticket = None
        self.ui.tariffs.rootObject().setProperty('ticket', self.ticket)
        self.reader.new_ticket.connect(self.handle_ticket)
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(True)

    def ready_to_pay(self):
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    def handle_ticket(self, ticket):
        self.reader.new_ticket.disconnect()
        self.new_payment.emit()

        self.ticket = ticket
        self.ui.cancel.setEnabled(True)
        self.ui.keyboard.setEnabled(False)

        self.ui.tariffs.rootObject().setProperty('ticket', self.ticket)

    def handle_payment(self, payment):
        print 'handle_payment'
        payment = payment.toPyObject()
        if payment:
            self.payment = payment
            self.ui.pay.setEnabled(payment.enabled)
        else:
            self.ui.pay.setEnabled(False)

    def handle_current_tariff(self, tariff):
        tariff = tariff.toPyObject()
        if not hasattr(tariff, 'calc'):
            self.ui.explanation.setText('This tariff is not supported yet\n')
            self.ui.pay.setEnabled(False)
            return

        if self.ticket:
            self.payment = self.ticket.pay(tariff)
            if self.payment:
                self.ui.explanation.setText(self.payment.explanation())
                self.ready_to_pay()
            else:
                self.ui.explanation.setText('Already paid.')
        else:
            self.ui.explanation.setText(tariff.name)

    def cancel(self):
        self.ready_to_accept()

    def pay(self):
        self.reader.payment_processed.connect(self.payment_completed)
        self.reader.pay(self.payment)
        self.ui.pay.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.ui.tariffs.setEnabled(False)
        self.ui.progress.setVisible(True)

    def payment_completed(self):
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect(self.payment_completed)
        self.notifier.showMessage(u'Оплата', u'Оплата выполнена успешно')
        self.ui.tariffs.setEnabled(True)
        self.ready_to_accept()

    def stop_reader(self):
        self.reader.stop()
