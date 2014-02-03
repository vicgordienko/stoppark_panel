import re
from PyQt4.QtCore import QObject, pyqtSignal
from threading import Thread
from gevent import spawn, sleep, get_hub
from gevent.queue import Queue
from safe_socket import SafeSocket
from report import Report
from db import DB, Ticket, Card
from datetime import datetime
from config import DISPLAY_PEER, TICKET_PEER, CARD_PEER, PRINTER_PEER
from i18n import language
_ = language.ugettext


class TicketReader(object):
    def __init__(self, peer, new_payable):
        self.regex = re.compile(r'(;(?P<bar>\d+)\?(\r\n)?)')
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
        elif self.card is not None:
            self.card = Card.config_card()
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


class Executor(QObject):
    new_payable = pyqtSignal(QObject, list)
    new_operator = pyqtSignal(QObject)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)
    terminals_notification = pyqtSignal(dict)
    notify = pyqtSignal(str, str)
    session_begin = pyqtSignal(str, str, str)
    session_end = pyqtSignal()
    report = pyqtSignal(object)
    option_notification = pyqtSignal(str, str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.async = None
        self.db = None
        self.queue = None
        self._card = None

        self.display_loop = DisplayLoop(DISPLAY_PEER)
        self.ticket_reader = TicketReader(TICKET_PEER, self.new_payable)
        self.card_reader = CardReader(CARD_PEER, self.new_payable, self.new_operator)

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
        self.db = DB(notify=lambda title, msg: self.notify.emit(title, msg), initialize_local_db=True)

        spawn(self._async_processor)
        spawn(self.ticket_reader, self.db)
        spawn(self.card_reader, self.db)
        spawn(self.display_loop)

        session = self.db.local.session()
        print session
        if session is not None:
            sn, operator, access, begin, end = session
            if end is None:
                self.emit_session_begin(sn, operator.decode('utf8', errors='replace'), access)

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
        printer = SafeSocket(PRINTER_PEER, reconnect_interval=0.1, attempt_limit=2)
        if not printer.connected:
            print 'Cannot print'
            return
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
        printer.send(message)
        # while message:
        #     printer.send(message[:256])
        #     sleep(0.5)
        #     message = message[256:]

    @async
    def handle_bar(self, bar):
        self.ticket_reader.handle_bar(bar, self.db)

    @async
    def update_tariffs(self):
        self.tariffs_updated.emit(self.db.get_tariffs())

    def emit_terminals_notification(self):
        self.terminals_notification.emit(self.db.get_terminals())

    @async
    def notify_terminals(self):
        self.emit_terminals_notification()

    @async
    def update_terminals(self):
        self.db.update_terminals()
        self.emit_terminals_notification()

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

    def emit_session_begin(self, sn, fio, access):
        self.session_begin.emit(sn, fio, access)
        self.emit_all_options()

    @async
    def begin_session(self, card):
        self.db.update_config()
        self.db.local.session_begin(card)
        self.emit_session_begin(card.sn, card.fio, card.access)

    @async
    def end_session(self):
        print 'end_session'
        self.db.update_config()
        self.db.local.session_end()
        self.session_end.emit()

    @async
    def generate_report(self):
        print 'generate_report'
        self.report.emit(Report(self.db))

    @async
    def set_option(self, key, value):
        self.db.local.set_option(str(key), str(value))

    def emit_option(self, key):
        self.option_notification.emit(key, self.db.local.option(key))

    def emit_all_options(self):
        for key, value in self.db.local.all_options():
            self.option_notification.emit(key, value)

    @async
    def notify_option(self, key):
        self.emit_option(key)

    @async
    def notify_all_options(self):
        self.emit_all_options()

    @async
    def stop(self):
        self.queue.put(None)
