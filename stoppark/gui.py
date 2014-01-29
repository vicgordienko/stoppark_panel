# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtGui import QWidget, QApplication, QIcon, QSystemTrayIcon, QDialog
from executor import Executor
from login import LoginDialog, LogoffDialog
from db import Card
from i18n import language
_ = language.ugettext


class Main(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('main.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.ui.config.setup(self.ui.terminals, self.ui.payments)

        self.tabs = [self.ui.terminals, self.ui.payments, self.ui.config]

        self.ui.terminals.ready.connect(self.ui.config.terminals_ready)

        self.left_terminals = []
        self.right_terminals = []

        self.ui.leftUp.clicked.connect(self.left_up)
        self.ui.leftDown.clicked.connect(self.left_down)
        self.ui.rightUp.clicked.connect(self.right_up)
        self.ui.rightDown.clicked.connect(self.right_down)

        self.end_session()

        self.notifier = QSystemTrayIcon(QIcon('arrow-up-icon.png'), self)
        self.notifier.show()

        self.session = None
        self.executor = self.setup_executor()
        self.executor.start()

        #self.setWindowFlags(Qt.CustomizeWindowHint)

    def localize(self):
        self.setWindowTitle(_('Stop-Park'))
        self.ui.tabs.setTabText(0, _('Terminals'))
        self.ui.tabs.setTabText(1, _('Payments'))
        self.ui.tabs.setTabText(2, _('Config'))

    def setup_payments(self, executor):
        self.ui.payments.tariff_update_requested.connect(executor.update_tariffs)
        executor.tariffs_updated.connect(self.ui.payments.update_tariffs)

        executor.new_payable.connect(self.ui.payments.handle_payable)
        self.ui.payments.payable_accepted.connect(lambda: self.ui.tabs.setCurrentIndex(1))

        self.ui.payments.display_requested.connect(executor.display)
        self.ui.payments.manual_ticket_inputted.connect(executor.handle_bar)
        self.ui.payments.notify_requested.connect(self.notifier.showMessage)

        self.ui.payments.payment_initiated.connect(executor.pay)
        executor.payment_processed.connect(self.ui.payments.handle_payment_processed)

    def setup_executor(self):
        executor = Executor()
        executor.notify.connect(lambda title, msg: self.notifier.showMessage(title, msg))

        self.setup_payments(executor)

        executor.new_operator.connect(self.handle_operator)
        executor.session_begin.connect(self.begin_session)
        executor.session_end.connect(self.end_session)

        executor.option_notification.connect(self.ui.config.set_option)
        self.ui.config.option_changed.connect(executor.set_option)

        self.ui.config.terminals_changed.connect(executor.notify_terminals)
        self.ui.config.terminals_update_requested.connect(executor.update_terminals)
        executor.terminals_notification.connect(self.update_terminals)

        return executor

    @staticmethod
    def disconnect_from_signal(signal, slot):
        try:
            signal.disconnect(slot)
            return True
        except TypeError:  # .disconnect raises TypeError when given signal is not connected
            return False

    def handle_operator(self, card):
        print 'operator', card
        if not self.disconnect_from_signal(self.executor.new_operator, self.handle_operator):
            return

        if self.session is None:
            login_dialog = LoginDialog(card, parent=self)
            if login_dialog.exec_() == QDialog.Accepted:
                self.executor.begin_session(card)
        elif self.session == card.sn or card.type == Card.ADMIN:
            login_dialog = LogoffDialog(card, self.executor)
            if login_dialog.exec_() == QDialog.Accepted:
                self.executor.end_session()
        self.executor.new_operator.connect(self.handle_operator)

    def begin_session(self, sn, fio, access):
        self.session = sn
        for tab_index, tab_widget in enumerate(self.tabs):
            self.ui.tabs.setTabEnabled(tab_index, tab_widget.begin_session(fio, access))
        if access in ['admin', 'operator']:
            self.executor.notify_terminals()
        else:
            self.update_buttons()

    def end_session(self):
        self.session = None
        for tab_index, tab_widget in enumerate(self.tabs):
            if tab_widget.end_session():
                self.ui.tabs.setTabEnabled(tab_index, False)
            else:
                self.ui.tabs.setCurrentIndex(tab_index)
        self.update_terminals()

    def update_terminals(self, terminals=None):
        if terminals is None:
            terminals = {}
        else:
            self.ui.terminals.stop_mainloop()

        self.left_terminals = [key for key, value in terminals.iteritems() if value[1] == 'left']
        print self.left_terminals
        self.ui.leftUp.setEnabled(not not self.left_terminals)
        self.ui.leftDown.setEnabled(not not self.left_terminals)

        self.right_terminals = [key for key, value in terminals.iteritems() if value[1] == 'right']
        print self.right_terminals
        self.ui.rightUp.setEnabled(not not self.right_terminals)
        self.ui.rightDown.setEnabled(not not self.right_terminals)

    def left_up(self):
        for addr in self.left_terminals:
            self.ui.terminals.terminal_open(addr)

    def left_down(self):
        for addr in self.left_terminals:
            self.ui.terminals.terminal_close(addr)

    def right_up(self):
        for addr in self.right_terminals:
            self.ui.terminals.terminal_open(addr)

    def right_down(self):
        for addr in self.right_terminals:
            self.ui.terminals.terminal_close(addr)

    #noinspection PyPep8Naming
    def closeEvent(self, event):
        self.ui.terminals.end_session(block=True)
        self.executor.stop()

        return QWidget.closeEvent(self, event)


if __name__ == '__main__':
    import sys
    import config

    config.setup_logging()

    app = QApplication(sys.argv)

    widget = Main()
    widget.showMaximized()

    sys.exit(app.exec_())