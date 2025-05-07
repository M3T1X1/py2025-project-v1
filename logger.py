import csv
from datetime import datetime
import os

class Logger:
    def __init__(self, logDir = 'logs'):
        self.logDir = logDir
        os.makedirs(self.logDir, exist_ok=True)

    def getLogFilePath(self, sensor):
        filename = f"{sensor.name}.log"
        return os.path.join(self.logDir, filename)

    def log(self, sensor):
        if not sensor.active:
            raise Exception("Sensor is not active")

        value = sensor.generate()
        filename = sensor.getLogFilePath(sensor)
        fileExists = os.path.exists(filename)

        with open(filename, 'a', newline='') as logFile:
            writer = csv.writer(logFile)
            if not fileExists:
                writer.writerow(["dateAndTime", 'sensorID', 'sensorName', 'unit', 'value'])
            dateAndTime = datetime.now().isoformat()
            writer.writerow([dateAndTime, sensor.id, sensor.name, sensor.unit, value])

    def readPreviousLogs(self, sensor):
        filename = sensor.getLogFilePath(sensor)
        if not os.path.exists(filename):
            raise Exception("File does not exists. Make sure to generate the file first!")
        with open(filename, 'r', newline='') as logFile:
            reader = csv.DictReader(logFile)
            return list(reader)