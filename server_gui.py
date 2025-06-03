import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import yaml
from datetime import datetime, timedelta
from collections import defaultdict, deque
from logger import Logger
import socket
import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)  # Dodaj katalog główny projektu

try:
    from server.server import NetworkServer
    from network.client import NetworkClient
    from network.config import load_config, load_log_config
except ImportError as e:
    print(f"Błąd: Nie można zaimportować modułów serwera. Sprawdź ścieżki.\n{e}")
    sys.exit(1)


class SensorDataManager:
    """Zarządza danymi sensorów i oblicza średnie"""

    def __init__(self):
        self.sensor_data = defaultdict(lambda: {
            'values': deque(maxlen=43200),  # 12h * 3600s = 43200 próbek (1 na sekundę)
            'timestamps': deque(maxlen=43200),
            'last_value': None,
            'last_timestamp': None,
            'unit': ''
        })

    def add_reading(self, sensor_id, value, unit, timestamp):
        """Dodaje nowy odczyt sensora"""
        data = self.sensor_data[sensor_id]
        data['values'].append(float(value))
        data['timestamps'].append(timestamp)
        data['last_value'] = float(value)
        data['last_timestamp'] = timestamp
        data['unit'] = unit

    def get_average(self, sensor_id, hours):
        """Oblicza średnią z ostatnich N godzin"""
        if sensor_id not in self.sensor_data:
            return None

        data = self.sensor_data[sensor_id]
        if not data['values']:
            return None

        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Filtruj wartości z ostatnich N godzin
        recent_values = []
        for timestamp, value in zip(data['timestamps'], data['values']):
            if timestamp >= cutoff_time:
                recent_values.append(value)

        if not recent_values:
            return None

        return sum(recent_values) / len(recent_values)

    def get_sensor_list(self):
        """Zwraca listę wszystkich sensorów z danymi"""
        return list(self.sensor_data.keys())


class StatusBar(tk.Frame):
    """Pasek statusu aplikacji"""

    def __init__(self, master):
        super().__init__(master)
        self.label = tk.Label(self, text="Gotowy", relief=tk.SUNKEN, anchor=tk.W)
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pack(side=tk.BOTTOM, fill=tk.X)

    def set_text(self, text):
        """Ustawia tekst na pasku statusu"""
        self.label.config(text=text)
        self.label.update_idletasks()


class ServerGUI:
    """Główna klasa GUI serwera"""

    def __init__(self, root):
        self.root = root
        self.root.title("Network Server GUI")
        self.root.geometry("800x600")

        # Inicjalizacja danych
        self.data_manager = SensorDataManager()
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.config_file = "gui_config.json"

        # Wczytaj konfigurację
        self.load_config()

        # Utwórz interfejs
        self.create_widgets()

        # Uruchom timer odświeżania
        self.update_timer()

        # Obsługa zamknięcia
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Tworzy wszystkie elementy interfejsu"""

        # Górny panel - sterowanie serwerem
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # Port
        tk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(self.config.get('port', 9999)))
        self.port_entry = tk.Entry(top_frame, textvariable=self.port_var, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        # Przyciski
        self.start_btn = tk.Button(top_frame, text="Start", command=self.start_server,
                                   bg="green", fg="white")
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(top_frame, text="Stop", command=self.stop_server,
                                  bg="red", fg="white", state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Status połączenia
        self.status_label = tk.Label(top_frame, text="Zatrzymany", fg="red")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Środkowy panel - tabela sensorów
        middle_frame = tk.Frame(self.root)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Nagłówek tabeli
        tk.Label(middle_frame, text="Lista sensorów", font=("Arial", 12, "bold")).pack()

        # Tabela z danymi sensorów
        columns = ("Sensor", "Wartość", "Jednostka", "Timestamp", "Śr. 1h", "Śr. 12h")
        self.tree = ttk.Treeview(middle_frame, columns=columns, show="headings", height=15)

        # Konfiguracja kolumn
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(middle_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pakowanie tabeli i scrollbara
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Dolny panel - pasek statusu
        self.status_bar = StatusBar(self.root)

    def load_config(self):
        """Wczytuje konfigurację z pliku"""
        default_config = {
            'port': 9999,
            'update_interval': 3
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
        except Exception as e:
            print(f"Błąd wczytywania konfiguracji: {e}")
            self.config = default_config

    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            self.config['port'] = int(self.port_var.get())
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Błąd zapisywania konfiguracji: {e}")

    def start_server(self):
        """Uruchamia serwer TCP"""
        try:
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                raise ValueError("Port musi być między 1 a 65535")

            # Sprawdź czy port jest dostępny
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('localhost', port))
            test_socket.close()

            # Uruchom serwer w osobnym wątku
            self.server_thread = threading.Thread(target=self.run_server, args=(port,))
            self.server_thread.daemon = True
            self.server_thread.start()

            # Aktualizuj interfejs
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            self.status_label.config(text="Nasłuchiwanie", fg="green")
            self.status_bar.set_text(f"Nasłuchiwanie na porcie {port}")

            self.is_running = True
            self.save_config()

        except ValueError as e:
            messagebox.showerror("Błąd", f"Nieprawidłowy port: {e}")
        except OSError as e:
            messagebox.showerror("Błąd", f"Nie można uruchomić serwera: {e}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nieoczekiwany błąd: {e}")

    def run_server(self, port):
        """Funkcja uruchamiająca serwer w osobnym wątku"""
        try:
            # Stwórz prosty serwer TCP
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', port))
            server_socket.listen(5)
            server_socket.settimeout(1.0)  # Timeout dla sprawdzania is_running

            self.status_bar.set_text(f"Serwer nasłuchuje na porcie {port}")

            while self.is_running:
                try:
                    client_socket, address = server_socket.accept()
                    self.status_bar.set_text(f"Połączono z {address}")

                    # Obsłuż klienta w osobnym wątku
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        print(f"Błąd serwera: {e}")

            server_socket.close()

        except Exception as e:
            self.status_bar.set_text(f"Błąd serwera: {e}")
            print(f"Błąd serwera: {e}")

    def handle_client(self, client_socket, address):
        logger = None  # Inicjalizacja zmiennej
        try:
            # Inicjalizuj Logger z poprawną ścieżką
            logger = Logger(config_path="config.json")  # <-- TU BYŁ BŁĄD
            logger.start()

            while self.is_running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                for line in data.strip().split('\n'):
                    if line:
                        try:
                            sensor_data = json.loads(line)
                            timestamp = datetime.fromisoformat(sensor_data['timestamp'])

                            # Aktualizuj GUI
                            self.data_manager.add_reading(
                                sensor_data['sensor_id'],
                                sensor_data['value'],
                                sensor_data['unit'],
                                timestamp
                            )

                            # Zapisz do pliku CSV
                            logger.log_reading(
                                timestamp=timestamp,
                                sensor_id=sensor_data['sensor_id'],
                                value=sensor_data['value'],
                                unit=sensor_data['unit']
                            )

                            client_socket.send(b'ACK\n')
                        except Exception as e:
                            print(f"Błąd przetwarzania danych: {e}")

        except Exception as e:
            print(f"Błąd obsługi klienta {address}: {e}")
        finally:
            if logger:  # <-- WAŻNE: sprawdź czy logger istnieje
                logger.stop()
            client_socket.close()

    def stop_server(self):
        """Zatrzymuje serwer"""
        self.is_running = False

        # Aktualizuj interfejs
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.status_label.config(text="Zatrzymany", fg="red")
        self.status_bar.set_text("Serwer zatrzymany")

    def update_table(self):
        """Aktualizuje tabelę z danymi sensorów"""
        # Wyczyść tabelę
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Dodaj dane sensorów
        for sensor_id in self.data_manager.get_sensor_list():
            data = self.data_manager.sensor_data[sensor_id]

            # Ostatnia wartość
            last_value = f"{data['last_value']:.2f}" if data['last_value'] is not None else "-"

            # Timestamp
            if data['last_timestamp']:
                timestamp_str = data['last_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = "-"

            # Średnie
            avg_1h = self.data_manager.get_average(sensor_id, 1)
            avg_12h = self.data_manager.get_average(sensor_id, 12)

            avg_1h_str = f"{avg_1h:.2f}" if avg_1h is not None else "-"
            avg_12h_str = f"{avg_12h:.2f}" if avg_12h is not None else "-"

            # Dodaj wiersz do tabeli
            self.tree.insert("", "end", values=(
                sensor_id,
                last_value,
                data['unit'],
                timestamp_str,
                avg_1h_str,
                avg_12h_str
            ))

    def update_timer(self):
        """Timer odświeżający interfejs co kilka sekund"""
        self.update_table()

        # Zaplanuj następną aktualizację
        interval = self.config.get('update_interval', 3) * 1000  # ms
        self.root.after(interval, self.update_timer)

    def on_closing(self):
        """Obsługuje zamknięcie aplikacji"""
        if self.is_running:
            self.stop_server()

        self.save_config()
        self.root.destroy()


def main():
    """Funkcja główna"""
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
