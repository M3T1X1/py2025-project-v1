import threading
import time
from datetime import datetime

class Observer:
    def __init__(self, sensor, logger):
        self.sensor = sensor
        self.logger = logger
        self._stop_event = threading.Event() # Zatrzymanie watku (flaga)
        self._thread = threading.Thread(target=self._run) # Watek wykonujacy _run

    def start(self):
        self._stop_event.clear() # Wyczyszczenie flagi
        self._thread.start()

    def stop(self):
        self._stop_event.set() # Ustawianie flagi
        self._thread.join()

    def _run(self):
        while not self._stop_event.is_set():
            if self.sensor.active:
                value = self.sensor.generate()
                timestamp = datetime.now()
                self.logger.log_reading(
                    sensor_id=self.sensor.sensor_id,
                    timestamp=timestamp,
                    value=value,
                    unit=self.sensor.unit
                )
            time.sleep(self.sensor.frequency)
