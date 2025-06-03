from Sensor import Sensor

class HumiditySensor(Sensor):
    def __init__(self, sensor_id, name = "Humidity Sensor",unit = "%RH", min_value = 0, max_value = 100, frequency = 1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

    def severityChecker(self, hadItRained, severity):
        if hadItRained:
            if severity is None:
                raise ValueError("If it had rained, specify how severe the rain was")
            if severity == 'Severe':
                self.min_value = 65
            elif severity == 'Moderate':
                self.min_value = 40
            elif severity == 'Light':
                self.min_value = 20
            else:
                raise ValueError("Error specifying the severity")
        if not hadItRained:
            if severity is None:
                raise ValueError("If it hadn't rained, specify how severe the drought was")
            if severity == 'Severe':
                self.max_value = 15
            elif severity == 'Moderate':
                self.max_value = 30
            elif severity == 'Light':
                self.max_value = 50
            else:
                raise ValueError("Error specifying the severity")


humidity = HumiditySensor(3)
