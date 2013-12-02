# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty, pyqtSlot
from math import ceil, floor
from datetime import datetime, timedelta, date
from calendar import monthrange
from itertools import cycle, izip
from config import DATE_USER_FORMAT


class Tariff(QObject):
    HOURLY = 1
    DAILY = 2
    MONTHLY = 3

    DIVISORS = {
        HOURLY: 60*60,
        DAILY: 60*60*24,
        MONTHLY: 60*60*24*30
    }

    FIXED = 1
    DYNAMIC = 2
    ONCE = 3
    PREPAID = 5
    SUBSCRIPTION = 6

    TYPES = {}

    @staticmethod
    def register(identifier):
        def wrapper(cls):
            Tariff.TYPES[identifier] = cls
            return cls
        return wrapper

    @staticmethod
    def create(response):
        try:
            assert(len(response) >= 8)
            return Tariff.TYPES.get(int(response[2]), Tariff)(response)
        except (ValueError, TypeError, AssertionError):
            return False

    def __init__(self, fields):
        QObject.__init__(self)
        self.fields = fields

        self._id = int(fields[0])
        self._title = fields[1].decode('utf8')
        self._type = int(fields[2])
        self._interval = int(fields[3])
        try:
            self.cost = int(fields[4])
        except ValueError:
            self.cost = [int(i) for i in fields[4].split(' ')]
        self.zero_time = [int(i, 10) for i in fields[5].split(':')] if fields[5] != 'None' else None
        self.max_per_day = int(fields[6]) if fields[6] != 'None' else None
        self._note = fields[7].decode('utf8')

    FREE_TIME = 60*15

    def calc_units(self, begin, end):
        """
        @param begin: datetime, beginning of calculation interval
        @param end: datetime, end of calculation interval
        @return: tuple of time delta between input parameters
                 and unit count for it (taking tariff interval in account).
        @rtype : tuple
        """
        delta = end - begin
        seconds = delta.total_seconds()
        if seconds < Tariff.FREE_TIME:
            return delta, 0
        return delta, int(ceil((seconds - Tariff.FREE_TIME) / Tariff.DIVISORS[self.interval]))

    #def __del__(self):
    #    print '~Tariff'

    @pyqtProperty(int, constant=True)
    def id(self):
        return self._id

    @pyqtProperty(str, constant=True)
    def title(self):
        return self._title

    @pyqtProperty(int, constant=True)
    def type(self):
        return self._type

    @pyqtProperty(int, constant=True)
    def interval(self):
        return self._interval

    @pyqtProperty(str, constant=True)
    def intervalStr(self):
        if self.type == Tariff.ONCE:
            return u'за раз'
        return {Tariff.HOURLY: u'час', Tariff.DAILY: u'сутки', Tariff.MONTHLY: u'месяц'}[self.interval]

    @pyqtProperty(str, constant=True)
    def costInfo(self):
        return str(self.cost) if isinstance(self.cost, int) else ','.join([str(cost) for cost in self.cost[:3]]) + '...'

    @pyqtProperty(str, constant=True)
    def note(self):
        return self._note

    @pyqtProperty(str, constant=True)
    def zeroTime(self):
        return ':'.join(['%02i' % (t,) for t in self.zero_time]) if self.zero_time is not None else u''

    @pyqtProperty(int, constant=True)
    def maxPerDay(self):
        return self.max_per_day if self.max_per_day is not None else -1


class FixedTariffResult(object):
    def __init__(self, delta, units=0, cost=0.0, max_per_day=None):
        """
        To activate price minimization algorithm, max_per_day argument must be present.
        This argument has any sense only when its applied to hourly tariff.
        """
        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units
        self.cost = cost

        self.price = self.units * cost
        if max_per_day is not None and self.price > max_per_day:
            cost_per_day = min(max_per_day, cost*24)
            self.price = cost_per_day * (self.units / 24)
            self.price += min((self.units % 24)*cost, max_per_day)

    def __unicode__(self):
        return u'Единиц оплаты: %i' % (self.units,)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.price))


@Tariff.register(Tariff.FIXED)
class FixedTariff(Tariff):
    """
    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0, 0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1, 1)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6, 6)
    >>> tariff = Tariff.create(['1', 'Час 1 грн. X', '1', '2', '1', '09:00', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 4, 4)
    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', '100', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, 57)
    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', '10', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, 29)
    """

    def __init__(self, fields):
        Tariff.__init__(self, fields)
        self.result_class = FixedTariffResult

    def calc_basis(self, begin, end):
        return FixedTariffResult(*self.calc_units(begin, end), cost=self.cost, max_per_day=self.max_per_day)

    def calc_daily_zero_time(self, begin, end):
        pivot = begin.replace(hour=self.zero_time[0], minute=self.zero_time[1], second=0)
        if pivot < begin:
            pivot += timedelta(days=1)
        if pivot > end:
            return self.calc_basis(begin, end)
        unit_diff = 1 if (pivot - begin).total_seconds() > self.FREE_TIME else 0
        _, units = self.calc_units(pivot, end)
        return FixedTariffResult(end - begin, units + unit_diff, self.cost)

    def calc(self, begin, end):
        if self.interval == Tariff.DAILY and self.zero_time:
            return self.calc_daily_zero_time(begin, end)
        else:
            return self.calc_basis(begin, end)


class DynamicTariffResult(object):
    def __init__(self, delta, units=0, cost=None, max_per_day=None):
        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units

        self.price = sum(price for _, price in izip(xrange(int(units)), cycle(cost)))
        if max_per_day is not None and self.price > max_per_day:
            cost_per_day = min(max_per_day, sum(cost))
            self.price = cost_per_day * (self.units / 24)
            self.price += min(max_per_day, sum(price for _, price in izip(xrange(int(self.units % 24)), cycle(cost))))
        self.cost = self.price

    def __unicode__(self):
        return u'Единиц оплаты: %i' % (self.units,)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.price))


@Tariff.register(Tariff.DYNAMIC)
class DynamicTariff(Tariff):
    """
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0, 0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1, 1)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6, 21)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 51, 606)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', '100', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, 245)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', '10', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, 30)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def calc(self, begin, end):
        return DynamicTariffResult(*self.calc_units(begin, end), cost=self.cost, max_per_day=self.max_per_day)


@Tariff.register(Tariff.ONCE)
class OnceTariff(Tariff):
    def __init__(self, fields):
        Tariff.__init__(self, fields)


class SubscriptionTariffResult(object):
    def __init__(self, begin, end, cost, units=1):
        self.begin = begin
        self.end = end
        self.units = units
        self.cost = cost
        self.price = self.units * self.cost

    def __repr__(self):
        return str((self.begin, self.end, self.units, self.cost, self.price))

    def __unicode__(self):
        return u'После пополнения: от %s до %s' % (self.begin.strftime(DATE_USER_FORMAT),
                                                   self.end.strftime(DATE_USER_FORMAT))


def days_in_month(d):
    """
    @rtype : int
    @param d: datetime.date
    @return: number of days in a month, specified by date
    """
    return monthrange(d.year, d.month)[1]


@Tariff.register(Tariff.SUBSCRIPTION)
class SubscriptionTariff(Tariff):
    """
    >>> tariff = Tariff.create(['3', '', '6', '3', '100', 'None', 'None', 'None'])

    >>> today = date.today()
    >>> month_begin = date(today.year, today.month, 1)
    >>> month_end = date(today.year, today.month, days_in_month(today))

    # Lets use some far away date in the past to test the second algorithm branch
    >>> A = tariff.calc(date(1980,10,1), date(1980,10,15))
    >>> A.begin == month_begin , A.end == month_end, A.cost
    (True, True, 100)

    Incorrect end date results in no result
    >>> tariff.calc(month_begin, month_end - timedelta(days=1))

    Having an active card at the moment of refill results in extending of activity period
    >>> B = tariff.calc(month_begin, month_end)
    >>> B.begin == month_begin, B.end == month_end + timedelta(days=1+days_in_month(month_end + timedelta(days=1)))
    (True, True)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            if days_in_month(end) == end.day:
                new_end = end + timedelta(days=1)
                new_end += timedelta(days=days_in_month(new_end))
                return SubscriptionTariffResult(begin, new_end, self.cost)
        else:
            new_begin = today - timedelta(days=today.day - 1)
            new_end = new_begin + timedelta(days=days_in_month(today) - 1)
            return SubscriptionTariffResult(new_begin, new_end, self.cost)


class PrepaidTariffResult(object):
    def __init__(self, begin, end, cost, units=1):
        self.begin = begin
        self.end = end
        self.units = units
        self.cost = cost
        self.price = self.units * self.cost

    def __repr__(self):
        return str((self.begin, self.end, self.units, self.cost, self.price))

    def __unicode__(self):
        return u'Пополнение на %i дней.\n' \
               u'После пополнения: от %s до %s.' % (self.units,
                                                    self.begin.strftime(DATE_USER_FORMAT),
                                                    self.end.strftime(DATE_USER_FORMAT))


@Tariff.register(Tariff.PREPAID)
class PrepaidTariff(Tariff):
    """
    >>> cost = 100
    >>> tariff = Tariff.create(['4', '', '5', '2', str(cost), 'None', 'None', 'None'])

    >>> today = date.today()
    >>> month_end = date(today.year, today.month, days_in_month(today))
    >>> month_begin = date(today.year, today.month, 1)

    # Lets use some far away date in the past to test the second algorithm branch
    >>> A = tariff.calc(date(1980,10,1), date(1980,10,15))
    >>> A.begin == today , A.end == month_end, A.price == cost * (month_end - today).days
    (True, True, True)

    Card that has been refilled up to the end of month, should currently be unavailable for refill by PrepaidContract
    >>> tariff.calc(today, month_end)

    Having an active card at the moment of refill results in extending of activity period
    up to the end of month, that end date belongs to.
    Note: this test will fail during the final days of their months.
    >>> B = tariff.calc(month_begin, today)
    >>> B.begin == month_begin, B.end == month_end, B.units == (month_end - today).days
    (True, True, True)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            units = days_in_month(end) - end.day
            if units:
                return PrepaidTariffResult(begin, end + timedelta(days=units), self.cost, units)
        else:
            units = days_in_month(today) - today.day
            return PrepaidTariffResult(today, today + timedelta(days=units), self.cost, units)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

