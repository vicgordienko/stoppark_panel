class Report(object):
    def __init__(self, db):
        self.sum = db.query('select sum(summa) from payment')[0]
        self.moved_in = db.query('select count(*) from events where Direction="внутрь" and EventName="проезд"')[0]
        self.moved_out = db.query('select count(*) from events where Direction="наружу" and EventName="проезд"')[0]

