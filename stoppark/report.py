# -*- coding: utf-8 -*-
from datetime import datetime
from config import DATETIME_FORMAT_USER, LOCAL_DATETIME_FORMAT
from i18n import language
_ = language.ugettext


class Report(object):

    def __init__(self, db):
        self.db = db
        self.begin = '?'
        session = self.db.local.session()
        if session is not None:
            _, _, self.begin, _ = session
            try:
                self.begin = datetime.strptime(self.begin, LOCAL_DATETIME_FORMAT).strftime(DATETIME_FORMAT_USER)
            except ValueError:
                pass

        self.header = self.db.get_check_header()
        self.total_places = self.db.get_total_places()
        self.free_places = self.db.get_free_places()

        self.sum = db.local.query('select sum(summa)/100 from payment')[0][0]
        if self.sum is None:
            self.sum = 0
        self.moved_in = db.local.query('select count(*) from events where Direction="внутрь" and EventName="проезд"')[0][0]
        self.moved_out = db.local.query('select count(*) from events '
                                        'where Direction="наружу" and EventName="проезд"')[0][0]
        self.card_moved_out = db.local.query('select count(*) from events '
                                             'where Direction="наружу" and EventName="проезд"'
                                             'and Card is not null')[0][0]
        self.ticket_moved_out = self.moved_out - self.card_moved_out

    def __unicode__(self):
        return _('Cash: ${self.sum}\n'
                 'Moved inside: %{self.moved_in}\n'
                 'Moved outside: %{self.moved_out}\n'
                 'Moved outside using card: %{self.card_moved_out}\n').format(self=self)

    def check(self, cashier=None):
        """
        >>> from db import DB
        >>> report = Report(DB()) #doctest:+ELLIPSIS
        0...
        0...
        >>> report.check() #doctest:+ELLIPSIS
        u...
        """
        if cashier is not None:
            footer = _('Session completed by: %s\n<c>***SESSION COMPLETED***</c>') % (cashier,)
        else:
            footer = _('<c>TEMPORARY REPORT</c>')

        return (self.header +
                _('<c><s>Report on period</s></c>\n'
                 '\n'
                 'from {self.begin}\n'
                 'to {now}\n'
                 'all places: {self.total_places}\n'
                 '      free: {self.free_places}\n'
                 '        in: {self.moved_in}\n'
                 '       out: {self.moved_out}\n'
                 '   tickets: {self.ticket_moved_out}\n'
                 '     cards: {self.card_moved_out}\n'
                 '\n'
                 '       Sum: {self.sum}\n'
                 '\n').format(self=self, now=datetime.now().strftime(DATETIME_FORMAT_USER)) +
                footer + u'\n<hr />')


if __name__ == '__main__':
    import doctest
    doctest.testmod()



