import unittest
from Sensor import Sensor
from AirQualitySensor import AirQualitySensor
from HumiditySensor import HumiditySensor
from PressureSensor import PressureSensor
from TemperatureSensor import TemperatureSensor


class TestSensor(unittest.TestCase):

    def setUp(self):
        self.sensor = Sensor(1, "Test Sensor", "unit", 0, 100)

    def test_generate_within_bounds(self):
        value = self.sensor.generate()
        self.assertTrue(self.sensor.min_value <= value <= self.sensor.max_value)

    def test_stop_and_start_sensor(self):
        self.sensor.stop()
        with self.assertRaises(Exception):
            self.sensor.generate()

        self.sensor.start()
        value = self.sensor.generate()
        self.assertIsNotNone(value)

    def test_calibrate(self):
        self.sensor.generate()
        calibrated = self.sensor.calibrate(2)
        self.assertEqual(calibrated, self.sensor.last_value)

    def test_get_last_value(self):
        val1 = self.sensor.get_last_value()
        val2 = self.sensor.get_last_value()
        self.assertEqual(val1, val2)


class TestAirQualitySensor(unittest.TestCase):

    def test_calculate_aqi_sets_range(self):
        sensor = AirQualitySensor(2)
        sensor.calculateAQI(20.0)  # Should be in second range
        self.assertTrue(0 <= sensor.min_value < sensor.max_value <= 500)


class TestHumiditySensor(unittest.TestCase):

    def test_rain_severity(self):
        sensor = HumiditySensor(3)
        sensor.severityChecker(True, 'Moderate')
        self.assertEqual(sensor.min_value, 40)

    def test_no_rain_severity(self):
        sensor = HumiditySensor(4)
        sensor.severityChecker(False, 'Severe')
        self.assertEqual(sensor.max_value, 15)

    def test_invalid_severity(self):
        sensor = HumiditySensor(5)
        with self.assertRaises(ValueError):
            sensor.severityChecker(True, 'CrazyRain')

        with self.assertRaises(ValueError):
            sensor.severityChecker(False, None)


class TestPressureSensor(unittest.TestCase):

    def test_setting_climate(self):
        sensor = PressureSensor(6)
        sensor.settingClimate('coastal')
        self.assertEqual(sensor.min_value, 990)

        sensor.settingClimate('mountain')
        self.assertEqual(sensor.max_value, 900)

        sensor.settingClimate('plains')
        self.assertEqual(sensor.min_value, 960)
        self.assertEqual(sensor.max_value, 1050)

    def test_invalid_climate(self):
        sensor = PressureSensor(7)
        with self.assertRaises(ValueError):
            sensor.settingClimate("desert")


class TestTemperatureSensor(unittest.TestCase):

    def test_setting_season(self):
        sensor = TemperatureSensor(8)
        sensor.settingSeason('winter')
        self.assertEqual(sensor.max_value, 5)

        sensor.settingSeason('spring')
        self.assertEqual(sensor.max_value, 25)
        self.assertEqual(sensor.min_value, -5)

    def test_invalid_season(self):
        sensor = TemperatureSensor(9)
        with self.assertRaises(ValueError):
            sensor.settingSeason('dryseason')

    def test_setting_season_inactive(self):
        sensor = TemperatureSensor(10)
        sensor.stop()
        with self.assertRaises(Exception):
            sensor.settingSeason('summer')


if __name__ == '__main__':
    unittest.main()
