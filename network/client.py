import socket
import json
import logging
import sys
import threading

import yaml
import time
from datetime import datetime
from AirQualitySensor import AirQualitySensor
from HumiditySensor import HumiditySensor
from PressureSensor import PressureSensor
from TemperatureSensor import TemperatureSensor

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s', stream=sys.stdout)

class NetworkClient:
    def __init__(self, config_path="../config.yaml"):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            client_cfg = config.get("client", {})
        except Exception as e:
            logging.error(f"Nie udało się wczytać pliku: '{config_path}': {e}")
            client_cfg = {}

        self.host = client_cfg.get("host", "127.0.0.1")
        self.port = client_cfg.get("port", 9000)
        self.timeout = client_cfg.get("timeout", 5.0)
        self.retries = client_cfg.get("retries", 3)

    def send_sensor_data(self, sensor_id, value, unit, timestamp):
        message_dict = {
            "sensor_id": sensor_id,
            "value": value,
            "unit": unit,
            "timestamp": timestamp.isoformat()
        }
        message = (json.dumps(message_dict) + "\n").encode('utf-8')

        for attempt in range(1, self.retries + 1):
            try:
                logging.info(f"[CLIENT] Łączenie z: {self.host}:{self.port}")
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    logging.info(f"[CLIENT] Połączono z: {self.host}:{self.port}")

                    sock.sendall(message)
                    logging.info(f"[CLIENT] Wysłano dane:: {message_dict}")

                    sock.settimeout(self.timeout)
                    ack = sock.recv(1024)

                    if ack.strip() == b'ACK':
                        logging.info("[CLIENT] Przyjęto ACK i wysłano dane.")
                        return True
                    else:
                        logging.warning(f"[CLIENT] Nieoczekiwany błąd ACK: {ack}")

            except socket.timeout:
                logging.error(f"[CLIENT] Próba {attempt} nie powiodła się: timed out")
            except Exception as e:
                logging.error(f"[CLIENT] Próba {attempt} nie powiodła się: {e}")

            logging.info("[CLIENT] Zamknięto połączenie")

        logging.error(f"[CLIENT] Nie udało się wyslać danych po {self.retries} próbach (sensor_id={sensor_id})")
        return False


def wait_for_enter(stop_event):
    input("Naciśnij ENTER, aby zakończyć działanie klienta...\n")
    stop_event.set()

if __name__ == "__main__":
    client = NetworkClient()
    temp_sensor = TemperatureSensor("T-01")
    air_sensor = AirQualitySensor("AQ-02")
    humidity_sensor = HumiditySensor("H-03")
    pressure_sensor = PressureSensor("P-04")

    sensors = [temp_sensor, air_sensor, humidity_sensor, pressure_sensor]

    stop_event = (
        threading.Event())
    threading.Thread(target=wait_for_enter, args=(stop_event,), daemon=True).start()

    try:
        while not stop_event.is_set():
            for sensor in sensors:
                if stop_event.is_set():
                    break

                value = sensor.generate()
                timestamp = datetime.now()
                sensor_id = sensor.sensor_id
                unit = sensor.unit

                success = client.send_sensor_data(sensor_id, value, unit, timestamp)
                if not success:
                    logging.error(f"Nie udało sie wyslać danych dla sensora: {sensor_id}.")
                else:
                    logging.info(f"Wysłano dane: sensor_id={sensor_id}, value={value}{unit}, timestamp={timestamp}")

                time.sleep(sensor.frequency)

    except KeyboardInterrupt:
        print("\n[CLIENT] Zakończono działanie klienta przez użytkownika.")

    finally:
        print("[CLIENT] Klient zatrzymany.")