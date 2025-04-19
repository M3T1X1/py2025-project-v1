import random

from Sensor import Sensor

class TemperatureSensor(Sensor):
    def __init__(self, sensor_id, name = "Temperature Sensor",unit = "°C", min_value = -20, max_value = 35, frequency = 1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

    def settingSeason(self, season): #season = winter, autumn, spirng, summer
        if not self.active:
            raise Exception("The temperature sensor is not active.")
        match season:
            case 'winter':
                self.max_value = 5
            case 'spring':
                self.max_value = 25
                self.min_value = -5
            case 'summer':
                self.min_value = 10
            case 'autumn':
                self.max_value = 20
                self.min_value = -10
            case _:
                raise ValueError
        print(f"The temperature sensor has been set to {season}.")

a = TemperatureSensor(1)

a.settingSeason('spring')
a.calibrate('dawn')
a.read_value()

print(f"Min: {a.min_value:.2f}, Max: {a.max_value:.2f}")
print(f"Wartość wygenerowana: {a.last_value:.2f}")



