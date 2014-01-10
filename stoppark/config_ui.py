# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QWidget, QDialog
from datetime import datetime
from config import DATETIME_FORMAT_USER
from terminal_config import TerminalConfig
from flickcharm import FlickCharm
from i18n import language
_ = language.ugettext


class Config(QWidget):
    terminals_changed = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('config.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.terminals = None
        self.payment = None
        self.terminal_config = None

        self.flick = FlickCharm()
        self.flick.activate_on(self.ui.scrollArea)

    def localize(self):
        self.ui.tabs.setTabText(0, _('Terminals'))
        self.ui.tabs.setTabText(1, _('Payments'))
        self.ui.updateTerminalsTitle.setText(_('Terminal list'))
        self.ui.updateTerminalsHelp.setText(_('Configure and update terminal list:'))
        self.ui.setupTerminals.setText(_('Configure'))
        self.ui.updateTerminals.setText(_('Update'))
        self.ui.updateConfigTitle.setText(_('Terminal setup'))
        self.ui.updateConfigHelp.setText(_('Perform global terminal setup:'))
        self.ui.updateConfig.setText(_('Setup'))
        self.ui.testsTitle.setText(_('Tests'))
        self.ui.testDisplayHelp.setText(_('Display test:'))
        self.ui.testDisplay.setText(_('Test display'))

    def setup(self, terminals, payment):
        self.terminals = terminals
        self.payment = payment
        self.ui.setupTerminals.clicked.connect(self.setup_terminals)
        self.ui.updateTerminals.clicked.connect(self.update_terminals)
        self.ui.updateConfig.clicked.connect(self.update_terminals_config)
        self.ui.testDisplay.clicked.connect(self.test_display)

    def test_display(self):
        self.terminals.test_display()
        self.ui.testDisplayResult.setText(datetime.now().strftime(DATETIME_FORMAT_USER))

    def setup_terminals(self):
        self.terminal_config = TerminalConfig()
        if self.terminal_config.exec_() == QDialog.Accepted:
            self.update_terminals()
        self.terminal_config = None

    def update_terminals_config(self):
        self.terminals.update_device_config()
        self.ui.updateConfigResult.setText(datetime.now().strftime(DATETIME_FORMAT_USER))

    def terminals_ready(self, ok):
        message = _('successful') if ok else _('unsuccessful')
        now = datetime.now().strftime(DATETIME_FORMAT_USER)
        self.ui.updateTerminalsResult.setText(_('Update: %(message)s (%(now)s)' % {
            'message': message,
            'now': now
        }))
        self.ui.updateTerminals.setEnabled(True)

    def update_terminals(self):
        self.ui.updateTerminals.setEnabled(False)
        self.terminals_changed.emit()