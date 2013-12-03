# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QWidget, QApplication
from db import LocalDB
from i18n import language
_ = language.ugettext


class Main(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('main.ui')[0]()
        self.ui.setupUi(self)

        self.localize()

        self.ui.config.setup(self.ui.terminals, self.ui.payments)

        self.ui.terminals.ready.connect(self.ui.config.terminals_ready)
        self.ui.config.terminals_changed.connect(self.ui.terminals.update_model)
        self.ui.config.terminals_changed.connect(self.enable_buttons)

        self.ui.payments.session_started.connect(self.session_start)
        self.ui.payments.session_ended.connect(self.session_end)

        self.db = LocalDB()
        self.left_terminals = []
        self.right_terminals = []

        self.ui.leftUp.clicked.connect(self.left_up)
        self.ui.leftDown.clicked.connect(self.left_down)
        self.ui.rightUp.clicked.connect(self.right_up)
        self.ui.rightDown.clicked.connect(self.right_down)

        self.ui.payments.new_payment.connect(lambda: self.ui.tabs.setCurrentIndex(1))

        self.session_end()
        #self.setWindowFlags(Qt.CustomizeWindowHint)

    def enable_buttons(self):
        self.left_terminals = self.db.get_terminals_id_by_option('left')
        self.ui.leftUp.setEnabled(not not self.left_terminals)
        self.ui.leftDown.setEnabled(not not self.left_terminals)

        self.right_terminals = \
            self.db.get_terminals_id_by_option('right')
        self.ui.rightUp.setEnabled(not not self.right_terminals)
        self.ui.rightDown.setEnabled(not not self.right_terminals)

    def disable_buttons(self):
        [bt.setEnabled(False) for bt in [self.ui.leftUp, self.ui.leftDown, self.ui.rightUp, self.ui.rightDown]]

    def session_start(self):
        [self.ui.tabs.setTabEnabled(i, True) for i in [0, 2]]
        self.ui.terminals.start_mainloop()
        self.enable_buttons()

    def session_end(self):
        [self.ui.tabs.setTabEnabled(i, False) for i in [0, 2]]
        self.disable_buttons()
        self.ui.terminals.stop_mainloop()

    def localize(self):
        self.ui.tabs.setTabText(0, _('Terminals'))
        self.ui.tabs.setTabText(1, _('Payments'))
        self.ui.tabs.setTabText(2, _('Config'))

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
        self.ui.terminals.stop_mainloop()
        self.ui.payments.stop_reader()

        return QWidget.closeEvent(self, event)


if __name__ == '__main__':
    import sys
    import config
    config.setup_logging()

    app = QApplication(sys.argv)

    widget = Main()
    widget.showMaximized()

    sys.exit(app.exec_())