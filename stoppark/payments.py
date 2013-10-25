from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal
from PyQt4.QtGui import QWidget
from gevent import socket, spawn, sleep
from gevent.queue import Queue
from threading import Thread
from db import DB, Ticket
import time


class Reader(QObject):
    new_ticket = pyqtSignal(Ticket)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.db = None
        self.sock = None
        self.queue = None

    def _reader(self):
        try:
            while True:
                bar = self.sock.recv(128).strip(';?\n\r')
                print 'bar_read', time.time()

                ticket = self.db.get_ticket(bar)
                if not ticket:
                    Ticket.register(self.db, str(bar))
                    ticket = self.db.get_ticket(bar)

                print ticket

                print 'bar_processed', time.time()

                self.new_ticket.emit(ticket)

        except socket.error:
            print 'reader completed'

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

    def _loop(self):
        self.queue = Queue()
        self.db = DB()

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect('/tmp/bar')

        spawn(self._job)
        spawn(self._reader)
        spawn(self._tariff_updater)

        while True:
            payment = self.queue.get()

            if payment is not None:
                self._process_payment(payment)
            else:
                print 'got None'
                #[greenlet.kill() for greenlet in greenlets]
                break

        print 'reader loop completed'

    def start(self):
        self.thread.start()

    def pay(self, payment):
        if self.queue:
            self.queue.put(payment)
        else:
            print 'There is not queue to put payments.'

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

        self.ui = uic.loadUiType('payments.ui')[0]()
        self.ui.setupUi(self)

        self.ui.progress.setVisible(False)

        self.reader = Reader(self)
        self.reader.tariffs_updated.connect(self.update_tariffs)
        self.reader.start()

        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

    def update_tariffs(self, tariffs):
        if self.tariffs is None:
            print 'update_tariffs A', tariffs
            self.ready_to_handle()
        else:
            print 'update_tariffs B'
        self.tariffs = tariffs

    def ready_to_handle(self):
        self.reader.new_ticket.connect(self.handle_ticket)
        self.ui.cancel.setEnabled(False)
        self.ui.pay.setEnabled(False)

    def ready_to_pay(self):
        self.reader.new_ticket.disconnect()
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    def handle_ticket(self, ticket):
        self.ui.bar.setText(ticket.bar)
        self.new_payment.emit()

        self.payment = ticket.pay(self.tariffs[0])
        if self.payment:
            self.ui.explanation.setText(self.payment.explanation())
            self.ready_to_pay()
        else:
            self.ui.explanation.setText('\nAlready paid.')

    def pay(self):
        self.reader.payment_processed.connect(self.payment_completed)
        self.reader.pay(self.payment)
        self.ui.pay.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.ui.progress.setVisible(True)

    def cancel(self):
        self.ui.explanation.setText('')
        self.ui.bar.setText('-')
        self.ready_to_handle()

    def payment_completed(self):
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect()

        self.ui.explanation.setText(self.ui.explanation.text() + '\n Paid.')
        self.ready_to_handle()

    def stop_reader(self):
        self.reader.stop()
