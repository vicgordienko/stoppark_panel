# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtGui import QWidget
from datetime import datetime
from terminal_config import TerminalConfig

class Config(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        uiClass, qtBaseClass = uic.loadUiType('config.ui')
        self.ui = uiClass()
        self.ui.setupUi(self)

        self.terminals = None
        self.payment = None
        self.terminal_config = None

    def setup(self, terminals, payment):
        self.terminals = terminals
        self.payment = payment
        self.ui.setupTerminals.clicked.connect(self.setup_terminals)
        self.ui.updateTerminals.clicked.connect(self.update_terminals)
        self.ui.updateConfig.clicked.connect(self.update_terminals_config)
        self.ui.testDisplay.clicked.connect(self.test_display)

    def test_display(self):
        self.terminals.test_display()
        self.ui.testDisplayResult.setText(datetime.now().strftime('%y-%m-%d %H:%M:%S'))

    def setup_terminals(self):
        if self.terminal_config:
            self.terminal_config.raise_()
        else:
            self.terminal_config = TerminalConfig()
            self.terminal_config.setModal(True)
            self.terminal_config.exec_()
            self.terminal_config = None
            #self.terminal_config.closed.connect(self.setup_terminals_closed)

    def setup_terminals_closed(self):
        self.terminal_config = None

    def update_terminals_config(self):
        self.terminals.update_device_config()
        self.ui.updateConfigResult.setText(datetime.now().strftime('%y-%m-%d %H:%M:%S'))

    def update_terminals(self):
        self.ui.updateTerminals.setEnabled(False)

        def terminals_updated(ok):
            message = u'успешно' if ok else u'не удалось'
            now = datetime.now().strftime('%y-%m-%d %H:%M:%S')
            self.ui.updateTerminalsResult.setText(u'Обновление %s (%s)' % (message, now))

            self.ui.updateTerminals.setEnabled(True)
        self.terminals.ready.connect(terminals_updated)
        self.terminals.update_model()

    def closeEvent(self, event):
        if self.terminal_config:
            self.terminal_config.close()