# -*- coding: utf-8 -*-


class Report(object):
    def __init__(self, db):
        self.sum = db.query('select sum(summa)/100 from payment')[0][0]
        if self.sum is None:
            self.sum = 0
        self.moved_in = db.query('select count(*) from events where Direction="внутрь" and EventName="проезд"')[0][0]
        self.moved_out = db.query('select count(*) from events where Direction="наружу" and EventName="проезд"')[0][0]

    def __unicode__(self):
        return u'Сумма в кассе: %i грн.\nВъехало: %i\nВыехало: %i' % (self.sum, self.moved_in, self.moved_out)

