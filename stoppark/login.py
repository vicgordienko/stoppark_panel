# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtGui import QDialog
from i18n import language
_ = language.ugettext


class LoginDialog(QDialog):
    def __init__(self, card, parent=None):
        QDialog.__init__(self, parent)

        self.ui = uic.loadUiType('login.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.ui.progress.setVisible(False)
        self.ui.print_check.setVisible(False)
        self.ui.info.setText(self.generate_info(card))

        self.ui.yes.clicked.connect(self.accept)
        self.ui.no.clicked.connect(self.reject)

    def localize(self):
        self.setWindowTitle(_('Session begin'))
        self.ui.operatorGroup.setTitle(_('Operator'))
        self.ui.question.setText(_('Begin session?'))
        self.ui.yes.setText(_('Yes'))
        self.ui.no.setText(_('No'))

    @staticmethod
    def generate_info(card):
        return _('Card #%(id)s\n%(fio)s\n') % {
            'id': card.id,
            'fio': card.fio
        }


class LogoffDialog(QDialog):
    def __init__(self, card, reader, parent=None):
        QDialog.__init__(self, parent)

        self.reader = reader
        self.card = card
        self.report = None

        self.ui = uic.loadUiType('login.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.ui.print_check.setVisible(False)
        self.ui.info.setText(self.generate_info(card))

        self.ui.yes.clicked.connect(self.accept_logoff)
        self.ui.no.clicked.connect(self.reject)

        self.reader.report.connect(self.handle_report)
        self.ui.print_check.clicked.connect(self.print_check)
        self.reader.generate_report()

    def localize(self):
        self.setWindowTitle(_('Session end'))
        self.ui.operatorGroup.setTitle(_('Operator'))
        self.ui.print_check.setText(_('Print temporary report'))
        self.ui.question.setText(_('End session?'))
        self.ui.yes.setText(_('Yes'))
        self.ui.no.setText(_('No'))

    def accept_logoff(self):
        self.reader.to_printer(self.report.check(cashier=self.card.fio_short))
        self.accept()

    @staticmethod
    def generate_info(card, report=None):
        report = unicode(report) if report else _('Report generation...')
        return _('Card #%(id)s\n%(fio)s\n\n%(report)s') % {
            'id': card.id,
            'fio': card.fio,
            'report': report
        }

    def print_check(self):
        self.reader.to_printer(self.report.check())

    def handle_report(self, report):
        print 'handle_report', report
        self.ui.progress.setVisible(False)
        self.reader.report.disconnect(self.handle_report)

        self.report = report
        self.ui.info.setText(self.generate_info(self.card, self.report))
        self.ui.print_check.setVisible(True)
