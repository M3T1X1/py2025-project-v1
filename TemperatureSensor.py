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

    def calibrate(self, timeOfDay): #timeOfDay = dawn, noon, dusk, night
        if self.last_value is None:
            self.generate()

        multiplier  = None

        match timeOfDay:
            case 'dawn':
                if self.last_value < 0:
                    multiplier = 1.2
                else:
                    multiplier = 0.8
            case 'noon':
                multiplier  = 1.2
            case 'dusk':
                multiplier  = 1
            case 'night':
                if self.last_value < 0:
                    multiplier = 1.3
                else:
                    multiplier = 0.7

        self.last_value *= multiplier
        return self.last_value

temperature = TemperatureSensor(1)

temperature.settingSeason('spring')
temperature.generate()
temperature.calibrate('dawn')

print(f"Min: {temperature.min_value}, Max: {temperature.max_value}")
print(f"Generated value: {temperature.last_value:.2f}{temperature.unit}")



