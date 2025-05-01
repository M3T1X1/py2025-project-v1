from Sensor import Sensor

class AirQualitySensor(Sensor):
    def __init__(self, sensor_id, name = "Air Quality Sensor",unit = "AQI", min_value = 0, max_value = 500, frequency = 1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

    def calculateAQI(self, concentration): # jednostka concentration µg/m³
        breakpoints = [
           # C_L  #C_H I_L I_H
            (0.0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500),
        ]
        # Wzór obliczania AQI (Air Quality Index):
        #
        #           (I_high - I_low)
        # AQI = --------------------------- * (C - C_low) + I_low
        #           (C_high - C_low)

        for concentration_low, concentration_high, index_low, index_high in breakpoints:
            if concentration_low <= concentration <= concentration_high:
                AQI = ((index_high - index_low) / (concentration_high - concentration_low) * (concentration - concentration_low) + index_low)
                AQI = round(AQI, 2)

                self.min_value = max(0, AQI-20)
                self.max_value = min(500, AQI+20)

airQuality = AirQualitySensor(4)
