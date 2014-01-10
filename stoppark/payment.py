# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty
from i18n import language
_ = language.ugettext


class Payment(QObject):
    """
    This is a base implementation of Payment concept.
    Payments are results of Payable.pay method execution.

    As such, for every payable concept in system there should be at least one payment.

    Payments are usually specific to their payable object and provide a way for them
    to interact with user giving him some payment for every any tariff given to `pay` method.

    Payments provide explanations for customer about themselves using `explanation` property.

    There are two types of payments: enabled and disabled.
    Enabled payments must provide full stack of methods with appropriate implementation,
    while disabled payments should only provide explanation.

    Usual scenario of payment lifetime includes creation, selecting by customer,
    showing its explanation, checking if its enabled and executing when user decides to do so.
    `execute` and `check` methods are final methods in this sequence.
    """

    def __init__(self, container=None):
        """
        Constructs this payment as QObject and appends itself to provided container.
        @param container: list, container to put self into
        """
        QObject.__init__(self)
        if container is not None:
            container.append(self)

    @pyqtProperty(bool, constant=True)
    def enabled(self):
        """
        This property decides if payment is worthy to be payed.
        When True, all other methods MUST be present and implemented correctly.
        When False, only explanation property is necessary.
        """
        print 'Default Payment.enabled', self
        return False

    @pyqtProperty(int, constant=True)
    def price(self):
        """
        This property shows full price of its payment.
        """
        print 'Default Payment.price', self
        return 0

    @pyqtProperty(str, constant=True)
    def price_info(self):
        """
        This property returns text information about payment price.
        """
        return _('Price: $%i') % (self.price,)

    @pyqtProperty(str, constant=True)
    def explanation(self):
        """
        This property holds a text explanation for its payment, according to its internal logic.
        """
        print 'Default Payment.explanation', self
        return u'Default Payment Explanation'

    def vfcd_explanation(self):
        """
        This method generates advice strings to be showed on Vacuum Fluorescent Customer Display.
        @return: list of two unicode strings
        """
        print 'Default Payment.vfcd_explanation', self
        return [u'Default explanation']*2

    def execute(self, db):
        """
        This method executes its payment
        @param db: db.DB, database instance to perform execution at.
        @return: None or bool
        """
        print 'Default Payment.execute with', self, db

    def check(self, db):
        """
        This method returns text representation of payment check to be printed.
        Implementation, provided here, can be used as a basis for other payments,
        since it generates correct header, that applies to every payment check.
        @param db: db.DB, database instance to be used in check generation.
        @return: unicode
        """
        return db.get_check_header() + _('<c><b>P A R K I N G  T I C K E T</b></c>\n\n')