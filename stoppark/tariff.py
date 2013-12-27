# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty
from math import ceil, floor
from datetime import datetime, timedelta, date
from calendar import monthrange
from itertools import cycle, izip
from config import DATE_USER_FORMAT


class Tariff(QObject):
    """
    This is a base class for all tariffs in stoppark.
    Most Tariff-related constants are stored as class variables of this class.
    """
    HOURLY = 1
    DAILY = 2
    MONTHLY = 3

    DIVISORS = {
        HOURLY: 60*60,
        DAILY: 60*60*24,
        MONTHLY: 60*60*24*30  # TODO: sad, but month is not a fixed-time interval in our calendar
    }

    FIXED = 1
    DYNAMIC = 2
    ONCE = 3
    PREPAID = 5
    SUBSCRIPTION = 6

    FREE_TIME = 60*15

    TYPES = {}

    @staticmethod
    def register(identifier):
        """
        This methods registers Tariff descendants for further usage in Tariff.create
        @param identifier: int, key to identify classes for this decorator
        @return: decorator for Tariff-based class
        """
        def wrapper(cls):
            Tariff.TYPES[identifier] = cls
            return cls
        return wrapper

    @staticmethod
    def create(response):
        """
        Initializes Tariff instance using response from remote database.
        @param response: response from remote database query that fetches tariff information
                         currently, it must be a list of string lists with a complete set of fields from Tariff table.
        @return: Tariff descendant instance when all conditions have been met.
                 False when remote response is False
                 None when some condition was not satisfied during preliminary check.
        """
        if response is False:
            return False
        try:
            assert(len(response) >= 8)
            return Tariff.TYPES[int(response[2])](response)
        except (TypeError, AssertionError, IndexError, ValueError, KeyError):
            return None

    def __init__(self, fields):
        QObject.__init__(self)
        self.fields = fields

        self._id = int(fields[0])
        self._title = fields[1].decode('utf8', errors='replace')

        self._type = int(fields[2])
        if self._type not in Tariff.TYPES.keys():
            raise KeyError("There is no such tariff type: %i" % (self._type,))

        self._interval = int(fields[3])
        if self._interval not in Tariff.DIVISORS.keys():
            raise KeyError("There is no such interval: %i" % (self._interval,))

        try:
            self.cost = int(fields[4])
        except ValueError:
            self.cost = [int(i) for i in fields[4].split(' ')]

        if fields[5] != 'None':
            self.zero_time = [int(i, 10) for i in fields[5].split(':')]
            if len(self.zero_time) != 2:
                raise IndexError("Incorrect zero time: %s" % (fields[5]))
        else:
            self.zero_time = None

        self.max_per_day = int(fields[6]) if fields[6] != 'None' else None
        self._note = fields[7].decode('utf8', errors='replace')

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

    def paid_time(self, units):
        return timedelta(seconds=units * Tariff.DIVISORS[self.interval])

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

    @property
    def cost_db(self):
        return str(self.cost*100) if isinstance(self.cost, int) else ''

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
    def __init__(self, tariff,  delta, units, extra_time=None, extra_units=None):
        """
        @param tariff: mandatory, Tariff
        @param delta: mandatory, datetime.timedelta
                      time interval, that is being paid for
        @param units: number of paid units,
                      this parameter will be used as a base value for calculation paid_time and price
        @param extra_time: optional, datetime.timedelta
                           provides a way to add some extra paid_time to the time determined by units
        @param extra_units: optional, int
                            provides a way to add some extra units, that will not affect paid_time
        """
        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units
        self.paid_time = tariff.paid_time(self.units) + (extra_time if extra_time is not None else timedelta(0))
        if extra_units is not None:
            self.units += extra_units
        self.cost = tariff.cost

        self.price = self.units * tariff.cost
        if tariff.interval == Tariff.HOURLY and tariff.max_per_day is not None and self.price > tariff.max_per_day:
            cost_per_day = min(tariff.max_per_day, tariff.cost*24)
            self.price = cost_per_day * (self.units / 24)
            self.price += min((self.units % 24)*tariff.cost, tariff.max_per_day)

    def add_units(self, units):
        self.units += units
        self.price += units * self.cost

    @property
    def interval_u(self):
        return u'%i доб. %i год. %i хв.' % (self.days, self.hours, self.minutes)

    @property
    def interval(self):
        return u'%i дн. %i час. %i мин.' % (self.days, self.hours, self.minutes)

    def __unicode__(self):
        return u'Единиц оплаты: %i' % (self.units,)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.paid_time, self.price))


@Tariff.register(Tariff.FIXED)
class FixedTariff(Tariff):
    """
    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0, datetime.timedelta(0), 0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6, datetime.timedelta(0, 21600), 6)
    >>> tariff.calc(datetime(2013,12,1,9,0,0), datetime(2013,12,2,10,0,0))
    (1, 1, 0, 25, datetime.timedelta(1, 3600), 25)
    >>> tariff.calc(datetime(2013,12,1,23,55,0), datetime(2013,12,2,3,25,0))
    (0, 3, 30, 4, datetime.timedelta(0, 14400), 4)
    >>> tariff.calc(datetime(2014,2,28,23,30,0), datetime(2014,3,1,4,0,0))
    (0, 4, 30, 5, datetime.timedelta(0, 18000), 5)
    >>> tariff.calc(datetime(2008,2,28,23,30,0), datetime(2008,2,29,2,0,0))
    (0, 2, 30, 3, datetime.timedelta(0, 10800), 3)
    >>> tariff.calc(datetime(2008,2,28,23,30,0), datetime(2008,3,1,2,0,0))
    (1, 2, 30, 27, datetime.timedelta(1, 10800), 27)
    >>> tariff.calc(datetime(2013,11,30,23,55,0), datetime(2013,12,1,0,5,0))
    (0, 0, 10, 0, datetime.timedelta(0), 0)
    >>> tariff.calc(datetime(2013,10,30,23,50,0), datetime(2013,10,31,1,0,0))
    (0, 1, 10, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,9,30,22,0,0), datetime(2013,10,1,9,0,0))
    (0, 11, 0, 11, datetime.timedelta(0, 39600), 11)
    >>> tariff.calc(datetime(2013,10,31,22,0,0), datetime(2013,11,1,9,0,0))
    (0, 11, 0, 11, datetime.timedelta(0, 39600), 11)
    >>> tariff.calc(datetime(2013,11,30,23,0,0), datetime(2013,12,1,8,0,0))
    (0, 9, 0, 9, datetime.timedelta(0, 32400), 9)
    >>> tariff.calc(datetime(2013,12,9,9,0,0), datetime(2014,12,10,9,0,0))
    (366, 0, 0, 8784, datetime.timedelta(366), 8784)
    >>> tariff.calc(datetime(2013,12,9,23,0,0), datetime(2014,1,10,23,0,0))
    (32, 0, 0, 768, datetime.timedelta(32), 768)
    >>> tariff.calc(datetime(2013,12,31,23,59,59), datetime(2014,1,1,1,0,0))
    (0, 1, 0, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,12,9,10,0,0), datetime(2013,12,9,10,15,1))
    (0, 0, 15, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,10,26,23,0,0), datetime(2013,10,27,1,0,0))
    (0, 2, 0, 2, datetime.timedelta(0, 7200), 2)
    >>> tariff.calc(datetime(2013,10,24,9,0,0), datetime(2013,10,21,10,0,0))
    (-3, 1, 0, 0, datetime.timedelta(0), 0)
    >>> tariff.calc(datetime(2013,10,24,9,0,0), datetime(2013,10,24,8,50,0))
    (-1, 23, 50, 0, datetime.timedelta(0), 0)

    >>> tariff = Tariff.create(['1', 'Час 1 грн. X', '1', '2', '1', '09:00', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 4, datetime.timedelta(3, 3600), 4)
    >>> tariff.calc(datetime(2013,12,9,11,0,0), datetime(2013,12,10,8,0,0))
    (0, 21, 0, 1, datetime.timedelta(0, 79200), 1)
    >>> tariff.calc(datetime(2013,11,30,8,0,0), datetime(2013,12,1,9,0,0))
    (1, 1, 0, 2, datetime.timedelta(1, 3600), 2)
    >>> tariff.calc(datetime(2008,2,28,16,0,0), datetime(2008,2,29,16,10,0))
    (1, 0, 10, 2, datetime.timedelta(1, 61200), 2)
    >>> tariff.calc(datetime(2008,2,28,8,0,0), datetime(2008,3,1,10,0,0))
    (2, 2, 0, 4, datetime.timedelta(3, 3600), 4)
    >>> tariff.calc(datetime(2014,2,27,9,0,0), datetime(2014,3,1,10,10,0))
    (2, 1, 10, 3, datetime.timedelta(3), 3)
    >>> tariff.calc(datetime(2013,12,31,23,0,0), datetime(2014,1,1,9,5,0))
    (0, 10, 5, 1, datetime.timedelta(0, 36000), 1)
    >>> tariff.calc(datetime(2013,12,9,8,0,0), datetime(2013,12,9,8,50,0))
    (0, 0, 50, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,12,9,9,0,0), datetime(2014,1,10,11,10,0))
    (32, 2, 10, 33, datetime.timedelta(33), 33)
    >>> tariff.calc(datetime(2013,12,1,9,0,0), datetime(2014,11,1,10,10,0))
    (335, 1, 10, 336, datetime.timedelta(336), 336)
    >>> tariff.calc(datetime(2013,12,3,9,0,0), datetime(2013,12,1,9,0,0))
    (-2, 0, 0, 0, datetime.timedelta(0), 0)
    >>> tariff.calc(datetime(2013,10,24,9,0,0), datetime(2013,10,24,8,50,0))
    (-1, 23, 50, 0, datetime.timedelta(0), 0)

    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', '100', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, datetime.timedelta(2, 32400), 57)
    >>> tariff = Tariff.create(['1', 'Час 1 грн.', '1', '1', '1', 'None', '10', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, datetime.timedelta(2, 32400), 29)
    """

    def __init__(self, fields):
        Tariff.__init__(self, fields)
        self.result_class = FixedTariffResult

    def calc_basis(self, begin, end):
        return FixedTariffResult(self, *self.calc_units(begin, end))

    def calc_daily_zero_time(self, begin, end):
        pivot = begin.replace(hour=self.zero_time[0], minute=self.zero_time[1], second=0)
        if pivot < begin:
            pivot += timedelta(days=1)
        _, units = self.calc_units(pivot, end)
        extra_units = 1 if (pivot - begin).total_seconds() > Tariff.FREE_TIME else 0
        return FixedTariffResult(self, end - begin, units, extra_time=pivot - begin, extra_units=extra_units)

        #if pivot > end:
        #    return self.calc_basis(begin, end)
        #unit_diff = 1 if (pivot - begin).total_seconds() > self.FREE_TIME else 0
        #_, units = self.calc_units(pivot, end)
        #return FixedTariffResult(self, end - begin, units + unit_diff)

    def calc(self, begin, end):
        if self.interval == Tariff.DAILY and self.zero_time:
            return self.calc_daily_zero_time(begin, end)
        else:
            return self.calc_basis(begin, end)


class DynamicTariffResult(object):
    def __init__(self, tariff, delta, units, extra_time=None):
        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units
        self.paid_time = tariff.paid_time(self.units) + (extra_time if extra_time is not None else timedelta(0))

        self.price = sum(price for _, price in izip(xrange(int(units)), cycle(tariff.cost)))
        if tariff.max_per_day is not None and self.price > tariff.max_per_day:
            cost_per_day = min(tariff.max_per_day, sum(tariff.cost))
            self.price = cost_per_day * (self.units / 24)
            self.price += min(tariff.max_per_day, sum(price for _, price in izip(xrange(int(self.units % 24)),
                                                                                 cycle(tariff.cost))))
        self.cost = self.price

    @property
    def interval_u(self):
        return u'%i доб. %i год. %i хв.' % (self.days, self.hours, self.minutes)

    @property
    def interval(self):
        return u'%i дн. %i час. %i мин.' % (self.days, self.hours, self.minutes)

    def __unicode__(self):
        return u'Единиц оплаты: %i' % (self.units,)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.paid_time, self.price))


@Tariff.register(Tariff.DYNAMIC)
class DynamicTariff(Tariff):
    """
    This tariff can only have hour interval.
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0, datetime.timedelta(0), 0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1, datetime.timedelta(0, 3600), 1)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6, datetime.timedelta(0, 21600), 21)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 51, datetime.timedelta(2, 10800), 606)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', '100', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, datetime.timedelta(2, 32400), 245)
    >>> tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1,25)), 'None', '10', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,16,20,0))
    (2, 8, 20, 57, datetime.timedelta(2, 32400), 30)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)
        if self.interval != Tariff.HOURLY:
            raise ValueError("DynamicTariff can only be hourly.")

    def calc(self, begin, end):
        return DynamicTariffResult(self, *self.calc_units(begin, end))


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
    >>> B.begin == month_begin, B.end == month_end + timedelta(days=days_in_month(month_end + timedelta(days=1)))
    (True, True)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            if days_in_month(end) == end.day:
                new_end = end + timedelta(days=1)
                new_end += timedelta(days=days_in_month(new_end) - 1)
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
    >>> A.begin == today , A.end == month_end, A.price == cost * ((month_end - today).days + 1)
    (True, True, True)

    Card that has been refilled up to the end of month, should currently be unavailable for refill by PrepaidContract
    >>> tariff.calc(today, month_end)

    Having an active card at the moment of refill results in extending of activity period
    up to the end of month, that end date belongs to.
    Note: this test will fail during the final days of their months.
    >>> B = tariff.calc(month_begin, today)
    >>> B.begin == month_begin, B.end == month_end, B.units == (month_end - today).days + 1
    (True, True, True)
    """
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            units = days_in_month(end) - end.day
            if units:
                return PrepaidTariffResult(begin, end + timedelta(days=units), self.cost, units + 1)
        else:
            units = days_in_month(today) - today.day
            return PrepaidTariffResult(today, today + timedelta(days=units), self.cost, units + 1)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

