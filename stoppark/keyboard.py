from subprocess import Popen
from PyQt4 import uic
from PyQt4.QtGui import QLineEdit, QDialog
from db import Ticket


class Keyboard(object):
    keyboard = None

    @classmethod
    def show(cls, layout=None):
        if cls.keyboard is not None:
            if cls.keyboard.poll() is None:
                return
        if layout is None:
            layout = 'digits'
        cls.keyboard = Popen(['matchbox-keyboard', layout])


class TouchLineEdit(QLineEdit):
    def __init__(self, *args):
        QLineEdit.__init__(self, *args)

    def focusInEvent(self, e):
        Keyboard.show()


class TicketInput(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.ui = uic.loadUiType('ticket-input.ui')[0]()
        self.ui.setupUi(self)

        self.ui.ok.clicked.connect(self.ok)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.keyboard.clicked.connect(self.show_keyboard)
        self.ui.bar.textChanged.connect(self.bar_changed)

        self.show_keyboard()

    @staticmethod
    def show_keyboard():
        Keyboard.show('digits')

    @property
    def bar(self):
        return str(self.ui.bar.text())

    def bar_changed(self, bar):
        bar = str(bar)
        try:
            assert(len(bar) == 18)
            Ticket.parse_bar(bar)
            self.ui.ok.setEnabled(True)
            self.ui.bar.setStyleSheet('background-color: #bbffbb')
        except (ValueError, AssertionError):
            self.ui.ok.setEnabled(False)
            self.ui.bar.setStyleSheet('background-color: #ffbbbb')

    def ok(self):
        self.accept()

    def cancel(self):
        self.reject()


