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


FREE_PLACES_UPDATE_INTERVAL = 5


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
    create table if not exists gstatus (
        id integer primary key,
        placefree integer
    );
    replace into gstatus(id, placefree) values(0, 100);

    create table if not exists config (
        Config text,
        id integer primary key,
        PlaceNum integer,
        FreeTime integer,
        PayTime text,
        TarifName1 text,
        TarifName2 text,
        TarifName3 text,
        TarifName4 text,
        UserStr1 text,
        UserStr2 text,
        UserStr3 text,
        UserStr4 text,
        UserStr5 text,
        UserStr6 text,
        UserStr7 text,
        UserStr8 text
    );

    create table if not exists session (
        id integer primary key default (null),
        sn text,
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

        if self.query('select count(*) from config')[0][0] == 0:
            with self.conn as c:
                default_strings = _('CARD-SYSTEMS\n'
                                    'Kyiv\n'
                                    'Peremohy ave, 123\n'
                                    '(+380 44) 284 0888\n'
                                    'EXAMPLE\n'
                                    'CAUTION! Do not crumple tickets!\n'
                                    'Ticket loss will be penalized\n'
                                    'EXAMPLE').split(u'\n')
                c.execute('insert into config(id,PlaceNum,FreeTime,'
                          'UserStr1,UserStr2,UserStr3,UserStr4,'
                          'UserStr5,UserStr6,UserStr7,UserStr8)'
                          ' values(null,100,15,?,?,?,?,?,?,?,?)', default_strings)

        self.free_places_update_time = None

    def session_begin(self, card):
        with self.conn as c:
            c.execute('insert into session(sn, operator) values(?,?)', (card.sn, card.fio))

    def session(self, session_id=None):
        session_id = session_id if session_id is not None else '(select max(id) from session)'
        session = self.query('select sn,operator,begin,end from session where id=%s' % (session_id,))
        if session:
            return session[0]

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

    def update_free_places(self, free_places):
        with self.conn as c:
            c.execute('update gstatus set placefree=?', (free_places,))
            self.free_places_update_time = measurement()

    def get_free_places(self):
        if self.free_places_update_time is None:
            return 0, False

        return (self.query('select placefree from gstatus')[0][0],
                measurement() - self.free_places_update_time < FREE_PLACES_UPDATE_INTERVAL)

    def update_terminals(self, terminals):
        with self.conn as c:
            c.executescript('drop table if exists terminal_remote;'
                            'create table terminal_remote (id integer primary key, title text);')
            c.executemany('insert into terminal_remote values(?,?)', terminals)
            c.executescript('delete from terminal where id not in (select id from terminal_remote);'
                            'insert into terminal(id,title) select id,title from terminal_remote '
                            'where id not in (select id from terminal);'
                            'update terminal set title = (select title from terminal_remote where id = terminal.id);'
                            'drop table terminal_remote;')

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

    def update_config(self, config):
        with self.conn as c:
            c.execute('update config set Config=?,id=?,PlaceNum=?,FreeTime=?,PayTime=?,'
                      'TarifName1=?,TarifName2=?,TarifName3=?,TarifName4=?,'
                      'UserStr1=?,UserStr2=?,UserStr3=?,UserStr4=?,'
                      'UserStr5=?,UserStr6=?,UserStr7=?,UserStr8=?', *config)

    def get_config_strings(self):
        return [s.decode('utf8') for s in self.query('select UserStr1,UserStr2,UserStr3,UserStr4,'
                                                     'UserStr5,UserStr6,UserStr7,UserStr8 from config')[0]]

    def get_free_time(self):
        try:
            return int(self.query('select FreeTime from config')[0][0])
        except (ValueError, KeyError):
            return None


class DB(QObject):
    free_places_update = pyqtSignal(int)

    STRINGS_UPDATE_INTERVAL = 60  # seconds

    def __init__(self, host='10.0.2.247', port=101, notify=None, parent=None):
        QObject.__init__(self, parent)

        self.addr = (host, port)
        self.notify = notify
        self.local = LocalDB()

    @measure
    def query(self, q, local=False):
        """
        This is a base function for communication with remote database.
        @param q: str, query to be executed remotely
        @param local: bool, this argument defines whether given query will be duplicated on local database
        @return: None when database returned correct NONE response
                 False when there was an error during database communication or error during query execution
                       Those cases are being explicitly notified using self.notify
                 list of string lists when database reponded with some data
        """
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
                self.notify(_("Database Error"), q.decode('utf8', errors='replace'))
            return False

        if answer == 'FAIL':
            self.notify(_("Query Error"), q.decode('utf8', errors='replace'))
            return False
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
        return dict((int(key), value.decode('utf8', errors='replace')) for key, value in self.local.get_terminals())

    def get_tariffs(self):
        free_time = self.get_free_time()
        ret = self.query('select * from tariff')
        if ret:
            self.local.update_tariffs(ret)
        return filter(lambda x: x is not None, [Tariff.create(t, free_time) for t in self.local.get_tariffs()])

    def get_total_places(self):
        ret = self.query('select PlaceNum from config')
        return int(ret[0][0]) if ret else ret

    def update_free_places(self, diff):
        self.query('update gstatus set placefree = placefree + %i' % (diff,), local=True)
        free_places, _ = self.local.get_free_places()
        self.free_places_update.emit(free_places)

    def get_free_places(self):
        free_places, valid = self.local.get_free_places()
        if not valid:
            answer = self.query('select placefree from gstatus')
            try:
                free_places = int(answer[0][0])
                self.local.update_free_places(free_places)
                self.free_places_update.emit(free_places)
            except (IndexError, KeyError, ValueError, TypeError) as e:
                print 'Incorrect response:', e.__class__.__name__, e
        return free_places

    reasons = {1: 'вручную', 5: 'автоматически'}

    def generate_open_event(self, addr, reason, command):
        if not command % 2:
            return True

        reason = self.reasons.get(reason, '')
        event_name = 'открытие' if command % 2 else ''
        now = datetime.now().strftime(DATETIME_FORMAT)

        args = (event_name, now, addr, reason)
        return self.query('insert into events values("Event",NULL,"%s","%s",%i,"","%s",'
                          '(select placefree from gstatus),"","")' % args, local=True)

    PASS_QUERY = ('insert into events values("Event",NULL,"проезд","%s",%i,"%s","",'
                  '(select placefree from gstatus),%s,"")')

    def generate_pass_event(self, addr, inside, sn=None):
        direction_name = 'внутрь' if inside else 'наружу'
        now = datetime.now().strftime(DATETIME_FORMAT)
        args = (now, addr, direction_name, '"%s"' % (sn,) if sn else 'null')

        return self.query(self.PASS_QUERY % args, local=True)

    def update_config(self):
        response = self.query('select * from config')
        if response:
            self.local.update_config(response)

    def get_config_strings(self):
        return self.local.get_config_strings()

    def get_free_time(self):
        return self.local.get_free_time()

    def get_check_header(self):
        return u'<c><hr />\n' + _('Automatic system\n'
                                  'of payed parking\n'
                                  'STOP-Park\n'
                                  '<hr />\n') + u'\n'.join(self.get_config_strings()[:4]) + u'\n<hr /></c>\n'

    PAYMENT_QUERY = 'insert into payment values(NULL, "{payment}", {tariff}, {console}, "{operator}", ' \
                    ' "{now}", "{id}", {status}, {tariff}, {cost}*100, {units}, "{begin}", "{end}", {price}*100)'

    def generate_payment(self, db_payment_args):
        session = self.local.session()
        operator = session[1] if session is not None else '?'
        now = datetime.now().strftime(DATETIME_FORMAT)

        return self.query(self.PAYMENT_QUERY.format(console=0, operator=operator, status=Ticket.PAID,
                                                    now=now, **db_payment_args), local=True) is None


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