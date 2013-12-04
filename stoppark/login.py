# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtGui import QDialog


class LoginDialog(QDialog):
    def __init__(self, card, parent=None):
        QDialog.__init__(self, parent)

        self.ui = uic.loadUiType('login.ui')[0]()
        self.ui.setupUi(self)
        self.ui.progress.setVisible(False)
        self.ui.print_check.setVisible(False)
        self.setWindowTitle(u'Начало смены')
        self.ui.question.setText(u'Начать смену?')

        self.ui.info.setText(self.generate_info(card))

        self.ui.yes.clicked.connect(self.accept)
        self.ui.no.clicked.connect(self.reject)

    @staticmethod
    def generate_info(card):
        return u'Карточка %s\n%s' % (card.sn, card.fio)


class LogoffDialog(QDialog):
    def __init__(self, card, reader, parent=None):
        QDialog.__init__(self, parent)

        self.reader = reader
        self.card = card
        self.report = None

        self.ui = uic.loadUiType('login.ui')[0]()
        self.ui.setupUi(self)
        self.ui.print_check.setVisible(False)
        self.setWindowTitle(u'Завершение смены')
        self.ui.question.setText(u'Завершить смену?')

        self.ui.info.setText(self.generate_info(card))

        self.ui.yes.clicked.connect(self.accept)
        self.ui.no.clicked.connect(self.reject)

        self.reader.report.connect(self.handle_report)
        self.reader.generate_report()

    @staticmethod
    def generate_info(card, report=None):
        report = unicode(report) if report else u'Отчет генерируется...'
        return u'Карточка %s\n%s\n\n%s' % (card.sn, card.fio, report)

    def handle_report(self, report):
        print 'handle_report', report
        self.ui.progress.setVisible(False)
        self.reader.report.disconnect(self.handle_report)

        self.report = report
        self.ui.info.setText(self.generate_info(self.card, self.report))
        self.ui.print_check.setVisible(True)
