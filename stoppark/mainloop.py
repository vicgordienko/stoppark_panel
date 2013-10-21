# -*- coding: utf-8 -*-
from gevent import sleep, spawn
from gevent.queue import Queue
from interface import Terminal, TerminalEntries, TerminalReaders, TerminalBarcode, TerminalState
from interface import TerminalCounters, TerminalStrings, TerminalTime, TerminalMessage
from PyQt4.QtCore import QObject, pyqtSignal
from db import DB
from threading import Thread
from datetime import datetime


def device_loop(terminal, mainloop, addr):
    failure = 0
    while True:
        processors = [TerminalEntries(addr), TerminalReaders(addr)]
        if addr % 2:
            processors.append(TerminalBarcode(addr))

        for p in processors:
            failure = 0 if p.process(terminal, mainloop) else (failure + 1)
            s = 4 if failure > 2 else 0.3
            mainloop.state.emit(addr, 'active' if failure <= 2 else 'inactive')
            sleep(s)


class Mainloop(QObject):
    ready = pyqtSignal(bool)
    report = pyqtSignal(int, str)
    state = pyqtSignal(int, str)
    notify = pyqtSignal(str, str)

    def __init__(self, devices, parent=None):
        super(Mainloop, self).__init__(parent)
        self.queue = None
        self.db = DB(notify=lambda title, msg: self.notify.emit(title, msg))
        self.thread = None
        self.devices = devices

    def spawn_device_greenlets(self, terminal):
        return [spawn(device_loop, terminal, self, addr) for addr in self.devices]

    def _mainloop(self):

        if not self.devices:
            self.notify.emit('Terminal error', 'No devices')
            self.ready.emit(False)
            return

        terminal = Terminal()
        if not terminal.is_open():
            self.notify.emit('Terminal error', 'No terminal')
            self.ready.emit(False)
            return

        self.queue = Queue()
        self.ready.emit(True)

        greenlets = self.spawn_device_greenlets(terminal)

        while True:
            command = self.queue.get()

            if callable(command):
                command(terminal)
            else:
                [greenlet.kill() for greenlet in greenlets]
                break

        terminal.close()
        print 'Mainloop completed'

    def start(self):
        self.thread = Thread(target=self._mainloop)
        self.thread.start()

    def stop(self):
        if self.queue:
            self.queue.put(None)
            self.thread.join()

    def test_display(self):
        self.queue.put(lambda terminal: TerminalMessage('Добро пожаловать').set(terminal, 0xFF, 5))

    def update_config(self, addr=0xFF):
        self.queue.put(lambda terminal: TerminalTime().set(terminal, addr))
        self.queue.put(lambda terminal: TerminalStrings(self.db).set(terminal, addr))
        self.queue.put(lambda terminal: TerminalCounters(self.db).set(terminal, addr))

    def terminal_open(self, addr):
        self.queue.put(lambda terminal: TerminalState('man', 'in_open').set(terminal, addr, self.db))

    def terminal_close(self, addr):
        self.queue.put(lambda terminal: TerminalState('man', 'in_close').set(terminal, addr, self.db))

if __name__ == '__main__':
    m = Mainloop([0, 1, 2, 3])
    m.start()

    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
       m.stop()
