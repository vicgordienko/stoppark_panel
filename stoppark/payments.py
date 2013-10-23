from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, QTimer
from PyQt4.QtGui import QWidget
from gevent import socket, spawn, sleep
from threading import Thread
from db import DB, Ticket


class BARReader(QObject):
    bar_read = pyqtSignal(str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.thread = Thread(target=self._loop)
        self.sock = None

    def _reader(self, sock):
        try:
            while True:
                bar = sock.recv(128)
                self.bar_read.emit(bar.strip(';?\n\r'))
        except socket.error:
            print 'reader completed'
            pass

    @staticmethod
    def _job():
        while True:
            sleep(2)

    def _loop(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect('/tmp/bar')

        spawn(self._job)
        spawn(self._reader, self.sock).join()

        print 'reader loop completed'

    def start(self):
        self.thread.start()

    def stop(self):
        if self.sock is not None:
            self.sock.close()


class Payments(QWidget):
    new_payment = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUi('payments.ui', self)

        self.reader = BARReader(self)
        self.reader.bar_read.connect(self.handle_bar)
        self.reader.start()

        self.db = DB()

        self.ui.pay.setEnabled(False)

    def handle_bar(self, bar):
        self.ui.bar.setText(bar)

        self.new_payment.emit()

        self.ticket = self.db.get_ticket(bar)
        if not self.ticket:
            Ticket.register(self.db, str(bar))
            self.ticket = self.db.get_ticket(bar)

        self.payment = self.ticket.pay(1)
        self.ui.explanation.setText(self.payment.explanation())

        self.ui.pay.setEnabled(True)

    def stop_reader(self):
        self.reader.stop()
