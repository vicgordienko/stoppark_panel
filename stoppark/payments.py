# -*- coding: utf-8 -*-
import re
from threading import Thread
from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, QUrl
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


class TicketReader(object):
    def __init__(self, peer, new_payable):
        self.regex = re.compile(r'(;(\d+)\?\r\n)')
        self.peer = peer
        self.new_payable = new_payable
        self.buf = ''
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
        while True:
            self.buf += sock.recv(128)
            print 'ticket_buf', self.buf

            last_index = 0
            for match in self.regex.finditer(self.buf):
                last_index = match.span()[1]
                bar = match.group(2)
                if len(bar) < 18:
                    continue
                self.handle_bar(bar, db)

            self.buf = self.buf[last_index:]


class DisplayLoop(object):
    def __init__(self, peer):
        self.peer = peer
        self.queue = None

    def time_loop(self, sock):
        while True:
            now = datetime.now()
            self.display(sock, [u' '*6 + u'%s' % (now.strftime('%x'),), u' '*6 + u'%s' % (now.strftime('%X'),)])
            sleep(1)

    def __call__(self):
        self.queue = Queue()
        sock = SafeSocket(self.peer)
        # '\x02\x05\x53\x3c\x03' set russian character set, optional for previously configured display
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
        messages = [message.encode('cp866') for message in messages]
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
    session_begin = pyqtSignal(str)
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

    @staticmethod
    def _card_read_loop(sock):
        while True:
            sock.send('n')
            sleep(1)

    def _card_loop(self):
        bar_regex = re.compile(r'(;([A-Z\d]+)\?)')
        sock = SafeSocket('/tmp/card')
        spawn(self._card_read_loop, sock)
        buf = ''
        while True:
            buf += sock.recv(128)
            print 'card_buf', buf

            last_index = 0
            for match in bar_regex.finditer(buf):
                last_index = match.span()[1]
                bar = match.group(2)

                self._handle_card(bar)

            buf = buf[last_index:]

    def _handle_card(self, sn):
        print '_handle_card', sn
        self._card = self.db.get_card(sn)
        if self._card:
            if self._card.type in [Card.CLIENT]:
                self.new_payable.emit(self._card, self.db.get_tariffs())
            if self._card.type in [Card.CASHIER]:
                self.new_operator.emit(self._card)

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
        spawn(self._card_loop)
        spawn(self.display_loop)

        print self.db.local.session()

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

    @async
    def handle_bar(self, bar):
        self._handle_bar(bar)

    @async
    def update_tariffs(self):
        self.tariffs_updated.emit(self.db.get_tariffs())

    @async
    def pay(self, payment):
        try:
            payment.execute(self.db)
        finally:
            self.payment_processed.emit()

    @async
    def display(self, message):
        self.display_loop.queue.put(message)

    @async
    def begin_session(self, card):
        self.db.local.session_begin(card)
        self.session_begin.emit(card.sn)

    @async
    def end_session(self):
        self.db.local.session_end()
        self.session_end.emit()

    @async
    def generate_report(self):
        print 'generate_report'
        self.report.emit(Report(self.db.local))

    @async
    def stop(self):
        self.queue.put(None)


class Payments(QWidget):
    new_payment = pyqtSignal()
    session_started = pyqtSignal(str)
    session_ended = pyqtSignal()

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

        self.reader = Reader(self)
        self.reader.notify.connect(lambda title, msg: self.notifier.showMessage(title, msg))
        self.reader.session_begin.connect(self.session_begin)
        self.reader.session_end.connect(self.session_end)
        self.reader.start()

        self.ui.keyboard.clicked.connect(self.manual_ticket_input)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

        self.ui.tariffs.setSource(QUrl('view.qml'))
        self.ui.tariffs.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        self.ui.tariffs.rootObject().new_payment.connect(self.handle_payment)

        self.session_end()

    def session_begin(self, sn):
        print 'session_start', sn
        self.session = sn
        self.session_started.emit(sn)

        self.reader.new_operator.connect(self.handle_operator)
        self.reader.tariffs_updated.connect(self.update_tariffs)
        self.reader.update_tariffs()

    def session_end(self):
        print 'session_end'
        self.session = None
        self.session_ended.emit()

        self.reader.new_operator.connect(self.handle_operator)
        self.ui.progress.setVisible(False)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.update_tariffs(None)

    def handle_operator(self, card):
        print 'operator', card
        self.reader.new_operator.disconnect(self.handle_operator)
        if self.session is None:
            login_dialog = LoginDialog(card, parent=self)
            if login_dialog.exec_() == QDialog.Accepted:
                return self.reader.begin_session(card)
        elif self.session == card.sn:
            login_dialog = LogoffDialog(card, self.reader)
            if login_dialog.exec_() == QDialog.Accepted:
                return self.reader.end_session()
        self.reader.new_operator.connect(self.handle_operator)

    def manual_ticket_input(self):
        self.reader.new_payable.disconnect(self.handle_payable)
        ticket_input = TicketInput()
        if ticket_input.exec_() == QDialog.Accepted:
            self.reader.handle_bar(ticket_input.bar)
        self.reader.new_payable.connect(self.handle_payable)

    def update_tariffs(self, tariffs):
        if self.tariffs is None and tariffs is not None:
            self.ready_to_accept()
        self.tariffs = tariffs
        self.ui.tariffs.rootObject().set_tariffs(self.tariffs)

    def ready_to_accept(self):
        print 'ready_to_accept'
        if self.payable:
            self.payable.payments = None
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(True)

        self.payable = OncePayable()
        self.ui.tariffs.rootObject().set_payable(self.payable)
        self.reader.new_payable.connect(self.handle_payable)

    def ready_to_pay(self):
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    def handle_payable(self, payable, tariffs):
        self.reader.new_payable.disconnect(self.handle_payable)
        self.new_payment.emit()

        self.tariffs = tariffs
        self.ui.tariffs.rootObject().set_tariffs(tariffs)

        self.payable = payable
        self.ui.cancel.setEnabled(True)
        self.ui.keyboard.setEnabled(False)

        self.ui.tariffs.rootObject().set_payable(self.payable)

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

    def payment_completed(self):
        self.payment = None
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect(self.payment_completed)
        self.notifier.showMessage(u'Оплата', u'Оплата выполнена успешно')
        self.ui.tariffs.setEnabled(True)
        self.ready_to_accept()

    def stop_reader(self):
        self.reader.stop()