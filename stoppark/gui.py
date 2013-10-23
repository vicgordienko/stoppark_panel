# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QWidget, QApplication
from db import LocalDB

class Main(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        uiClass, qtBaseClass = uic.loadUiType('main.ui')
        self.ui = uiClass()
        self.ui.setupUi(self)

        self.ui.config.setup(self.ui.terminals, self.ui.payments)

        self.ui.terminals.ready.connect(self.ui.config.terminals_ready)
        self.ui.config.terminals_changed.connect(self.ui.terminals.update_model)
        self.ui.config.terminals_changed.connect(self.update_terminals)

        self.db = LocalDB()
        self.left_terminals = []
        self.right_terminals = []

        self.ui.leftUp.clicked.connect(self.left_up)
        self.ui.leftDown.clicked.connect(self.left_down)
        self.ui.rightUp.clicked.connect(self.right_up)
        self.ui.rightDown.clicked.connect(self.right_down)

        self.update_terminals()

        self.ui.payments.new_payment.connect(lambda: self.ui.tabs.setCurrentIndex(1))
        #self.setWindowFlags(Qt.CustomizeWindowHint)

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

    def update_terminals(self):
        self.left_terminals = self.db.get_terminals_id_by_option('left')
        self.ui.leftUp.setEnabled(not not self.left_terminals)
        self.ui.leftDown.setEnabled(not not self.left_terminals)

        self.right_terminals = \
            self.db.get_terminals_id_by_option('right')
        self.ui.rightUp.setEnabled(not not self.right_terminals)
        self.ui.rightDown.setEnabled(not not self.right_terminals)

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
    widget = None
