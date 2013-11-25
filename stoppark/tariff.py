# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty
from math import ceil, floor
from datetime import datetime, timedelta


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
            self.cost = fields[4].split(' ')
        self.zero_time = [int(i, 10) for i in fields[5].split(':')] if fields[5] != 'None' else None
        self.max_per_day = fields[6]
        self._note = fields[7].decode('utf8')

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
    def costInfo(self):
        return str(self.cost) if isinstance(self.cost, int) else ','.join([str(cost) for cost in self.cost[:3]]) + '...'

    @pyqtProperty(str, constant=True)
    def note(self):
        return self._note

    @pyqtProperty(str, constant=True)
    def zeroTime(self):
        return ':'.join(['%02i' % (t,) for t in self.zero_time]) if self.zero_time else u''


class TariffResult(object):
    def __init__(self, delta, units=0.0, cost=0.0, max_per_day=None):
        """
        max_per_day parameter should only be present for  tariffs with hour interval.
        It activates minimization algorithm

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

    def __str__(self):
        return u'Единиц оплаты: %f' % (self.units,)

    def __repr__(self):
        return str((self.days, self.hours, self.minutes, self.units, self.price))


@Tariff.register(Tariff.FIXED)
class FixedTariff(Tariff):
    """
    >>> tariff = FixedTariff(['1', 'Час 1 грн.', '1', '1', '1', 'None', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,10,0))
    (0, 0, 10, 0.0, 0.0)
    >>> tariff.calc(datetime(2013,10,28,11,0,0), datetime(2013,10,28,11,45,0))
    (0, 0, 45, 1.0, 1.0)
    >>> tariff.calc(datetime(2013,10,28,9,0,0), datetime(2013,10,28,14,45,0))
    (0, 5, 45, 6.0, 6.0)
    >>> tariff = FixedTariff(['1', 'Час 1 грн. X', '1', '2', '1', '09:00', 'None', 'None'])
    >>> tariff.calc(datetime(2013,10,26,8,0,0), datetime(2013,10,28,11,10,0))
    (2, 3, 10, 4.0, 4.0)
    """

    FREE_TIME = 60*15

    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def _calc_a(self, begin, end):
        delta = end - begin
        seconds = delta.total_seconds()
        if seconds < self.FREE_TIME:
            return TariffResult(delta)
        units = ceil((seconds - self.FREE_TIME) / Tariff.DIVISORS[self.interval])
        return TariffResult(delta, units, self.cost)

    def calc(self, begin, end):
        if self.interval == Tariff.DAILY and self.zero_time:
            pivot = begin.replace(hour=self.zero_time[0], minute=self.zero_time[1], second=0)
            if pivot < begin:
                pivot += timedelta(days=1)
            if pivot > end:
                return self._calc_a(begin, end)
            unit_diff = 1 if (pivot - begin).total_seconds() > self.FREE_TIME else 0
            result = self._calc_a(pivot, end)
            return TariffResult(end - begin, result.units + unit_diff, self.cost)
        else:
            return self._calc_a(begin, end)


@Tariff.register(Tariff.ONCE)
class OnceTariff(Tariff):
    def __init__(self, fields):
        Tariff.__init__(self, fields)

    def execute(self):
        print 'OnceTariff.execute'


if __name__ == '__main__':
    import doctest
    doctest.testmod()