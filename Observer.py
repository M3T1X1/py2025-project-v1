import threading
import time
from datetime import datetime
import logging

from network.client import NetworkClient

class Observer:
    def __init__(self, sensor, logger, network_client):
        self.sensor = sensor
        self.logger = logger
        self.network_client = network_client

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run)

    def start(self):
        self._stop_event.clear()
        self._thread.start()
        logging.info(f"[OBSERVER] Started observing sensor {self.sensor.sensor_id}")

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        logging.info(f"[OBSERVER] Stopped observing sensor {self.sensor.sensor_id}")

    def _run(self):
        while not self._stop_event.is_set():
            if self.sensor.active:
                try:
                    value = self.sensor.generate()
                    timestamp = datetime.now()

                    # Log lokalnie (np. do pliku CSV)
                    self.logger.log_reading(
                        sensor_id=self.sensor.sensor_id,
                        timestamp=timestamp,
                        value=value,
                        unit=self.sensor.unit
                    )

                    # Wysyłka do serwera TCP
                    sent_ok = self.network_client.send_sensor_data(
                        sensor_id=self.sensor.sensor_id,
                        value=value,
                        unit=self.sensor.unit,
                        timestamp=timestamp
                    )

                    if not sent_ok:
                        logging.warning(f"[OBSERVER] Sending data failed for sensor {self.sensor.sensor_id}")

                except Exception as e:
                    logging.error(f"[OBSERVER] Error in sensor {self.sensor.sensor_id}: {e}")

            time.sleep(self.sensor.frequency)
