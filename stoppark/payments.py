from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal
from PyQt4.QtGui import QWidget
from threading import Thread


class BARReader(QObject):
    bar_read = pyqtSignal(str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.thread = Thread(target=self._loop)

    def _loop(self):
        import serial
        port = serial.Serial(port='/dev/ttyS0', baudrate=9600)
        while True:
            bar = port.readline()
            self.bar_read.emit(bar)

    def start(self):
        self.thread.start()

    def stop(self):
        pass


class Payments(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUi('payments.ui', self)

        self.reader = BARReader(self)
        self.reader.bar_read.connect(self.handle_bar)
        self.reader.start()

    def handle_bar(self, bar):
        print 'handle_bar', bar