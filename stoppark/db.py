# coding=utf-8
from PyQt4.QtCore import pyqtSignal, QObject
from gevent import socket
from datetime import datetime
from time import clock as measurement
from ticket import Ticket
from card import Card
from tariff import Tariff
from config import db_filename, DATETIME_FORMAT
import sqlite3
from i18n import language
_ = language.ugettext


def measure(f):
    def wrapper(*args, **kw):
        begin = measurement()
        ret = f(*args, **kw)
        elapsed = measurement() - begin
        print elapsed, args, ret
        return ret

    return wrapper


class LocalDB(object):
    script = """
    create table if not exists terminal (
        id integer primary key,
        title text,
        display integer default 1,
        option text default ''
    );
    create table if not exists tariffs (
        id integer primary key,
        name text,
        type integer,
        interval integer,
        cost integer,
        zerotime text,
        maxperday text,
        note text
    );
    create table if not exists payment (
        id integer primary key,
        payment text,
        type integer,
        kassa integer,
        operator text,
        DTime text,
        TalonID text,
        Status integer,
        TarifType integer,
        Tarif integer,
        TarifKol integer,
        DTIn text,
        DTOut text,
        Summa integer
    );
    create table if not exists events (
        event text not null default "Event",
        id integer primary key,
        EventName text,
        DateTime text,
        Terminal integer,
        Direction text,
        Reason text,
        FreePlaces integer,
        Card text,
        GosNom text
    );
    create table if not exists session (
        id integer primary key default (null),
        operator text,
        begin text default (datetime(current_timestamp, 'localtime')),
        end text default (null)
    );
    """

    def __init__(self, filename=None):
        if filename is None:
            filename = db_filename
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
        self.conn.text_factory = str
        with self.conn as c:
            c.executescript(LocalDB.script)

    def session_begin(self, operator):
        with self.conn as c:
            c.execute('insert into session(operator) values(?)', operator)

    def session(self, session_id=None):
        session_id = session_id if session_id is not None else '(select max(id) from session)'
        begin, end = self.query('select begin,end from session where id=%s' % (session_id,))
        return begin, end

    def session_end(self):
        with self.conn as c:
            c.execute('delete from payment')
            c.execute('delete from events')
            c.execute('update session set end=datetime(current_timestamp, "localtime") '
                      'where id=(select max(id) from session)')

    def connection(self):
        return self.conn

    def query(self, q, *args):
        cursor = self.conn.execute(q, *args)
        return [row for row in cursor]

    def update_terminals(self, terminals):
        with self.conn as c:
            c.executescript('create table terminal_remote (id integer primary key, title text);')
            c.executemany('insert into terminal_remote values(?,?)', terminals)
            c.executescript('''delete from terminal where id not in (select id from terminal_remote);
insert into terminal(id,title) select id,title from terminal_remote where id not in (select id from terminal);
update terminal set title = (select title from terminal_remote where id = terminal.id);
drop table terminal_remote;''')

    def get_terminals_id_by_option(self, option):
        return [int(row[0]) for row in self.query('select id from terminal where option = "%s"' % (option,))]

    def get_terminals(self):
        return self.query('select id,title from terminal where display = 1')

    def update_tariffs(self, tariffs):
        try:
            with self.conn as c:
                c.executescript('delete from tariffs')
                c.executemany('insert into tariffs values(?,?,?,?,?,?,?,?)', tariffs)
        except sqlite3.OperationalError as e:
            print 'LOCAL DB ERROR', e.__class__.__name__, e

    def get_tariff_by_id(self, tariff_id):
        ret = self.query('select * from tariffs where id = ?', (tariff_id,))
        if ret:
            return ret[0]

    def get_tariffs(self):
        return self.query('select * from tariffs')


class DB(QObject):
    free_places_update = pyqtSignal(int)

    def __init__(self, host='10.0.2.247', port=101, notify=None, parent=None):
        QObject.__init__(self, parent)

        self.addr = (host, port)
        self._free_places = (100, None)
        self._strings = [
            'ТОВ "КАРД-СIСТЕМС"',
            'м. Київ',
            'проспект перемоги, 123',
            '(+380 44) 284 0888',
            'ЗРАЗОК',
            'УВАГА! Талон не згинати',
            'ЗА ВТРАТУ ТАЛОНУ ШТРАФ',
            '',
        ]
        self.notify = notify
        self.local = LocalDB()

    @measure
    def query(self, q, local=False):
        if local:
            with self.local.connection() as c:
                c.execute(q)

        try:
            s = socket.create_connection(self.addr, timeout=20)
            s.send(q)
            answer = s.recv(1024)
        except socket.error as e:
            print e.__class__.__name__, e
            if self.notify:
                #self.notify(u'Ошибка БД', u'Нет связи с удалённой базой данных')
                self.notify(_("Database Error"), q.decode('utf8'))
            return False

        if answer == 'FAIL':
            raise Exception('FAIL on query: %s' % (q,))
        if answer == 'NONE':
            return None

        return [line.split('|') for line in answer.split('\n')]

    def get_card(self, sn):
        return Card.create(self.query('select * from card where cardid = "%s"' % (sn,)))

    def get_ticket(self, bar):
        return Ticket.create(self.query('select * from ticket where bar = "%s"' % (bar,)))

    def get_terminals(self):
        ret = self.query('select terminal_id,title from terminal')
        if ret:
            self.local.update_terminals(ret)
        return dict((int(key), value.decode('utf8')) for key, value in self.local.get_terminals())

    def get_tariffs(self):
        ret = self.query('select * from tariff')
        if ret:
            self.local.update_tariffs(ret)
        return [Tariff.create(t) for t in self.local.get_tariffs()]

    def update_free_places(self, diff):
        if self._free_places is not None:
            free, timestamp = self._free_places
            self._free_places = (free + diff, timestamp)
            self.free_places_update.emit(self._free_places[0])
        return self.query('update gstatus set placefree = placefree + %i' % (diff,))

    def get_free_places(self):
        now = measurement()
        if self._free_places[1] is None or self._free_places[1] - now > 5:
            answer = self.query('select placefree from gstatus')
            try:
                self._free_places = (int(answer[0][0]), now)
                self.free_places_update.emit(self._free_places[0])
            except (IndexError, KeyError, ValueError, TypeError) as e:
                print 'Incorrect response:', e.__class__.__name__, e
        return self._free_places[0]

    reasons = {1: 'вручную', 5: 'автоматически'}

    def generate_open_event(self, addr, reason, command):
        if not command % 2:
            return True

        reason = self.reasons.get(reason, '')
        event_name = 'открытие' if command % 2 else ''
        now = datetime.now().strftime(DATETIME_FORMAT)

        args = (event_name, now, addr, reason, self.get_free_places())
        return self.query('insert into events values("Event",NULL,"%s","%s",%i,"","%s",%i,"","")' % args, local=True)

    PASS_QUERY = '''insert into events
values("Event",NULL,"проезд","%s",%i,"%s","",(select placefree from gstatus),"%s","")'''

    def generate_pass_event(self, addr, inside, sn=None):
        direction_name = 'внутрь' if inside else 'наружу'
        now = datetime.now().strftime(DATETIME_FORMAT)
        args = (now, addr, direction_name, sn if sn else '')

        return self.query(self.PASS_QUERY % args, local=True)

    def get_config_strings(self):
        ret = self.query('select userstr1,userstr2,userstr3,userstr4,userstr5,userstr6,userstr7,userstr8 from config')
        if ret:
            self._strings = ret[0]
        return self._strings

    PAYMENT_QUERY = 'insert into payment values(NULL,"%s",%i,%i,"%s","%s","%s",%i,%i,%i*100,%i,"%s","%s",%i*100)'

    def generate_payment(self, ticket_payment=None, card_payment=None, once_payment=None):
        if ticket_payment is None and card_payment is None and once_payment is None:
            print 'No payment to generate.'
            return None

        if ticket_payment:
            payment_args = ("Talon payment", ticket_payment.tariff.id, 0,
                            'Кассир', datetime.now().strftime(DATETIME_FORMAT),
                            ticket_payment.ticket.bar, Ticket.PAID, ticket_payment.tariff.id,
                            ticket_payment.result.cost, ticket_payment.result.units,
                            ticket_payment.ticket.time_in.strftime(DATETIME_FORMAT),
                            ticket_payment.now.strftime(DATETIME_FORMAT),
                            ticket_payment.result.price)
            return self.query(self.PAYMENT_QUERY % payment_args, local=True) is None

        if once_payment:
            now = datetime.now().strftime(DATETIME_FORMAT)
            payment_args = ('Single payment', once_payment.tariff.id, 0,
                            'Кассир', now,
                            '', 0, once_payment.tariff.id,
                            once_payment.price, 1,
                            now, now, once_payment.price)

            return self.query(self.PAYMENT_QUERY % payment_args, local=True) is None

        if card_payment:
            now = datetime.now().strftime(DATETIME_FORMAT)
            payment_args = ('Card payment', card_payment.tariff.id, 0,
                            'Кассир', now,
                            card_payment.card.sn, Ticket.PAID, card_payment.tariff.id,
                            card_payment.result.cost, card_payment.result.units,
                            card_payment.result.begin, card_payment.result.end,
                            card_payment.result.price)
            return self.query(self.PAYMENT_QUERY % payment_args, local=True) is None


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    d = DB()
    #d.query('delete from ticket')
    #d.query('update ticket set status=5 where bar = "102514265300000029"')
    #d.query('delete from ticket where bar >= "102516091500000030"')
    #d.query('update ticket set timeout="13-10-28 11:40:00" where bar = "102516091500000030"')
    #d.query('update ticket set summdopl = summdopl+1 where bar = "102516091500000030"')
    #d.query('select * from ticket where  bar = "102516091500000030" ')
    #d.query('select * from tariff where id = 2')
    #tariff = d.get_tariffs()[0]
    #t = d.get_ticket('102514265300000029')
    #print t.pay(tariff).explanation()