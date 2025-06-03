from Sensor import Sensor

class PressureSensor(Sensor):
    def __init__(self, sensor_id, name = "Pressure Sensor", unit = "hPa", min_value = 800 , max_value = 1150, frequency = 1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

    def settingClimate(self, climate):
        match climate:
            case 'coastal':
                self.min_value = 990
            case 'mountain':
                self.max_value = 900
            case 'plains':
                self.min_value = 960
                self.max_value = 1050
            case _:
                raise ValueError("Enter correct value!")


pressure = PressureSensor(2)





