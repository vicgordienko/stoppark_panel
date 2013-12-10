from unittest import TestCase
from tariff import Tariff
from datetime import datetime, timedelta


class TestFixedTariff(TestCase):
    def test_incorrect_tariffs(self):
        self.assertRaises(ValueError, Tariff, ['1', 'Hourly tariff', 'fail', '1', '1', 'None', 'None', 'None'])
        self.assertRaises(ValueError, Tariff, ['1', 'Hourly tariff', '1', 'fail', '1', 'None', 'None', 'None'])
        self.assertRaises(IndexError, Tariff, ['1', 'Special daily tariff', '1', '1', '1', '123', 'None', 'None'])

        self.assertRaises(KeyError, Tariff, ['1', 'Hourly tariff', '100', '1', '1', 'None', 'None', 'None'])
        self.assertRaises(KeyError, Tariff, ['1', 'Hourly tariff', '1', '100', '1', 'None', 'None', 'None'])

    def test_tariff_create(self):
        a = Tariff.create(['1', 'Hourly tariff', '1', '1', '1', 'None', 'None', 'None'])
        self.assertEquals((a.type, a.interval), (Tariff.FIXED, Tariff.HOURLY))

    def test_calc_units_hourly(self):
        tariff = Tariff.create(['1', 'Hourly tariff', '1', '1', '1', 'None', 'None', 'None'])
        self.assertEqual(tariff.calc_units(datetime(2013, 3, 1, 12, 0, 0), datetime(2013, 3, 1, 14, 0, 0)),
                         (timedelta(0, 7200), 2))
        self.assertEqual(tariff.calc_units(datetime(2010, 3, 1, 12, 0, 0), datetime(2013, 3, 1, 14, 38, 41)),
                         (timedelta(1096, 9521), 26307))
        self.assertEqual(tariff.calc_units(datetime(2013, 3, 1, 12, 0, 0), datetime(2010, 3, 1, 14, 0, 0)),
                         (timedelta(-1096, 7200), 0))
        self.assertEqual(tariff.calc_units(datetime(2013, 3, 1, 12, 0, 0),
                                            datetime(2013, 3, 1, 12, Tariff.FREE_TIME / 60 - 1, 0)),
                         (timedelta(0, Tariff.FREE_TIME - 60), 0))
        self.assertEqual(tariff.calc_units(datetime(2013, 3, 1, 12, 0, 0),
                                            datetime(2013, 3, 1, 12, Tariff.FREE_TIME / 60 - 1, 30)),
                         (timedelta(0, Tariff.FREE_TIME - 60 + 30), 0))

    def test_calc_units_daily(self):
        tariff = Tariff.create(['1', 'Daily tariff', '1', '2', '1', 'None', 'None', 'None'])
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 1, 8, 0, 0), datetime(2013, 9, 30, 9, 30, 0)),
                         (timedelta(29, 5400), 30))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0), datetime(2013, 10, 1, 8, 30, 0)),
                         (timedelta(1, 1800), 2))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0), datetime(2013, 10, 1, 9, 30, 0)),
                         (timedelta(1, 5400), 2))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0),
                                            datetime(2013, 10, 1, 8, Tariff.FREE_TIME / 60, 0)),
                         (timedelta(1, 900), 1))  # FREE_TIME works here
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 1, 8, 0, 0), datetime(2013, 8, 31, 9, 30, 0)),
                         (timedelta(-1, 5400), 0))

    def test_calc_daily_with_zero_time(self):
        def extract(result):
            return result.days, result.hours, result.minutes, result.units, result.price

        tariff = Tariff.create(['1', 'Special daily tariff', '1', '2', '100', '09:00', 'None', 'None'])
        self.assertEqual(extract(tariff.calc(datetime(2013, 10, 1, 9, 0, 0), datetime(2013, 10, 2, 9, 0, 0))),
                         (1, 0, 0, 1, 100))
        self.assertEqual(extract(tariff.calc(datetime(2013, 10, 1, 8, 0, 0), datetime(2013, 10, 2, 9, 0, 0))),
                         (1, 1, 0, 2, 200))
        self.assertEqual(extract(tariff.calc(datetime(2013, 10, 1, 8, 0, 0), datetime(2013, 10, 2, 10, 0, 0))),
                         (1, 2, 0, 3, 300))
        self.assertEqual(extract(tariff.calc(datetime(2013, 10, 31, 6, 0, 0), datetime(2013, 11, 3, 12, 0, 0))),
                         (3, 6, 0, 5, 500))
