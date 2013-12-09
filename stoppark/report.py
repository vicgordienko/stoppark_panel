# -*- coding: utf-8 -*-
from datetime import datetime
from config import DATETIME_USER_FORMAT, LOCAL_DATETIME_FORMAT


class Report(object):

    def __init__(self, db):
        self.db = db
        self.begin = '?'
        session = self.db.local.session()
        if session is not None:
            _, _, self.begin, _ = session
            try:
                self.begin = datetime.strptime(self.begin, LOCAL_DATETIME_FORMAT).strftime(DATETIME_USER_FORMAT)
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
        #self.ticket_moved_out = db.local.query('select count(*) from events '
        #                                       'where Direction="наружу" and EventName="проезд'
        #                                       'and Card is not null"')[0][0]

    def __unicode__(self):
        return u'Сумма в кассе: %i грн.\n' \
               u'Въехало: %i\n' \
               u'Выехало всего: %i\n' \
               u'Выехало по карточкам: %i\n' % (self.sum, self.moved_in,
                                                self.moved_out, self.card_moved_out)

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
            footer = u'Зміну здав: %s\n<c>***ЗМІНУ ЗАВЕРШЕНО***</c>' % (cashier,)
        else:
            footer = u'<c>***ТИМЧАСОВИЙ ЗВІТ***</c>'

        return u'\n'.join([
            self.header + u'<c><s>Звіт за період</s></c>\n',
            u'з  %s' % (self.begin,),
            u'по %s' % (datetime.now().strftime(DATETIME_USER_FORMAT),),
            u'паркомісць разом: %i' % (self.total_places,),
            u'         вільних: %i' % (self.free_places,),
            u'         в\'їздів: %i' % (self.moved_in,),
            u'         виїздів: %i' % (self.moved_out,),
            u'         разових: %i' % (self.moved_out - self.card_moved_out,),
            u'       постійних: %i' % (self.card_moved_out,),
            u'',
            u'     Сума в касі: %i грн.' % (self.sum,),
            u'',
            footer,
            u'<hr />'
        ])


if __name__ == '__main__':
    import doctest
    doctest.testmod()



