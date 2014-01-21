# coding=utf-8
from PyQt4.QtCore import QObject, pyqtProperty, pyqtSlot
from math import ceil, floor
from datetime import datetime, timedelta, date
from calendar import monthrange
from itertools import cycle, izip
from config import DATE_USER_FORMAT
from i18n import language

_ = language.ugettext
_n = language.ungettext

_n('unit_', 'units_', 1)
_n('hour_', 'hours_', 1)
_n('day_', 'days_', 1)
_n('month_', 'months_', 1)

_n('unit', 'units', 1)
_n('hour', 'hours', 1)
_n('day', 'days', 1)
_n('month', 'months', 1)

DEFAULT_FREE_TIME = 15


class Tariff(QObject):
    """
    This is a base class for all tariffs in stoppark.
    Most Tariff-related constants are stored as class variables of this class.
    """
    HOURLY = 1
    DAILY = 2
    MONTHLY = 3

    DIVISORS = {
        HOURLY: 60 * 60,
        DAILY: 60 * 60 * 24,
        MONTHLY: 60 * 60 * 24 * 30  # TODO: sad, but month is not a fixed-time interval in our calendar
    }

    FIXED = 1
    DYNAMIC = 2
    ONCE = 3
    PREPAID = 5
    SUBSCRIPTION = 6

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
    def create(response, free_time=None):
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
        if free_time is None:
            free_time = DEFAULT_FREE_TIME
        free_time *= 60
        try:
            assert (len(response) >= 8)
            return Tariff.TYPES[int(response[2])](response, free_time=free_time)
        except (TypeError, AssertionError, IndexError, ValueError, KeyError) as e:
            return None
            #import sys
            #import traceback
            #for line in traceback.format_exception(*sys.exc_info()):
            #    print line

    def __init__(self, fields, free_time=None):
        QObject.__init__(self)
        if free_time is None:
            free_time = DEFAULT_FREE_TIME * 60
        self.free_time = free_time
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
        if seconds < self.free_time:
            return delta, 0
        return delta, int(ceil((seconds - self.free_time) / Tariff.DIVISORS[self.interval]))

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

    @pyqtSlot(int, bool, result=str)
    def interval_str_check(self, units, include_number=False):
        if self.type == Tariff.ONCE:
            interval_base = ('unit_', 'units_')
        else:
            interval_base = {
                Tariff.HOURLY: ('hour_', 'hours_'),
                Tariff.DAILY: ('day_', 'days_'),
                Tariff.MONTHLY: ('month_', 'months_')
            }[self.interval]

        extra = u'%i ' % (units,) if include_number else u''
        return extra + _n(*(interval_base + (units,)))


    @pyqtSlot(int, bool, result=str)
    def interval_str(self, units, include_number=False):
        if self.type == Tariff.ONCE:
            interval_base = ('unit', 'units')
        else:
            interval_base = {
                Tariff.HOURLY: ('hour', 'hours'),
                Tariff.DAILY: ('day', 'days'),
                Tariff.MONTHLY: ('month', 'months')
            }[self.interval]

        extra = u'%i ' % (units,) if include_number else u''
        return extra + _n(*(interval_base + (units,)))

    @pyqtProperty(str, constant=True)
    def note(self):
        return self._note

    @pyqtProperty(str, constant=True)
    def cost_info_check(self):
        return _('$%(cost)s/%(interval)s') % {
            'cost': self.cost if isinstance(self.cost, int) else ','.join([str(c) for c in self.cost[:3]]) + '...',
            'interval': self.interval_str_check(1)
        }

    @pyqtProperty(str, constant=True)
    def cost_info(self):
        return _('$%(cost)s/%(interval)s') % {
            'cost': self.cost if isinstance(self.cost, int) else ','.join([str(c) for c in self.cost[:3]]) + '...',
            'interval': self.interval_str(1)
        }

    @pyqtProperty(str, constant=True)
    def cost_info(self):
        return _('$%(cost)s/%(interval)s') % {
            'cost': self.cost if isinstance(self.cost, int) else ','.join([str(c) for c in self.cost[:3]]) + '...',
            'interval': self.interval_str(1)
        }

    @property
    def cost_db(self):
        return str(self.cost * 100) if isinstance(self.cost, int) else ''

    @pyqtProperty(str, constant=True)
    def zero_time_info(self):
        if self.zero_time is not None:
            return _('Zero time: ') + ':'.join(['%02i' % (t,) for t in self.zero_time])
        else:
            return u''

    @pyqtProperty(str, constant=True)
    def max_per_day_info(self):
        return _('Max per day: $%i') % (self.max_per_day,) if self.max_per_day is not None else u''


class TicketTariffResult(object):
    """
    This is a base class for ticket tariff results
    It provides common methods and properties shared between its descendants.
    """

    def __init__(self):
        self.days = None
        self.hours = None
        self.minutes = None
        self.paid_time = None
        self.units = None
        self.price = None

    @property
    def check_duration(self):
        return u'%i %s %i %s %i %s' % (self.days, _n('day_', 'days_', self.days),
                                       self.hours, _n('hour_', 'hours_', self.hours),
                                       self.minutes, _n('minute_', 'minutes_', self.minutes))

    @property
    def duration(self):
        return u'%i %s %i %s %i %s' % (self.days, _n('day', 'days', self.days),
                                       self.hours, _n('hour', 'hours', self.hours),
                                       self.minutes, _n('minute', 'minutes', self.minutes))

    def __unicode__(self):
        return _('Duration: %(duration)s.\n'
                 'Payment units: %(units)i') % {
                   'duration': self.duration,
                   'units': self.units
               }

    def state(self):
        return self.days, self.hours, self.minutes, self.units, self.paid_time, self.price

    def __repr__(self):
        return str(self.state())


class FixedTariffResult(TicketTariffResult):
    def __init__(self, tariff, delta, units, extra_time=None, extra_units=None):
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
        super(FixedTariffResult, self).__init__()

        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units
        self.paid_time = tariff.paid_time(self.units) + (extra_time if extra_time is not None else timedelta(0))
        if extra_units is not None:
            self.units += extra_units
        if self.units == 0 or self.paid_time < delta:
            self.paid_time = delta
        self.cost = tariff.cost

        self.price = self.units * tariff.cost
        if tariff.interval == Tariff.HOURLY and tariff.max_per_day is not None and self.price > tariff.max_per_day:
            cost_per_day = min(tariff.max_per_day, tariff.cost * 24)
            self.price = cost_per_day * (self.units / 24)
            self.price += min((self.units % 24) * tariff.cost, tariff.max_per_day)


@Tariff.register(Tariff.FIXED)
class FixedTariff(Tariff):
    def __init__(self, fields, **kw):
        Tariff.__init__(self, fields, **kw)
        self.result_class = FixedTariffResult

    def calc_basis(self, begin, end):
        return FixedTariffResult(self, *self.calc_units(begin, end))

    def calc_daily_zero_time_extra(self, begin, end, pivot):
        return {
            'extra_time': pivot - begin,
            'extra_units': 1
        } if all((
            (end - begin).total_seconds() > self.free_time,
            (pivot - begin).total_seconds() > self.free_time
        )) else {}

    def calc_daily_zero_time(self, begin, end):
        pivot = begin.replace(hour=self.zero_time[0], minute=self.zero_time[1], second=0)
        if pivot < begin:
            pivot += timedelta(days=1)
        _, units = self.calc_units(pivot, end)
        return FixedTariffResult(self, end - begin, units, **self.calc_daily_zero_time_extra(begin, end, pivot))

    def calc(self, begin, end):
        if self.interval == Tariff.DAILY and self.zero_time:
            return self.calc_daily_zero_time(begin, end)
        else:
            return self.calc_basis(begin, end)


class DynamicTariffResult(TicketTariffResult):
    def __init__(self, tariff, delta, units, extra_time=None):
        super(DynamicTariffResult, self).__init__()

        self.days = delta.days
        self.hours = int(floor(delta.seconds / 3600))
        self.minutes = int(floor((delta.seconds % 3600) / 60))
        self.units = units
        if self.units == 0:
            self.paid_time = delta
        else:
            self.paid_time = tariff.paid_time(self.units) + (extra_time if extra_time is not None else timedelta(0))

        if self.paid_time < delta:
            self.paid_time = delta

        self.price = sum(price for _, price in izip(xrange(int(units)), cycle(tariff.cost)))
        if tariff.max_per_day is not None and self.price > tariff.max_per_day:
            cost_per_day = min(tariff.max_per_day, sum(tariff.cost))
            self.price = cost_per_day * (self.units / 24)
            self.price += min(tariff.max_per_day, sum(price for _, price in izip(xrange(int(self.units % 24)),
                                                                                 cycle(tariff.cost))))
        self.cost = self.price  # this value will then go to the database


@Tariff.register(Tariff.DYNAMIC)
class DynamicTariff(Tariff):
    """
    This tariff can only have hour interval.
    """

    def __init__(self, fields, **kw):
        Tariff.__init__(self, fields, **kw)
        if self.interval != Tariff.HOURLY:
            raise ValueError("DynamicTariff can only be hourly.")

    def calc(self, begin, end):
        return DynamicTariffResult(self, *self.calc_units(begin, end))


@Tariff.register(Tariff.ONCE)
class OnceTariff(Tariff):
    def __init__(self, fields, **kw):
        Tariff.__init__(self, fields, **kw)


class CardTariffResult(object):
    """
    Generally applicable card tariff result.
    Can be used with both Subscription and Prepaid tariffs.
    """

    def __init__(self, begin, end, cost, units=1):
        self.begin = begin
        self.end = end
        self.units = units
        self.cost = cost
        self.price = self.units * self.cost

    def __repr__(self):
        return str((self.begin, self.end, self.units, self.cost, self.price))

    def __unicode__(self):
        return _('After refill: from %(begin)s to %(end)s') % {
            'begin': self.begin.strftime(DATE_USER_FORMAT),
            'end': self.end.strftime(DATE_USER_FORMAT)
        }


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

    def __init__(self, fields, **kw):
        Tariff.__init__(self, fields, **kw)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            if days_in_month(end) == end.day:
                new_end = end + timedelta(days=1)
                new_end += timedelta(days=days_in_month(new_end) - 1)
                return CardTariffResult(begin, new_end, self.cost)
        else:
            new_begin = today - timedelta(days=today.day - 1)
            new_end = new_begin + timedelta(days=days_in_month(today) - 1)
            return CardTariffResult(new_begin, new_end, self.cost)


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

    def __init__(self, fields, **kw):
        Tariff.__init__(self, fields, **kw)

    def calc(self, begin, end):
        today = date.today()
        if begin <= today <= end:
            units = days_in_month(end) - end.day
            if units:
                return CardTariffResult(begin, end + timedelta(days=units), self.cost, units + 1)
        else:
            units = days_in_month(today) - today.day
            return CardTariffResult(today, today + timedelta(days=units), self.cost, units + 1)


if __name__ == '__main__':
    import doctest

    doctest.testmod()

