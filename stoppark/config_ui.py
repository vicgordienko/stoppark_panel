# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QWidget, QDialog
from datetime import datetime
from config import DATETIME_FORMAT_USER
from flickcharm import FlickCharm
from keyboard import Keyboard
import stoppark
from i18n import language
_ = language.ugettext


class Config(QWidget):
    terminals_changed = pyqtSignal()
    terminals_update_requested = pyqtSignal()
    option_changed = pyqtSignal(str, str)
    own_ip_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('config.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.terminals = None
        self.payment = None
        self.terminal_config = None

        self.flick = FlickCharm()
        self.flick.activate_on(self.ui.terminalsScrollArea)
        self.flick.activate_on(self.ui.generalScrollArea)

        self.ui.version.setText(stoppark.__version__)
        self.get_time()

        self.ui.updateVersion.setVisible(False)
        self.ui.setupTerminals.clicked.connect(self.setup_terminals)
        self.ui.updateTerminals.clicked.connect(self.begin_terminal_update)

        self.wicd = None
        self.ui.setupNetworkConnection.clicked.connect(self.setup_network_connection)

        self.ui.apbState.stateChanged.connect(lambda state: self.option_changed.emit('apb', str(state)))
        self.ui.manualTicketPrint.stateChanged.connect(lambda state: self.option_changed.emit('ticket.manual_print',
                                                                                              str(state)))

    def localize(self):
        self.ui.tabs.setTabText(0, _('General'))
        self.ui.tabs.setTabText(1, _('Terminals'))
        self.ui.tabs.setTabText(2, _('Payments'))

        self.ui.versionTitle.setText(_('Version:'))

        self.ui.dateTimeTitle.setText(_('Date and time:'))
        self.ui.setTime.setText(_('Setup'))

        self.ui.dbIPTitle.setText(_('DB server IP:'))
        self.ui.setDBIP.setText(_('Setup'))

        self.ui.networkConnectionTitle.setText(_('Network connection:'))
        self.ui.setupNetworkConnection.setText(_('Setup network connection'))

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
        self.ui.apbTitle.setText(_('Antipassback'))
        self.ui.apbState.setText(_('Enable'))

        self.ui.manualTicketPrintTitle.setText(_('Manual ticket print'))
        self.ui.manualTicketPrint.setText(_('Enable'))

    def begin_session(self, fio, access):
        if access in ['admin', 'operator']:
            [self.ui.tabs.setTabEnabled(i, True) for i in [0, 1, 2]]
            self.ui.setTime.setEnabled(True)
            self.ui.updateVersion.setEnabled(True)
            return True
        if access in ['config']:
            [self.ui.tabs.setTabEnabled(i, True if i == 0 else False) for i in [0, 1, 2]]
            self.ui.setTime.setEnabled(False)
            self.ui.updateVersion.setEnabled(False)
            return True
        return False

    def end_session(self):
        [self.ui.tabs.setTabEnabled(i, False) for i in [0, 1, 2]]
        return True

    def setup(self, terminals, payment):
        self.terminals = terminals
        self.payment = payment

        self.ui.setTime.clicked.connect(self.set_time)
        self.ui.showKeyboard.clicked.connect(lambda: Keyboard.show())

        self.ui.setDBIP.clicked.connect(self.set_db_ip)
        self.ui.testDisplay.clicked.connect(self.test_display)

    def handle_option(self, key, value):
        handler = {
            'db.ip': lambda v: self.ui.dbIP.setText(v),
            'apb': lambda v: self.ui.apbState.setCheckState(int(v)),
            'ticket.manual_print': lambda v: self.ui.manualTicketPrint.setCheckState(int(v))
        }.get(str(key), None)
        if handler:
            print 'found handler for ', key
            handler(value)

    def get_time(self):
        from PyQt4.QtCore import QTime, QDate

        self.ui.dateEdit.setDate(QDate.currentDate())
        self.ui.timeEdit.setTime(QTime.currentTime())

    def set_time(self):
        from subprocess import Popen

        new_date = self.ui.dateEdit.date()
        new_time = self.ui.timeEdit.time()
        new_datetime = datetime(year=new_date.year(), month=new_date.month(), day=new_date.day(),
                                hour=new_time.hour(), minute=new_time.minute(), second=new_time.second())
        arg = new_datetime.strftime('%m%d%H%M%Y')
        Popen(['date', arg])

    def set_db_ip(self):
        self.option_changed.emit('db.ip', self.ui.dbIP.text())
        self.ui.setDBIPHelp.setText(_('Update: %s') % (datetime.now().strftime(DATETIME_FORMAT_USER)))

    def test_display(self):
        self.terminals.test_display()
        self.ui.testDisplayResult.setText(_('Update: %s') % (datetime.now().strftime(DATETIME_FORMAT_USER)))

    def setup_terminals(self):
        from terminal_config import TerminalConfig
        self.terminal_config = TerminalConfig()
        if self.terminal_config.exec_() == QDialog.Accepted:
            self.begin_terminal_change()
        self.terminal_config = None

    def terminals_ready(self, ok):
        message = _('successful') if ok else _('unsuccessful')
        now = datetime.now().strftime(DATETIME_FORMAT_USER)
        self.ui.updateTerminalsResult.setText(_('Update: %(message)s (%(now)s)' % {
            'message': message,
            'now': now
        }))
        self.ui.updateTerminals.setEnabled(True)

    def begin_terminal_update(self):
        self.ui.updateTerminals.setEnabled(False)
        self.terminals_update_requested.emit()

    def begin_terminal_change(self):
        self.ui.updateTerminals.setEnabled(False)
        self.terminals_changed.emit()

    def setup_network_connection(self):
        Keyboard.show(layout=[])

        from subprocess import Popen
        if self.wicd is not None:
            if self.wicd.poll() is None:
                return
        self.wicd = Popen(['xterm', '-maximized', '-e', 'wicd-curses'])


