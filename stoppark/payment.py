# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty


class Payment(QObject):
    def __init__(self, container=None):
        QObject.__init__(self)
        if container is not None:
            container.append(self)

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        print 'Default Payment.enabled', self
        return False

    @pyqtProperty(int, constant=True)
    def price(self):
        print 'Default Payment.price', self
        return 0

    @pyqtProperty(str, constant=True)
    def explanation(self):
        print 'Default Payment.explanation', self
        return u'Default Payment Explanation'

    def vfcd_explanation(self):
        print 'Default Payment.vfcd_explanation', self
        return [u'Default explanation']*2

    def execute(self, db):
        print 'Default Payment.execute with', self, db

    def check(self, db):
        return db.get_check_header() + u'<c><b>П А Р К У В А Л Ь Н И Й  Т А Л О Н</b></c>\n\n'