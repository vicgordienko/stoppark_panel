# coding=utf-8
from PyQt4.QtCore import pyqtSignal, pyqtSlot, pyqtProperty, QObject
from gevent import socket
from datetime import datetime, date, timedelta
from time import clock as measurement, mktime
import u2py.config
import sqlite3
from math import ceil, floor
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
        try:
            self.conn.executescript('delete from tariffs')
            self.conn.executemany('insert into tariffs values(?,?,?,?,?,?,?,?)', tariffs)
            self.conn.commit()
        except sqlite3.OperationalError as e:
            print e.__class__.__name__, e

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


class TicketPayment(QObject):
    def __init__(self, ticket, tariff):
        QObject.__init__(self)#, parent=ticket)

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.ticket = ticket
        self.tariff = tariff

        self.now = datetime.now()
        self.result = tariff.calc(self.ticket.time_in, self.now)

    def __del__(self):
        print '~TicketPayment'

    @pyqtProperty(bool)
    def enabled(self):
        return self._enabled

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return u'Невозможно оплатить по этому тарифу'
        return u'''
Оплата по талону %s
Время вьезда: %s
%s
''' % (self.ticket.bar, self.ticket.time_in.strftime(DB.DATETIME_FORMAT), self.result)

    QUERY = 'update ticket set typetarif=%i, pricetarif=%i * 100, summ=%i * 100, summdopl=0, timeout="%s", status = status | %i where bar="%s"'

    def execute(self, db):
        args = (self.tariff.id, self.tariff.cost, self.result.price,
                self.now.strftime(db.DATETIME_FORMAT), Ticket.PAID, self.ticket.bar)
        return db.query(self.QUERY % args)


class TicketExcessPayment(QObject):
    def __init__(self, ticket, tariff, excess=False):
        QObject.__init__(self, parent=ticket)

        self._enabled = hasattr(tariff, 'calc')
        if not self._enabled:
            return

        self.ticket = ticket
        self.tariff = tariff
        self.excess = excess

        self.now = datetime.now()
        self.base_time = self.ticket.time_excess_paid if self.excess else self.ticket.time_paid
        self.result = tariff.calc(self.base_time, self.now)

    def __del__(self):
        print '~TicketExcessPayment'

    @pyqtProperty(str, constant=True)
    def explanation(self):
        if not self._enabled:
            return u'Невозможно оплатить по этому тарифу'
        return u'''
Доплата по талону %s
Время вьезда: %s
Время последней оплаты: %s
%s''' % (self.ticket.bar, self.ticket.time_in.strftime(DB.DATETIME_FORMAT),
               self.base_time.strftime(DB.DATETIME_FORMAT), self.result)

    QUERY = 'update ticket set summdopl = summdopl + %i * 100, timedopl="%s", status = status | %i where bar = "%s"'

    def execute(self, db):
        args = (self.result.price, self.now.strftime(DB.DATETIME_FORMAT), Ticket.PAID, self.ticket.bar)
        return db.query(self.QUERY % args)


class Ticket(QObject):
    IN = 1
    PAID = 5
    OUT = 15

    EXCESS_INTERVAL = 15*60

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
        try:
            ticket_time = Ticket.parse_bar(bar).strftime(DB.DATETIME_FORMAT)
        except ValueError:
            return None
        args = ("Ticket", bar, ticket_time)
        return db.query(query % args) is None

    def __init__(self, fields):
        QObject.__init__(self)
        self.fields = fields

        self.id = fields[1]
        self._bar = fields[2]
        self.tariff_type = fields[3]
        self.tariff_price = fields[4]
        self.tariff_sum = fields[5]
        self.tariff_sum_excess = fields[6]
        self.time_in = datetime.strptime(fields[7], DB.DATETIME_FORMAT)
        self.time_paid = datetime.strptime(fields[8], DB.DATETIME_FORMAT) if fields[8] != 'None' else None
        self.time_count = datetime.strptime(fields[9], DB.DATETIME_FORMAT) if fields[9] != 'None' else None
        self.time_excess_paid = datetime.strptime(fields[10], DB.DATETIME_FORMAT) if fields[10] != 'None' else None
        self.status = int(fields[11])

    def __del__(self):
        print '~Ticket'

    @pyqtProperty(str)
    def bar(self):
        return self._bar

    @pyqtSlot(QObject, result=QObject)
    def pay(self, tariff):
        if self.status == self.IN:
            return TicketPayment(self, tariff)

        if self.status == self.PAID:
            if self.time_excess_paid:
                if (datetime.now() - self.time_excess_paid).total_seconds() > self.EXCESS_INTERVAL:
                    return TicketExcessPayment(self, tariff, excess=True)
                else:
                    return None

            if self.time_paid:
                if (datetime.now() - self.time_paid).total_seconds() > self.EXCESS_INTERVAL:
                    return TicketExcessPayment(self, tariff)

    def check(self):
        if self.status == self.IN:
            return False

        if self.status == self.PAID:
            time_paid, time_excess_paid = (
                mktime(datetime.strptime(self.time_paid, DB.DATETIME_FORMAT).timetuple()),
                mktime(datetime.strptime(self.time_excess_paid, DB.DATETIME_FORMAT).timetuple())
            )

            now = mktime(datetime.now().timetuple())
            if now - time_paid < self.EXCESS_INTERVAL or now - time_excess_paid < self.EXCESS_INTERVAL:
                return True


class Tariff(QObject):
    HOURLY = 1
    DAILY = 2
    MONTHLY = 3

    DIVISORS = {
        HOURLY: 60*60,
        DAILY: 60*60*24,
        MONTHLY: 60*60*24*30
    }

    FIXED = 1
    DYNAMIC = 2
    ONCE = 3
    PREPAID = 5
    SUBSCRIPTION = 6

    TYPES = {}

    @staticmethod
    def register(identifier):
        def wrapper(cls):
            Tariff.TYPES[identifier] = cls
            return cls
        return wrapper

    @staticmethod
    def create(response):
        try:
            assert(len(response) >= 8)
            return Tariff.TYPES.get(int(response[2]), Tariff)(response)
        except (ValueError, TypeError, AssertionError):
            return False

    def __init__(self, fields):
        QObject.__init__(self)
        self.fields = fields

        self._id = int(fields[0])
        self._title = fields[1].decode('utf8')
        self._type = int(fields[2])
        self._interval = int(fields[3])
        try:
            self.cost = int(fields[4])
        except ValueError:
            self.cost = fields[4].split(' ')
        self.zero_time = [int(i, 10) for i in fields[5].split(':')] if fields[5] != 'None' else None
        self.max_per_day = fields[6]
        self._note = fields[7].decode('utf8')

    def __del__(self):
        print '~Tariff'

    @pyqtProperty(int, constant=True)
    def id(self):
        return self._id

    @pyqtProperty(str, constant=True)
    def title(self):
        return self._title

    @pyqtProperty(int, constant=True)
    def type(self):
        return self._type

    @pyqtProperty(int, constant=True)
    def interval(self):
        return self._interval

    @pyqtProperty(str, constant=True)
    def costInfo(self):
        return str(self.cost) if isinstance(self.cost, int) else ','.join([str(cost) for cost in self.cost[:3]]) + '...'

    @pyqtProperty(str, constant=True)
    def note(self):
        return self._note


class TariffResult(object):
    def __init__(self, delta, units=0, cost=0, max_per_day=None):
        """
        max_per_day parameter should only be present for  tariffs with hour interval.
        It activates minimization algorithm

        """
        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units

        self.price = self.units * cost
        if max_per_day is not None and self.price > max_per_day:
            cost_per_day = min(max_per_day, cost*24)
            self.price = cost_per_day * (self.units / 24)
            self.price += min((self.units % 24)*cost, max_per_day)

    def __str__(self):
        return u"""Единиц оплаты: %f
Стоимость: %i грн.""" % (self.units, self.price)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.price))


@Tariff.register(Tariff.FIXED)
class FixedTariff(Tariff):
    """
    >>> tariff = FixedTariff(['1', 'Час 1 грн.', '1', '1', '1', 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0, 0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1.0, 1.0)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6.0, 6.0)
    >>> tariff = FixedTariff(['1', 'Час 1 грн. X', '1', '2', '1', '09:00', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 4.0, 4.0)
    """

    FREE_TIME = 60*15

    def __init__(self, fields):
        super(FixedTariff, self).__init__(fields)

    def _calc_a(self, begin, end):
        delta = end - begin
        seconds = delta.total_seconds()
        if seconds < self.FREE_TIME:
            return TariffResult(delta)
        units = ceil((seconds - self.FREE_TIME) / Tariff.DIVISORS[self.interval])
        return TariffResult(delta, units, self.cost)

    def calc(self, begin, end):
        if self.interval == Tariff.DAILY and self.zero_time:
            pivot = begin.replace(hour=self.zero_time[0], minute=self.zero_time[1], second=0)
            if pivot < begin:
                pivot += timedelta(days=1)
            if pivot > end:
                return self._calc_a(begin, end)
            unit_diff = 1 if (pivot - begin).total_seconds() > self.FREE_TIME else 0
            result = self._calc_a(pivot, end)
            return TariffResult(end - begin, result.units + unit_diff, self.cost)
        else:
            return self._calc_a(begin, end)


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
        except (ValueError, TypeError, AssertionError):
            return False

    def __init__(self, fields):
        self.fields = fields

        self.id = fields[1]
        self.type = int(fields[2])
        self.sn = fields[3]
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
        self.status = int(fields[15])
        self.tariff_type = fields[16]
        self.tariff_price = fields[17]
        self.tariff_sum = fields[18]

    def check(self, direction):
        if self.status not in self.ALLOWED_STATUS[direction]:
            return False
        if self.type not in self.ALLOWED_TYPE:
            return False

        begin, end = (
            datetime.strptime(self.date_reg, '%y-%m-%d').date(),
            datetime.strptime(self.date_end, '%y-%m-%d').date()
        )
        return begin <= date.today() <= end

    def fio(self):
        return ('%s %s %s' % (self.drive_fname, self.drive_name, self.drive_sname)).decode('utf8')

    def moved(self, db, addr, inside):
        status = Card.INSIDE if inside else Card.OUTSIDE
        db.query('update card set status = %i where cardid = \"%s\"' % (status, self.sn))
        return db.generate_pass_event(addr, inside, self.sn)


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

