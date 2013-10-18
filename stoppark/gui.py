# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QWidget, QApplication

class Main(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        uiClass, qtBaseClass = uic.loadUiType('main.ui')
        self.ui = uiClass()
        self.ui.setupUi(self)

        self.ui.config.setup(self.ui.terminals, self.ui.payment)

        self.setWindowFlags(Qt.CustomizeWindowHint)

    def closeEvent(self, event):
        self.ui.terminals.closeEvent(event)
        self.ui.payment.closeEvent(event)
        self.ui.config.closeEvent(event)

if __name__ == '__main__':
    import sys
    import config
    config.setup_logging()

    app = QApplication(sys.argv)

    widget = Main()
    widget.showMaximized()

    sys.exit(app.exec_())
