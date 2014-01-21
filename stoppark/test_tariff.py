from unittest import TestCase
from tariff import Tariff, FixedTariff, DynamicTariff
from datetime import datetime, timedelta


class TestFixedTariff(TestCase):
    def test_incorrect_init(self):
        self.assertRaises(ValueError, FixedTariff, ['1', 'Hourly tariff', 'fail', '1', '1', 'None', 'None', 'None'])
        self.assertRaises(ValueError, FixedTariff, ['1', 'Hourly tariff', '1', 'fail', '1', 'None', 'None', 'None'])
        self.assertRaises(IndexError, FixedTariff, ['1', 'Special daily tariff', '1', '1', '1', '123', 'None', 'None'])

        self.assertRaises(KeyError, FixedTariff, ['1', 'Hourly tariff', '100', '1', '1', 'None', 'None', 'None'])
        self.assertRaises(KeyError, FixedTariff, ['1', 'Hourly tariff', '1', '100', '1', 'None', 'None', 'None'])

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
                                           datetime(2013, 3, 1, 12, tariff.free_time / 60 - 1, 0)),
                         (timedelta(0, tariff.free_time - 60), 0))
        self.assertEqual(tariff.calc_units(datetime(2013, 3, 1, 12, 0, 0),
                                           datetime(2013, 3, 1, 12, tariff.free_time / 60 - 1, 30)),
                         (timedelta(0, tariff.free_time - 60 + 30), 0))

    def test_fixed_hourly(self):
        tariff = Tariff.create(['1', 'Hourly tariff', '1', '1', '1', 'None', 'None', 'None'])
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 11, 0, 0), datetime(2013, 10, 28, 11, 10, 0)).state(),
                         (0, 0, 10, 0, timedelta(0, 600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 9, 0, 0), datetime(2013, 10, 28, 14, 45, 0)).state(),
                         (0, 5, 45, 6, timedelta(0, 21600), 6))
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 11, 0, 0), datetime(2013, 10, 28, 11, 10, 0)).state(),
                         (0, 0, 10, 0, timedelta(0, 600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 12, 1, 9, 0, 0), datetime(2013, 12, 2, 10, 0, 0)).state(),
                         (1, 1, 0, 25, timedelta(1, 3600), 25))
        self.assertEqual(tariff.calc(datetime(2013, 12, 1, 23, 55, 0), datetime(2013, 12, 2, 3, 25, 0)).state(),
                         (0, 3, 30, 4, timedelta(0, 14400), 4))
        self.assertEqual(tariff.calc(datetime(2014, 2, 28, 23, 30, 0), datetime(2014, 3, 1, 4, 0, 0)).state(),
                         (0, 4, 30, 5, timedelta(0, 18000), 5))
        self.assertEqual(tariff.calc(datetime(2008, 2, 28, 23, 30, 0), datetime(2008, 2, 29, 2, 0, 0)).state(),
                         (0, 2, 30, 3, timedelta(0, 10800), 3))
        self.assertEqual(tariff.calc(datetime(2008, 2, 28, 23, 30, 0), datetime(2008, 3, 1, 2, 0, 0)).state(),
                         (1, 2, 30, 27, timedelta(1, 10800), 27))
        self.assertEqual(tariff.calc(datetime(2013, 11, 30, 23, 55, 0), datetime(2013, 12, 1, 0, 5, 0)).state(),
                         (0, 0, 10, 0, timedelta(0, 600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 30, 23, 50, 0), datetime(2013, 10, 31, 1, 0, 0)).state(),
                         (0, 1, 10, 1, timedelta(0, 4200), 1))
        self.assertEqual(tariff.calc(datetime(2013, 9, 30, 22, 0, 0), datetime(2013, 10, 1, 9, 0, 0)).state(),
                         (0, 11, 0, 11, timedelta(0, 39600), 11))
        self.assertEqual(tariff.calc(datetime(2013, 10, 31, 22, 0, 0), datetime(2013, 11, 1, 9, 0, 0)).state(),
                         (0, 11, 0, 11, timedelta(0, 39600), 11))
        self.assertEqual(tariff.calc(datetime(2013, 11, 30, 23, 0, 0), datetime(2013, 12, 1, 8, 0, 0)).state(),
                         (0, 9, 0, 9, timedelta(0, 32400), 9))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 9, 0, 0), datetime(2014, 12, 10, 9, 0, 0)).state(),
                         (366, 0, 0, 8784, timedelta(366), 8784))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 23, 0, 0), datetime(2014, 1, 10, 23, 0, 0)).state(),
                         (32, 0, 0, 768, timedelta(32), 768))
        self.assertEqual(tariff.calc(datetime(2013, 12, 31, 23, 59, 59), datetime(2014, 1, 1, 1, 0, 0)).state(),
                         (0, 1, 0, 1, timedelta(0, 3601), 1))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 10, 0, 0), datetime(2013, 12, 9, 10, 15, 1)).state(),
                         (0, 0, 15, 1, timedelta(0, 3600), 1))
        self.assertEqual(tariff.calc(datetime(2013, 10, 26, 23, 0, 0), datetime(2013, 10, 27, 1, 0, 0)).state(),
                         (0, 2, 0, 2, timedelta(0, 7200), 2))
        self.assertEqual(tariff.calc(datetime(2013, 10, 24, 9, 0, 0), datetime(2013, 10, 21, 10, 0, 0)).state(),
                         (-3, 1, 0, 0, timedelta(-3, 3600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 24, 9, 0, 0), datetime(2013, 10, 24, 8, 50, 0)).state(),
                         (-1, 23, 50, 0, timedelta(-1, 85800), 0))

    def test_calc_units_daily(self):
        tariff = Tariff.create(['1', 'Daily tariff', '1', '2', '1', 'None', 'None', 'None'])
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 1, 8, 0, 0), datetime(2013, 9, 30, 9, 30, 0)),
                         (timedelta(29, 5400), 30))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0), datetime(2013, 10, 1, 8, 30, 0)),
                         (timedelta(1, 1800), 2))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0), datetime(2013, 10, 1, 9, 30, 0)),
                         (timedelta(1, 5400), 2))
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 30, 8, 0, 0),
                                           datetime(2013, 10, 1, 8, tariff.free_time / 60, 0)),
                         (timedelta(1, 900), 1))  # FREE_TIME works here
        self.assertEqual(tariff.calc_units(datetime(2013, 9, 1, 8, 0, 0), datetime(2013, 8, 31, 9, 30, 0)),
                         (timedelta(-1, 5400), 0))

    def test_fixed_hourly_extra(self):
        tariff = Tariff.create(['1', 'Hourly tariff', '1', '1', '11', 'None', 'None', 'None'])
        print tariff.calc(datetime(2014, 1, 17, 16, 24, 25), datetime(2014, 01, 17, 16, 32, 23))

    def test_fixed_daily_with_zero_time(self):
        tariff = Tariff.create(['1', 'Special daily tariff', '1', '2', '100', '09:00', 'None', 'None'])

        # Free time in action
        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 12, 0, 0), datetime(2013, 10, 1, 12, 10, 0)).state(),
                         (0, 0, 10, 0, timedelta(0, 600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 8, 50, 0), datetime(2013, 10, 1, 9, 10, 0)).state(),
                         (0, 0, 20, 0, timedelta(0, 1200), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 8, 50, 0), datetime(2013, 10, 2, 9, 10, 0)).state(),
                         (1, 0, 20, 1, timedelta(1, 1200), 100))

        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 9, 0, 0), datetime(2013, 10, 2, 9, 0, 0)).state(),
                         (1, 0, 0, 1, timedelta(1, 0), 100))
        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 8, 0, 0), datetime(2013, 10, 2, 9, 0, 0)).state(),
                         (1, 1, 0, 2, timedelta(1, 3600), 200))
        self.assertEqual(tariff.calc(datetime(2013, 10, 1, 8, 0, 0), datetime(2013, 10, 2, 10, 0, 0)).state(),
                         (1, 2, 0, 3, timedelta(2, 3600), 300))
        self.assertEqual(tariff.calc(datetime(2013, 10, 31, 6, 0, 0), datetime(2013, 11, 3, 12, 0, 0)).state(),
                         (3, 6, 0, 5, timedelta(4, 3600 * 3), 500))
        self.assertEqual(tariff.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 11, 10, 0)).state(),
                         (2, 3, 10, 4, timedelta(3, 3600), 400))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 11, 0, 0), datetime(2013, 12, 10, 8, 0, 0)).state(),
                         (0, 21, 0, 1, timedelta(0, 79200), 100))
        self.assertEqual(tariff.calc(datetime(2013, 11, 30, 8, 0, 0), datetime(2013, 12, 1, 9, 0, 0)).state(),
                         (1, 1, 0, 2, timedelta(1, 3600), 200))
        self.assertEqual(tariff.calc(datetime(2008, 2, 28, 16, 0, 0), datetime(2008, 2, 29, 16, 10, 0)).state(),
                         (1, 0, 10, 2, timedelta(1, 61200), 200))
        self.assertEqual(tariff.calc(datetime(2008, 2, 28, 8, 0, 0), datetime(2008, 3, 1, 10, 0, 0)).state(),
                         (2, 2, 0, 4, timedelta(3, 3600), 400))
        self.assertEqual(tariff.calc(datetime(2014, 2, 27, 9, 0, 0), datetime(2014, 3, 1, 10, 10, 0)).state(),
                         (2, 1, 10, 3, timedelta(3), 300))
        self.assertEqual(tariff.calc(datetime(2013, 12, 31, 23, 0, 0), datetime(2014, 1, 1, 9, 5, 0)).state(),
                         (0, 10, 5, 1, timedelta(0, 36300), 100))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 8, 0, 0), datetime(2013, 12, 9, 8, 50, 0)).state(),
                         (0, 0, 50, 1, timedelta(0, 3600), 100))
        self.assertEqual(tariff.calc(datetime(2013, 12, 9, 9, 0, 0), datetime(2014, 1, 10, 11, 10, 0)).state(),
                         (32, 2, 10, 33, timedelta(33), 3300))
        self.assertEqual(tariff.calc(datetime(2013, 12, 1, 9, 0, 0), datetime(2014, 11, 1, 10, 10, 0)).state(),
                         (335, 1, 10, 336, timedelta(336), 33600))
        self.assertEqual(tariff.calc(datetime(2013, 12, 3, 9, 0, 0), datetime(2013, 12, 1, 9, 0, 0)).state(),
                         (-2, 0, 0, 0, timedelta(-2), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 24, 9, 0, 0), datetime(2013, 10, 24, 8, 50, 0)).state(),
                         (-1, 23, 50, 0, timedelta(-1, 85800), 0))

    def test_hourly_with_max_per_day(self):
        tariff_a = Tariff.create(['1', 'Hourly + max_per_day', '1', '1', '1', 'None', '100', 'None'])
        self.assertEqual(tariff_a.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 16, 20, 0)).state(),
                         (2, 8, 20, 57, timedelta(2, 32400), 57))
        tariff_b = Tariff.create(['1', 'Hourly + max_per_day', '1', '1', '1', 'None', '10', 'None'])
        self.assertEqual(tariff_b.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 16, 20, 0)).state(),
                         (2, 8, 20, 57, timedelta(2, 32400), 29))


class TestDynamicTariff(TestCase):
    def test_incorrect_init(self):
        self.assertRaises(ValueError, DynamicTariff, ['1', 'Dynamic', '2', '2', '1', 'None', 'None', 'None'])

    def test_dynamic(self):
        tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1, 25)), 'None', 'None', 'None'])
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 11, 0, 0), datetime(2013, 10, 28, 11, 10, 0)).state(),
                         (0, 0, 10, 0, timedelta(0, 600), 0))
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 11, 0, 0), datetime(2013, 10, 28, 11, 45, 0)).state(),
                         (0, 0, 45, 1, timedelta(0, 3600), 1))
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 11, 0, 0), datetime(2013, 10, 28, 11, 45, 0)).state(),
                         (0, 0, 45, 1, timedelta(0, 3600), 1))
        self.assertEqual(tariff.calc(datetime(2013, 10, 28, 9, 0, 0), datetime(2013, 10, 28, 14, 45, 0)).state(),
                         (0, 5, 45, 6, timedelta(0, 21600), 21))

    def test_dynamic_with_max_per_day(self):
        tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1, 25)), 'None', '100', 'None'])
        self.assertEqual(tariff.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 11, 10, 0)).state(),
                         (2, 3, 10, 51, timedelta(2, 3*3600 + 600), 206))
        self.assertEqual(tariff.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 16, 20, 0)).state(),
                         (2, 8, 20, 57, timedelta(2, 32400), 245))

        tariff = Tariff.create(['2', '', '2', '1', ' '.join(str(i) for i in range(1, 25)), 'None', '10', 'None'])
        self.assertEqual(tariff.calc(datetime(2013, 10, 26, 8, 0, 0), datetime(2013, 10, 28, 16, 20, 0)).state(),
                         (2, 8, 20, 57, timedelta(2, 32400), 30))