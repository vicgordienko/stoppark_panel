# coding=utf-8
from PyQt4.QtCore import pyqtSignal, QObject
from gevent import socket
from datetime import datetime, date
from time import clock as measurement, mktime
import u2py.config
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
    """

    def __init__(self, filename=None):
        if filename is None:
            filename = u2py.config.db_filename
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.executescript(LocalDB.script)
        self.conn.row_factory = sqlite3.Row
        self.conn.text_factory = str

    def query(self, q, *args):
        cursor = self.conn.execute(q, *args)
        return [row for row in cursor]

    def update_terminals(self, terminals):
        self.conn.executescript('''
        create table terminal_remote (
            id integer primary key,
            title text
        );''')
        self.conn.executemany('insert into terminal_remote values(?,?)', terminals)
        self.conn.executescript('''
        delete from terminal where id not in (select id from terminal_remote);
        insert into terminal(id,title) select id,title from terminal_remote where id not in (select id from terminal);
        update terminal set title = (select title from terminal_remote where id = terminal.id);
        drop table terminal_remote;
        ''')
        self.conn.commit()

    def get_terminals_id_by_option(self, option):
        return [int(row[0]) for row in self.query('select id from terminal where option = "%s"' % (option,))]

    def get_terminals(self):
        return self.query('select id,title from terminal where display = 1')

    def update_tariffs(self, tariffs):
        self.conn.executescript('delete from tariffs')
        self.conn.executemany('insert into tariffs values(?,?,?,?,?,?,?,?)', tariffs)
        self.conn.commit()

    def get_tariff_by_id(self, tariff_id):
        ret = self.query('select * from tariffs where id = ?', (tariff_id,))
        if ret:
            return ret[0]

    def get_tariffs(self):
        return self.query('select * from tariffs')


class DB(QObject):
    free_places_update = pyqtSignal(int)

    DATETIME_FORMAT = '%y-%m-%d %H:%M:%S'

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
    def query(self, q):
        try:
            s = socket.create_connection(self.addr, timeout=5)
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
        return self.local.get_tariffs()

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
        now = datetime.now().strftime(self.DATETIME_FORMAT)

        args = (event_name, now, addr, reason, self.get_free_places())
        return self.query('insert into events values("Event",NULL,"%s","%s",%i,"","%s",%i,"","")' % args)

    def generate_pass_event(self, addr, inside, sn=None):
        direction_name = 'внутрь' if inside else 'наружу'
        now = datetime.now().strftime(self.DATETIME_FORMAT)
        args = (now, addr, direction_name, sn if sn else '')

        return self.query('insert into events values("Event",NULL,"проезд","%s",%i,"%s","",(select placefree from gstatus),"%s","")' % args)

    def get_config_strings(self):
        ret = self.query('select userstr1,userstr2,userstr3,userstr4,userstr5,userstr6,userstr7,userstr8 from config')
        if ret:
            self._strings = ret[0]
        return self._strings


class TicketPayment(object):
    def __init__(self, ticket, tariff):
        self.ticket = ticket
        self.tariff = tariff

        self.now = datetime.now()

        self.timedelta = self.now - self.ticket.time_in()
        self.minutes = self.timedelta.total_seconds() / 60
        self.price = self.minutes * 200

    def explanation(self):
        return u'''
        Время, проведенное на парковке: %i мин.\n
        Стоимость: %i грн.
        ''' % (self.minutes, self.price)

    def execute(self, db):
        args = (self.tariff, self.price, self.now.strftime(db.DATETIME_FORMAT), Ticket.PAID)
        return db.query('update ticket set typetarif=%i, summ=%i, timeout="%s", status = status & %i' % args)


class Ticket(object):
    IN = 1
    PAID = 5
    OUT = 15

    @staticmethod
    def remove(db, bar):
        return db.query('delete from ticket where bar="%s"' % (bar,))

    @staticmethod
    def create(response):
        try:
            fields = response[0]
            assert(len(fields) >= 12)
            return Ticket(fields)
        except (TypeError, AssertionError):
            return False

    @staticmethod
    def parse_bar(bar):
        return datetime.strptime(str(datetime.now().year) + bar[:10], '%Y%m%d%H%M%S')

    @staticmethod
    def register(db, bar):
        query = 'insert into ticket values("%s", NULL, "%s", NULL, NULL, NULL, NULL, "%s", NULL, NULL, NULL, 1)'
        args = ("Ticket", bar, Ticket.parse_bar(bar).strftime(DB.DATETIME_FORMAT))
        return db.query(query % args) is None

    def pay(self, tariff):
        return TicketPayment(self, tariff)

    def pay_excess(self, tariff):
        pass

    def __init__(self, fields):
        self.fields = fields

        self.id = fields[1]
        self.bar = fields[2]
        self.tariff_type = fields[3]
        self.tariff_price = fields[4]
        self.tariff_summ = fields[5]
        self.tariff_summ_excess = fields[6]
        self.time_in = fields[7]
        self.time_paid = fields[8]
        self.time_count = fields[9]
        self.time_excess_paid = fields[10]
        self.status = fields[11]

    def time_in(self):
        return datetime.strptime(self.fields[7], DB.DATETIME_FORMAT)

    def check(self):
        status = int(self.fields[11])
        if status == self.IN:
            return False

        if status == self.PAID:
            time_paid, time_paid2 = (
                mktime(datetime.strptime(self.fields[8], DB.DATETIME_FORMAT).timetuple()),
                mktime(datetime.strptime(self.fields[10], DB.DATETIME_FORMAT).timetuple())
            )

            now = mktime(datetime.now().timetuple())
            if now - time_paid < 15*60 or now - time_paid2 < 15*60:
                return True


class Card(object):
    STAFF = 0
    ONCE = 1
    CLIENT = 2
    CASHIER = 3
    ADMIN = 4

    ALLOWED_TYPE = [ONCE, CLIENT]

    ALLOWED = 1
    LOST = 2
    EXPIRED = 3
    DENIED = 4
    OUTSIDE = 5
    INSIDE = 6

    ALLOWED_STATUS = [
        [ALLOWED, OUTSIDE],  # 0, directed inside
        [ALLOWED, INSIDE]    # 1, directed outside
    ]

    @staticmethod
    def create(response):
        try:
            fields = response[0]
            assert(len(fields) >= 19)
            return Card(fields)
        except (TypeError, AssertionError):
            return False

    def __init__(self, fields):
        self.fields = fields

        self.id = fields[1]
        self.type = fields[2]
        self._sn = fields[3]
        self.date_reg = fields[4]
        self.date_end = fields[5]
        self.date_in = fields[6]
        self.date_out = fields[7]
        self.drive_name = fields[8]
        self.drive_sname = fields[9]
        self.drive_fname = fields[10]
        self.drive_phone = fields[11]
        self.number = fields[12]
        self.model = fields[13]
        self.color = fields[14]
        self.status = fields[15]
        self.tariff_type = fields[16]
        self.tariff_price = fields[17]
        self.tariff_sum = fields[18]

    def check(self, direction):
        if int(self.fields[15]) not in self.ALLOWED_STATUS[direction]:
            return False
        if int(self.fields[2]) not in self.ALLOWED_TYPE:
            return False

        begin, end = (
            datetime.strptime(self.fields[4], '%y-%m-%d').date(),
            datetime.strptime(self.fields[5], '%y-%m-%d').date()
        )
        return begin <= date.today() <= end

    def fio(self):
        return ('%s %s %s' % (self.fields[10], self.fields[8], self.fields[9])).decode('utf8')

    def sn(self):
        return self.fields[3]

    def moved(self, db, addr, inside):
        status = Card.INSIDE if inside else Card.OUTSIDE
        db.query('update card set status = %i where cardid = \"%s\"' % (status, self.sn()))
        return db.generate_pass_event(addr, inside, self.sn())


if __name__ == '__main__':
    d = DB()
    print d.get_tariffs()
