# -*- coding: utf-8 -*-
from gevent import sleep, spawn
from gevent.queue import Queue
from interface import Terminal, TerminalEntries, TerminalReaders, TerminalBarcode, TerminalState
from interface import TerminalCounters, TerminalStrings, TerminalTime, TerminalMessage
from interface import ReaderError
from PyQt4.QtCore import QObject, pyqtSignal
from db import DB
from threading import Thread
from i18n import language
_ = language.ugettext


def device_loop(terminal, mainloop, addr, data):
    failure = 0

    def notify_mainloop(title, message):
        return mainloop.notify.emit(title, message)

    notify = notify_mainloop if data.notify else lambda title, msg: None

    while True:
        processors = [TerminalEntries(addr), TerminalReaders(addr)]
        if addr % 2:
            processors.append(TerminalBarcode(addr))

        for p in processors:
            failure = 0 if p.process(terminal, mainloop.db, notify) else (failure + 1)
            s = 4 if failure > 2 else 0.3
            mainloop.state.emit(addr, 'active' if failure <= 2 else 'inactive')
            sleep(s)


class Mainloop(QObject):
    ready = pyqtSignal(bool, dict)
    stopped = pyqtSignal()
    report = pyqtSignal(int, str)
    state = pyqtSignal(int, str)
    notify = pyqtSignal(str, str)

    def __init__(self, devices, parent=None):
        super(Mainloop, self).__init__(parent)
        self.queue = None
        self.thread = None
        self.devices = devices
        self.db = None

    def spawn_device_greenlets(self, terminal, devices):
        print devices
        return [spawn(device_loop, terminal, self, addr, data) for addr, data in devices.iteritems()]

    @staticmethod
    def dummy_greenlet():
        while True:
            sleep(1)

    def _mainloop(self):

        try:
            terminal = Terminal(explicit_error=True)
        except ReaderError:
            self.notify.emit(_('Terminals error'), _('Cannot connect to concentrator'))
            self.ready.emit(False, {})
            sleep(5)
            self.stopped.emit()
            return

        self.db = DB(notify=lambda title, msg: self.notify.emit(title, msg))

        self.queue = Queue()
        self.ready.emit(True, self.devices)

        greenlets = self.spawn_device_greenlets(terminal, self.devices)
        if not greenlets:
            greenlets.append(spawn(self.dummy_greenlet))

        while True:
            command = self.queue.get()

            if callable(command):
                command(terminal)
            else:
                [greenlet.kill() for greenlet in greenlets]
                break

        terminal.close()
        self.queue = None
        self.stopped.emit()

    def start(self):
        self.thread = Thread(target=self._mainloop)
        self.thread.start()

    def stop(self, block=False):
        if self.queue:
            self.queue.put(None)
            if block:
                self.thread.join()

    def test_display(self):
        test_message = _('Test message')
        self.queue.put(lambda terminal: TerminalMessage(test_message).set(terminal, 0xFF, 5))

    def update_config(self, addr=0xFF):
        self.queue.put(lambda terminal: TerminalTime().set(terminal, addr))
        self.queue.put(lambda terminal: TerminalStrings(self.db).set(terminal, addr))
        self.queue.put(lambda terminal: TerminalCounters(self.db).set(terminal, addr))

    def terminal_open(self, addr):
        self.queue.put(lambda terminal: TerminalState('man', 'open').set(terminal, addr, self.db))

    def terminal_close(self, addr):
        self.queue.put(lambda terminal: TerminalState('man', 'close').set(terminal, addr, self.db))

if __name__ == '__main__':
    m = Mainloop([0, 1, 2, 3])
    m.start()

    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
       m.stop()
