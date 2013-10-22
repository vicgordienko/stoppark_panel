from u2py.interface_basis import load, BaseReader as Terminal, DumpableStructure, DumpableBigEndianStructure, ByteArray, ReaderError
from ctypes import POINTER as P, c_uint16, c_uint8, c_char, c_char_p, Structure
from datetime import datetime

class TerminalEntries(Structure):
    _fields_ = [
        ('dts11', c_uint8, 1),
        ('dts12', c_uint8, 1),
        ('key1', c_uint8, 1),
        ('in1', c_uint8, 1),
        ('in2', c_uint8, 1),
        ('key2', c_uint8, 1),
        ('dts22', c_uint8, 1),
        ('dts21', c_uint8, 1),

        ('stp_time', c_uint8, 1),
        ('stp_mes', c_uint8, 1),
        ('stp_tarif', c_uint8, 1),
        ('stp_places', c_uint8, 1),
        ('stp_paper_near', c_uint8, 1),
        ('stp_paper_no', c_uint8, 1),
        ('_stp_reserved', c_uint8, 2),

        ('in_count', c_uint8),
        ('out_count', c_uint8),
        ('status_reason', c_uint8),
    ]

    def __init__(self, addr):
        self.addr = addr

    def __str__(self):
        this = ByteArray(self)
        return str({
            'in_count': self.in_count,
            'out_count': self.out_count,
            'status': bin(this[1]),
            'reason': TerminalState.reverse_reasons.get(self.status_reason, None)
        })

    def process(self, terminal, mainloop, reset=True):
        if terminal_get_entries(terminal, self.addr, self):
            return False
        if reset:
            terminal_reset_entries(terminal, self.addr)

        if not self.stp_time:
            TerminalTime().set(terminal, self.addr)

        if not self.stp_mes:
            TerminalStrings(mainloop.db).set(terminal, self.addr)

        free_places_diff = self.out_count - self.in_count
        if free_places_diff:
            mainloop.db.update_free_places(free_places_diff)
            TerminalCounters(mainloop.db).set(terminal, 0xFF)
        elif not self.stp_places:
            TerminalCounters(mainloop.db).set(terminal, self.addr)

        for i in range(self.out_count):
            mainloop.db.generate_pass_event(self.addr, inside=False)

        for i in range(self.in_count):
            mainloop.db.generate_pass_event(self.addr, inside=True)

        return True


class TerminalState(DumpableStructure):
    _fields_ = [
        ('reason', c_uint8),
        ('command', c_uint8),
    ]

    reasons = {'not': 0, 'man': 1, 'prepay': 2, 'talon': 3, 'staff': 4, 'auto': 5}
    commands = {'no': 0, 'open': 1, 'close': 2, 'in_open': 3, 'in_close': 4,
                'out_open': 5, 'out_close': 6}
    reverse_reasons = {v: k for k, v in reasons.items()}
    reverse_commands = {v: k for k, v in commands.items()}

    def __init__(self, reason, command):
        self.reason = self.reasons.get(reason, reason)
        self.command = self.commands.get(command, command)

    TRY_COUNT = 3

    def set(self, terminal, addr, db=None):
        for i in range(self.TRY_COUNT):
            ret = terminal_set_state(terminal, addr, self)
            print 'Action open[%i]: %s' % (addr, hex(ret),)
            if ret == 0:
                if db is not None:
                    db.generate_open_event(addr, self.reason, self.command)
                return ret

    def __str__(self):
        return str({
            'reason': self.reverse_reasons.get(self.reason, self.reason),
            'command': self.reverse_commands.get(self.command, self.command),
        })


class TerminalCounters(DumpableBigEndianStructure):
    _fields_ = [
        ('free_places', c_uint16)
    ]

    def __init__(self, db):
        self.free_places = db.get_free_places()

    def set(self, terminal, addr):
        return terminal_set_counters(terminal, addr, self)


class TerminalReader(DumpableStructure):
    _fields_ = [
        ('time', c_uint8),
        ('status', c_uint8),
        ('sn', c_char * 10),
    ]

    CARD_READ = 0x03
    CARD_ON = 0x04
    CARD_OUT = 0x05
    CARD_IN = 0x06
    CARD_EMPTY = 0xFF

    TIMEOUT = 30

    def process(self, direction, mainloop):
        if self.status == self.CARD_READ and self.time < self.TIMEOUT:
            card = mainloop.db.get_card(self.sn)
            mainloop.notify.emit(u'Поднесение карточки к терминалу', u'%s' % (card.fio()))
            if card and card.check(direction):
                mainloop.notify.emit(u'Проезд разрешен', u'%s' % (card.fio()))
                return lambda terminal, addr: TerminalState('man', 'in_open').set(terminal, addr, mainloop.db)
            else:
                mainloop.notify.emit(u'Проезд запрещен', u'%s' % (card.fio()))
        if self.status == self.CARD_IN:
            card = mainloop.db.get_card(self.sn)
            mainloop.notify.emit(u'Въезд', u'%s' % (card.fio()))
            mainloop.db.card_moved_inside(self.sn)
        if self.status == self.CARD_OUT:
            card = mainloop.db.get_card(self.sn)
            mainloop.notify.emit(u'Выезд', u'%s' % (card.fio()))
            mainloop.db.card_moved_outside(self.sn)


class TerminalReaders(Structure):
    _fields_ = [
        ('reader_in', TerminalReader),
        ('reader_out', TerminalReader),
    ]

    def __init__(self, addr):
        self.addr = addr

    def __str__(self):
        return str(self.reader_out) if self.addr % 2 else str(self.reader_in)

    def process(self, terminal, mainloop):
        ret = terminal_get_readers(terminal, self.addr, self)

        direction = self.addr % 2
        if (direction == 0 and ret != 0xe0c18de) or (direction == 1 and ret != 0):
            return False

        terminal_ack_readers(terminal, self.addr)

        handler = self.reader_out if direction else self.reader_in
        action = handler.process(direction, mainloop)
        if action:
            action(terminal, self.addr)

        return True


class TerminalBarcode(DumpableStructure):
    _fields_ = [
        ('time', c_uint8),
        ('status', c_uint8),
        ('code', c_char * 18)
    ]

    BAR_READ = 0x00
    BAR_LEFT = 0x01
    BAR_NO = 0x02

    def __init__(self, addr):
        self.addr = addr

    def process(self, terminal, mainloop):
        ret = terminal_get_barcode(terminal, self.addr, self)
        if ret != 0 and ret != 0xe0214de:
            return False

        if self.status == self.BAR_READ:
            print self
            print mainloop.db.get_ticket(self.code)

        return True


class CheckLine(Structure):
    _fields_ = [
        ('data', c_char*30),
    ]


class TerminalStrings(Structure):
    _fields_ = [
        ('tariff_names', (c_char * 20) * 8),
        ('check_lines', CheckLine * 8)
    ]

    def __init__(self, db):
        strings = db.get_config_strings()
        [setattr(self.check_lines[i], 'data', s.decode('utf8').encode('cp1251')[:30]) for i, s in enumerate(strings)]

    def set(self, terminal, addr):
        return terminal_set_strings(terminal, addr, self)


class TerminalMessage(Structure):
    def __init__(self, message):
        self.message = message.decode('utf8').encode('cp1251')
        self.message += ' '*(80 - len(self.message))

    def set(self, terminal, addr, status=15):
        return terminal_show_message(terminal, addr, self.message, len(self.message), status)


class TerminalTime(DumpableStructure):
    _fields_ = [
        ('year', c_uint8),
        ('month', c_uint8),
        ('day', c_uint8),
        ('hour', c_uint8),
        ('minute', c_uint8),
        ('second', c_uint8),
    ]

    def __init__(self):
        now = datetime.now()
        self.year = now.year % 2000
        self.month = now.month
        self.day = now.day
        self.hour = now.hour
        self.minute = now.minute
        self.second = now.second

    def set(self, terminal, addr):
        return terminal_set_time(terminal, addr, self)


def check(params):
    """
    This function assures that first parameter (namely: Terminal) is open.'
    If it's not, then it tries to open it and returns -0xFF on failure.
    """
    terminal = params[0]
    if not terminal.is_open():
        try:
            terminal.reopen()
        except ReaderError:
            import time
            time.sleep(1)
            return -0xFF

terminal_set_state = load('terminal_set_state', (Terminal, c_uint8, P(TerminalState)), check_params=check)
terminal_reset_entries = load('terminal_reset_entries', (Terminal, c_uint8,), check_params=check)
terminal_get_entries = load('terminal_get_entries', (Terminal, c_uint8, P(TerminalEntries)), check_params=check)
terminal_set_counters = load('terminal_set_counters', (Terminal, c_uint8, P(TerminalCounters)), check_params=check)
terminal_get_readers = load('terminal_get_readers', (Terminal, c_uint8, P(TerminalReaders)), check_params=check)
terminal_ack_readers = load('terminal_ack_readers', (Terminal, c_uint8,), check_params=check)
terminal_get_barcode = load('terminal_get_barcode', (Terminal, c_uint8, P(TerminalBarcode)), check_params=check)
terminal_ack_barcode = load('terminal_ack_barcode', (Terminal, c_uint8,), check_params=check)
terminal_set_strings = load('terminal_set_strings', (Terminal, c_uint8, P(TerminalStrings)), check_params=check)
terminal_set_time = load('terminal_set_time', (Terminal, c_uint8, P(TerminalTime)), check_params=check)
terminal_show_message = load('terminal_show_message', (Terminal, c_uint8, c_char_p, c_uint8, c_uint8), check_params=check)

if __name__ == '__main__':
    import config

    config.setup_logging()

    t = Terminal()

    terminal_set_state(t, 0, TerminalState('auto', 'open'))