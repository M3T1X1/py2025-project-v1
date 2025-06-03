import socket
import json
import os
import threading

import yaml
from datetime import datetime
from logger import Logger  # zakładam, że Logger masz w osobnym pliku logger.py

class NetworkServer:
    def __init__(self, config_path_yaml="../config.yaml", config_path_json="../config.json"):
        # Wczytanie konfiguracji YAML dla servera
        with open(config_path_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        server_config = config.get("server", {})
        self.host = server_config.get("host", "0.0.0.0")
        self.port = server_config.get("port", 9000)
        self.log_path = server_config.get("log_path", "../logs")

        os.makedirs(self.log_path, exist_ok=True)

        # Inicjalizacja Loggera z konfiguracją JSON
        self.logger = Logger(config_path_json)
        self.logger.start()  # otwarcie pliku CSV do zapisu

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(5)

            print(f"[SERVER] Serwer nasłuchuje na porcie {self.port}...")

            stop_event = threading.Event()

            def wait_for_enter():
                input("Naciśnij ENTER, aby zatrzymać serwer...\n")
                stop_event.set()

            threading.Thread(target=wait_for_enter, daemon=True).start()

            try:
                while not stop_event.is_set():
                    s.settimeout(1.0)  # timeout, żeby móc sprawdzać stop_event
                    try:
                        conn, addr = s.accept()
                    except socket.timeout:
                        continue  # sprawdzamy stop_event ponownie
                    print(f"[SERVER] Połączenie od: {addr}")
                    with conn:
                        self._handle_client(conn)
            except KeyboardInterrupt:
                print("[SERVER] Zatrzymywanie serwera...")
            finally:
                self.logger.stop()  # zamknięcie pliku CSV przy końcu działania serwera
                print("[SERVER] Serwer zatrzymany.")

    def _handle_client(self, conn):
        buffer = b""
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    message = json.loads(line.decode("utf-8"))
                    print(f"[SERVER] Received: {message}")

                    # Logowanie do CSV za pomocą Loggera
                    self.logger.log_reading(
                        timestamp=datetime.fromisoformat(message["timestamp"]),
                        sensor_id=message["sensor_id"],
                        value=message["value"],
                        unit=message["unit"]
                    )

                    conn.sendall(b"ACK\n")

                except Exception as e:
                    print(f"[SERVER] Błąd podczas obsługi danych: {e}")
                    # Możesz tutaj dodać logowanie błędów, jeśli chcesz

if __name__ == "__main__":
    server = NetworkServer()
    server.start()
