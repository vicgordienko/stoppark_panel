# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QWidget, QDialog
from datetime import datetime
from terminal_config import TerminalConfig
from flickcharm import FlickCharm


class Config(QWidget):
    DATETIME_FORMAT = '%d-%m-%Y %H:%M:%S'

    terminals_changed = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('config.ui')[0]()
        self.ui.setupUi(self)

        self.terminals = None
        self.payment = None
        self.terminal_config = None

        self.flick = FlickCharm()
        self.flick.activate_on(self.ui.scrollArea)

    def setup(self, terminals, payment):
        self.terminals = terminals
        self.payment = payment
        self.ui.setupTerminals.clicked.connect(self.setup_terminals)
        self.ui.updateTerminals.clicked.connect(self.update_terminals)
        self.ui.updateConfig.clicked.connect(self.update_terminals_config)
        self.ui.testDisplay.clicked.connect(self.test_display)

    def test_display(self):
        self.terminals.test_display()
        self.ui.testDisplayResult.setText(datetime.now().strftime(self.DATETIME_FORMAT))

    def setup_terminals(self):
        self.terminal_config = TerminalConfig()
        if self.terminal_config.exec_() == QDialog.Accepted:
            self.update_terminals()
        self.terminal_config = None

    def update_terminals_config(self):
        self.terminals.update_device_config()
        self.ui.updateConfigResult.setText(datetime.now().strftime(self.DATETIME_FORMAT))

    def terminals_ready(self, ok):
        message = u'успешно' if ok else u'не удалось'
        now = datetime.now().strftime(self.DATETIME_FORMAT)
        self.ui.updateTerminalsResult.setText(u'Обновление %s (%s)' % (message, now))
        self.ui.updateTerminals.setEnabled(True)

    def update_terminals(self):
        self.ui.updateTerminals.setEnabled(False)
        self.terminals_changed.emit()