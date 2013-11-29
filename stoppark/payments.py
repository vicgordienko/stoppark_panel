# -*- coding: utf-8 -*-
import re
from threading import Thread
from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, QUrl
from PyQt4.QtGui import QWidget, QIcon, QSystemTrayIcon, QDialog
from PyQt4.QtDeclarative import QDeclarativeView
from keyboard import TicketInput
from gevent import socket, spawn, sleep, get_hub
from gevent.queue import Queue
from db import DB, Ticket
from datetime import datetime


class SafeSocket(object):
    def __init__(self, peer):
        self.sock = None
        self.peer = peer
        self.reconnect()

    def reconnect(self):
        print 'safe_recv auto reconnect started'
        if self.sock is not None:
            self.sock.close()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        while True:
            print 'reconnect iteration'
            try:
                self.sock.connect(self.peer)
                break
            except socket.error:
                sleep(2)
                continue

    def recv(self, *args):
        while True:
            try:
                data = self.sock.recv(*args)
                if data == '':
                    self.reconnect()
                else:
                    return data
            except socket.error:
                self.reconnect()

    def send(self, *args):
        while True:
            try:
                return self.sock.send(*args)
            except socket.error:
                self.reconnect()


class Reader(QObject):
    new_payable = pyqtSignal(Ticket, list)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)
    notify = pyqtSignal(str, str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.async = None
        self.db = None
        self.queue = None
        self.display_queue = None
        self._ticket = None
        self._card = None

    def _ticket_loop(self):
        bar_regex = re.compile(r'(;(\d+)\?\r\n)')
        sock = SafeSocket('/tmp/bar')
        buf = ''
        while True:
            buf += sock.recv(128)
            print 'ticket_buf', buf

            last_index = 0
            for match in bar_regex.finditer(buf):
                last_index = match.span()[1]
                bar = match.group(2)
                if len(bar) < 18:
                    continue

                self._handle_bar(bar)

            buf = buf[last_index:]

    def _handle_bar(self, bar):
        print '_handle_bar', bar
        self._ticket = self.db.get_ticket(bar)
        if self._ticket is None:
            print 'registering ticket'
            if Ticket.register(self.db, str(bar)):
                self._ticket = self.db.get_ticket(bar)
        if self._ticket:
            self.new_payable.emit(self._ticket, self.db.get_tariffs())

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
            self.new_payable.emit(self._card, self.db.get_tariffs())

    def _display_time_loop(self, sock):
        while True:
            now = datetime.now()
            self._display(sock, [u' '*6 + u'%s' % (now.strftime('%x'),), u' '*6 + u'%s' % (now.strftime('%X'),)])
            sleep(1)

    def _display_loop(self):
        self.display_queue = Queue()
        sock = SafeSocket('/tmp/screen')
        # '\x02\x05\x53\x3c\x03' set russian character set, optional for previously configured display
        sock.send('\x1b\x40' '\x02\x05\x53\x3c\x03' '\x0c')  # initialize display and clear screen
        time_loop = spawn(self._display_time_loop, sock)
        while True:
            messages = self.display_queue.get()
            if messages is None:
                if time_loop is None:
                    time_loop = spawn(self._display_time_loop, sock)
            else:
                if time_loop is not None:
                    time_loop.kill()
                    time_loop = None
                self._display(sock, messages)

    @staticmethod
    def _display(sock, messages):
        messages = [message.encode('cp866') for message in messages]
        # set cursor at given position and send each message
        [sock.send('\x1b\x6c\x01' + chr(i+1) + message + ' '*(20 - len(message))) for i, message in enumerate(messages)]

    def _process_payment(self, payment):
        try:
            payment.execute(self.db)
        finally:
            self.payment_processed.emit()

    def _tariff_updater(self):
        while True:
            self.tariffs_updated.emit(self.db.get_tariffs())
            sleep(60)

    def _update_tariffs(self):
        self.tariffs_updated.emit(self.db.get_tariffs())

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
        spawn(self._ticket_loop)
        spawn(self._card_loop)
        spawn(self._display_loop)

        self._update_tariffs()

        while True:
            action = self.queue.get()

            if action is not None:
                if callable(action):
                    action()
            else:
                print 'got None'
                #[greenlet.kill() for greenlet in greenlets]
                break

        print 'reader loop completed'

    def async(method):
        """async decorator that wraps up self.async.send() call during async operations"""
        def async_wrapper(self, *args, **kw):
            ret = method(self, *args, **kw)
            self.async.send()
            return ret
        return async_wrapper

    def start(self):
        self.thread.start()

    @async
    def handle_bar(self, bar):
        self.queue.put(lambda: self._handle_bar(bar))

    @async
    def update_tariffs(self):
        self.queue.put(lambda: self._update_tariffs())

    @async
    def pay(self, payment):
        self.queue.put(lambda: self._process_payment(payment))

    @async
    def display(self, message):
        self.display_queue.put(message)

    @async
    def stop(self):
        self.queue.put(None)


class Payments(QWidget):
    new_payment = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.tariffs = None
        self.payment = None
        self.payable = None

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
        self.reader.new_payable.disconnect()
        ticket_input = TicketInput()
        if ticket_input.exec_() == QDialog.Accepted:
            self.reader.handle_bar(ticket_input.bar)
        self.reader.new_payable.connect(self.handle_payable)

    def update_tariffs(self, tariffs):
        if self.tariffs is None:
            self.ready_to_accept()
        self.tariffs = tariffs
        self.ui.tariffs.rootObject().set_tariffs(self.tariffs)

    def ready_to_accept(self):
        if self.payable:
            self.payable.payments = None
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(False)
        self.ui.keyboard.setEnabled(True)

        self.payable = None
        self.ui.tariffs.rootObject().set_payable(self.payable)
        self.reader.new_payable.connect(self.handle_payable)

    def ready_to_pay(self):
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    def handle_payable(self, payable, tariffs):
        self.reader.new_payable.disconnect()
        self.new_payment.emit()

        self.tariffs = tariffs
        self.ui.tariffs.rootObject().set_tariffs(tariffs)

        self.payable = payable
        self.ui.cancel.setEnabled(True)
        self.ui.keyboard.setEnabled(False)

        self.ui.tariffs.rootObject().set_payable(self.payable)

    def handle_payment(self, payment):
        print 'handle_payment'
        payment = payment.toPyObject()
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
        self.payment = None
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect(self.payment_completed)
        self.notifier.showMessage(u'Оплата', u'Оплата выполнена успешно')
        self.ui.tariffs.setEnabled(True)
        self.ready_to_accept()

    def stop_reader(self):
        self.reader.stop()

if __name__ == '__main__':
    print