# -*- coding: utf-8 -*-
import re
from threading import Thread
from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt4.QtGui import QWidget, QIcon, QSystemTrayIcon, QDialog
from PyQt4.QtDeclarative import QDeclarativeView
from login import LoginDialog, LogoffDialog
from keyboard import TicketInput
from gevent import spawn, sleep, get_hub
from gevent.queue import Queue
from safe_socket import SafeSocket
from db import DB, Ticket, Card
from once_payable import OncePayable
from report import Report
from datetime import datetime
from i18n import language
_ = language.ugettext


class TicketReader(object):
    def __init__(self, peer, new_payable):
        self.regex = re.compile(r'(;(?P<bar>\d+)\?\r\n)')
        self.peer = peer
        self.new_payable = new_payable
        self.ticket = None

    def handle_bar(self, bar, db):
        print 'handle_bar', bar
        self.ticket = db.get_ticket(bar)
        if self.ticket is None:
            print 'registering ticket', bar
            if Ticket.register(db, str(bar)):
                self.ticket = db.get_ticket(bar)
        if self.ticket:
            self.new_payable.emit(self.ticket, db.get_tariffs())

    def __call__(self, db):
        sock = SafeSocket(self.peer)
        buf = ''
        while True:
            buf += sock.recv(128)
            print 'ticket_buf', buf

            last_index = 0
            for match in self.regex.finditer(buf):
                last_index = match.span()[1]
                bar = match.group('bar')
                if len(bar) < 18:
                    continue
                self.handle_bar(bar, db)

            buf = buf[last_index:]


class CardReader(object):
    def __init__(self, peer, new_payable, new_operator):
        self.regex = re.compile(r'(;(?P<sn>[A-Z\d]+)\?)')
        self.peer = peer
        self.new_payable = new_payable
        self.new_operator = new_operator
        self.buf = ''
        self.card = None

    def handle_card(self, sn, db):
        print 'handle_card', sn
        self.card = db.get_card(sn)
        if self.card:
            if self.card.type in [Card.CLIENT]:
                self.new_payable.emit(self.card, db.get_tariffs())
            if self.card.type in [Card.CASHIER, Card.ADMIN]:
                self.new_operator.emit(self.card)

    @staticmethod
    def card_read_loop(sock):
        while True:
            sock.send('n')
            sleep(1)

    def __call__(self, db):
        sock = SafeSocket(self.peer)
        spawn(self.card_read_loop, sock)
        buf = ''
        while True:
            buf += sock.recv(128)
            print 'card_buf', buf

            last_index = 0
            for match in self.regex.finditer(buf):
                last_index = match.span()[1]
                bar = match.group('sn')

                self.handle_card(bar, db)

            buf = buf[last_index:]


class DisplayLoop(object):
    def __init__(self, peer):
        self.peer = peer
        self.queue = None

    def time_loop(self, sock):
        line_length = 20
        date_format = _('%x')
        time_format = _('%X')
        while True:
            now = datetime.now()
            self.display(sock, [
                now.strftime(date_format).center(line_length),
                now.strftime(time_format).center(line_length)
            ])
            sleep(1)

    def __call__(self):
        self.queue = Queue()
        sock = SafeSocket(self.peer)
        # '\x02\x05\x53\x3c\x03' set russian character set, this command is redundant for already configured display
        sock.send('\x1b\x40' '\x02\x05\x53\x3c\x03' '\x0c')  # initialize display and clear screen
        time_loop = spawn(self.time_loop, sock)
        while True:
            messages = self.queue.get()
            if messages is None:
                if time_loop is None:
                    time_loop = spawn(self.time_loop, sock)
            else:
                if time_loop is not None:
                    time_loop.kill()
                    time_loop = None
                self.display(sock, messages)

    @staticmethod
    def display(sock, messages):
        messages = [message.encode('cp866', errors='replace') for message in messages]
        # set cursor at given position and send each message
        [sock.send('\x1b\x6c\x01' + chr(i+1) + message + ' '*(20 - len(message))) for i, message in enumerate(messages)]


def async(method):
    """async decorator that wraps up self.async.send() call during async operations"""
    def async_wrapper(self, *args, **kw):
        self.queue.put(lambda: method(self, *args, **kw))
        self.async.send()
    return async_wrapper


class Reader(QObject):
    new_payable = pyqtSignal(QObject, list)
    new_operator = pyqtSignal(QObject)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)
    notify = pyqtSignal(str, str)
    session_begin = pyqtSignal(str, str)
    session_end = pyqtSignal()
    report = pyqtSignal(object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.async = None
        self.db = None
        self.queue = None
        self._card = None

        self.display_loop = DisplayLoop('/tmp/screen')
        self.ticket_reader = TicketReader('/tmp/bar', self.new_payable)
        self.card_reader = CardReader('/tmp/card', self.new_payable, self.new_operator)

    def _tariff_updater(self):
        while True:
            self.tariffs_updated.emit(self.db.get_tariffs())
            sleep(60)

    def _async_processor(self):
        hub = get_hub()
        while True:
            hub.wait(self.async)

    def _loop(self):
        self.async = get_hub().loop.async()
        self.async.start(lambda: None)

        self.queue = Queue()
        self.db = DB(notify=lambda title, msg: self.notify.emit(title, msg))

        spawn(self._async_processor)
        spawn(self.ticket_reader, self.db)
        spawn(self.card_reader, self.db)
        spawn(self.display_loop)

        session = self.db.local.session()
        if session is not None:
            sn, operator, begin, end = session
            print sn, operator, begin, end
            if end is None:
                self.session_begin.emit(sn, operator.decode('utf8', errors='replace'))

        while True:
            action = self.queue.get()

            if action is not None:
                if callable(action):
                    action()
            else:
                #[greenlet.kill() for greenlet in greenlets]
                break

        print 'reader loop completed'

    def start(self):
        self.thread.start()

    @staticmethod
    def barcode_replace(match):
        bar = match.group('bar')
        result = ('\n\x1ba\x31\x1dw\x02\x1d\x68\x70\x1dk\x48'
                  + chr(len(bar)) + bar + bar + '\n\x1ba\x30')
        return result

    BARCODE_REPLACE_REGEX = re.compile(r'<<(?P<bar>\d+)>>')

    @async
    def to_printer(self, message):
        printer = SafeSocket('/tmp/printer')
        message = message.encode('cp1251', errors='replace')
        message = message.replace('<b>', '\x1d!\x01')
        message = message.replace('</b>', '\x1d!\x00')
        message = message.replace('<s>', '\x1d!\x21')
        message = message.replace('</s>', '\x1d!\x00')
        message = message.replace('<c>', '\x1ba\x31')
        message = message.replace('</c>\n', '\n\x1ba\x30')
        message = message.replace('</c>', '\x1ba\x30')
        message = message.replace('<hr />', '-'*48)
        message = re.sub(self.BARCODE_REPLACE_REGEX, self.barcode_replace, message)
        message += '\n'*6 + '\x1d\x56\x01'
        while message:
            printer.send(message[:256])
            sleep(0.5)
            message = message[256:]

    @async
    def handle_bar(self, bar):
        self.ticket_reader.handle_bar(bar, self.db)

    @async
    def update_tariffs(self):
        self.tariffs_updated.emit(self.db.get_tariffs())

    @async
    def pay(self, payment):
        try:
            payment.execute(self.db)
            self.to_printer(payment.check(self.db))
        finally:
            self.payment_processed.emit()

    @async
    def display(self, message):
        self.display_loop.queue.put(message)

    @async
    def begin_session(self, card):
        self.db.local.session_begin(card)
        self.session_begin.emit(card.sn, card.fio)

    @async
    def end_session(self):
        self.db.local.session_end()
        self.session_end.emit()

    @async
    def generate_report(self):
        print 'generate_report'
        self.report.emit(Report(self.db))

    @async
    def stop(self):
        self.queue.put(None)


class Payments(QWidget):
    new_payment = pyqtSignal()
    session_begin = pyqtSignal(str)
    session_end = pyqtSignal()
    session_dialog = pyqtSignal(QObject)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.tariffs = None
        self.payment = None
        self.payable = None
        self.session = None

        self.notifier = QSystemTrayIcon(QIcon('arrow-up-icon.png'), self)
        self.notifier.show()

        self.ui = uic.loadUiType('payments.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.ui.keyboard.clicked.connect(self.manual_ticket_input)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

        self.ui.tariffs.setSource(QUrl('view.qml'))
        self.ui.tariffs.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        self.ui.tariffs.rootObject().new_payment.connect(self.handle_payment)
        self.ui.tariffs.rootObject().set_message(_('Waiting for operator card...'))

        self.session_dialog.connect(self.handle_session_dialog)

        self.reader = Reader(self)
        self.reader.notify.connect(lambda title, msg: self.notifier.showMessage(title, msg))
        self.reader.session_begin.connect(self.begin_session)
        self.reader.session_end.connect(self.end_session)
        self.end_session()
        self.reader.start()

    def localize(self):
        self.ui.pay.setText(_('Pay'))
        self.ui.cancel.setText(_('Cancel'))

    def begin_session(self, sn, fio):
        print 'begin_session', sn
        self.session = sn
        self.session_begin.emit(fio)

        self.reader.new_operator.connect(self.handle_operator)
        self.reader.tariffs_updated.connect(self.update_tariffs)
        self.reader.update_tariffs()

    def end_session(self):
        print 'end_session'
        try:
            self.reader.new_payable.disconnect(self.handle_payable)
        except TypeError:  # .disconnect raises TypeError when given signal is not connected
            pass

        self.session = None
        self.session_end.emit()

        self.reader.new_operator.connect(self.handle_operator)
        self.ui.progress.setVisible(False)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.update_tariffs(None)

    def handle_session_dialog(self, card):
        if self.session is None and card.type == Card.CASHIER:
            login_dialog = LoginDialog(card, parent=self)
            if login_dialog.exec_() == QDialog.Accepted:
                return self.reader.begin_session(card)
        elif self.session == card.sn or card.type == Card.ADMIN:
            login_dialog = LogoffDialog(card, self.reader)
            if login_dialog.exec_() == QDialog.Accepted:
                return self.reader.end_session()
        self.reader.new_operator.connect(self.handle_operator)

    @pyqtSlot(QObject)
    def handle_operator(self, card):
        print 'operator', card
        self.reader.new_operator.disconnect(self.handle_operator)
        self.session_dialog.emit(card)

    def manual_ticket_input(self):
        self.reader.new_payable.disconnect(self.handle_payable)
        ticket_input = TicketInput()
        if ticket_input.exec_() == QDialog.Accepted:
            self.reader.handle_bar(ticket_input.bar)
        self.reader.new_payable.connect(self.handle_payable)

    def update_tariffs(self, tariffs):
        if self.tariffs is None and tariffs is not None:
            self.tariffs = tariffs
            self.ready_to_accept()
        else:
            self.tariffs = tariffs
            self.ui.tariffs.rootObject().set_tariffs_with_payable(self.tariffs, self.payable)

    def ready_to_accept(self):
        print 'ready_to_accept'
        if self.payable:
            self.payable.payments = None
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(True)

        self.payable = OncePayable()
        self.ui.tariffs.rootObject().set_tariffs_with_payable(self.tariffs, self.payable)
        self.reader.new_payable.connect(self.handle_payable)

    def ready_to_pay(self):
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    @pyqtSlot(QObject, list)
    def handle_payable(self, payable, tariffs):
        try:
            self.reader.new_payable.disconnect(self.handle_payable)
        except TypeError:  # .disconnect raises TypeError when given signal is not connected
            pass

        self.new_payment.emit()

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
                self.reader.display(payment.vfcd_explanation())
            else:
                self.reader.display(None)
        else:
            self.reader.display(None)
            self.ui.pay.setEnabled(False)

    def cancel(self):
        self.ready_to_accept()

    def pay(self):
        self.reader.payment_processed.connect(self.payment_completed)
        self.reader.pay(self.payment)
        self.ui.pay.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.ui.tariffs.setEnabled(False)
        self.ui.progress.setVisible(True)

    @pyqtSlot()
    def payment_completed(self):
        self.payment = None
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect(self.payment_completed)
        self.notifier.showMessage(_('Payment'), _('Payment has been successful'))
        self.ui.tariffs.setEnabled(True)
        self.ready_to_accept()

    def stop_reader(self):
        self.reader.stop()


if __name__ == '__main__':
    import doctest
    doctest.testmod()