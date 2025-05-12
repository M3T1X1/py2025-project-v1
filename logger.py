import os
import json
import csv
import zipfile
from datetime import datetime, timedelta
from typing import Iterator, Dict, Optional

class Logger:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Inicjalizacja parametrów z konfiguracji
        self.log_dir = self.config['log_dir']
        self.filename_pattern = self.config['filename_pattern']
        self.buffer_size = self.config['buffer_size']
        self.rotate_every_hours = self.config['rotate_every_hours']
        self.max_size_mb = self.config['max_size_mb']
        self.rotate_after_lines = self.config.get('rotate_after_lines')
        self.retention_days = self.config['retention_days']

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'archive'), exist_ok=True)

        # Inicjalizacja pól wewnętrznych loggera
        self.current_file = None
        self.writer = None
        self.buffer = []
        self.last_rotation_time = datetime.now()
        self.current_line_count = 0
        self.current_filename = ""

    def _get_log_filename(self, dt: Optional[datetime] = None): # Generowanie nazwy pliku na podstawie wzorca i daty
        if not dt:
            dt = datetime.now()
        return os.path.join(self.log_dir, dt.strftime(self.filename_pattern))

    def start(self): # Rozpoczęcie logowania – otwarcie nowego pliku i zapis nagłówka jeśli nowy
        self.current_filename = self._get_log_filename()
        self.current_file = open(self.current_filename, mode='a', newline='', encoding='utf-8')
        self.writer = csv.writer(self.current_file)

        # Sprawdzenie, czy plik jest nowy i ewentualne dodanie nagłówka
        if os.path.getsize(self.current_filename) == 0:
            self.writer.writerow(["timestamp", "sensor_id", "value", "unit"])

        self.last_rotation_time = datetime.now()
        # Zliczanie istniejących linii w pliku (poza nagłówkiem)
        self.current_line_count = sum(1 for _ in open(self.current_filename)) - 1

    def stop(self): # Zatrzymanie logowania – zapisanie bufora i zamknięcie pliku
        self._flush()
        if self.current_file:
            self.current_file.close()
            self.current_file = None

    def log_reading(self, sensor_id, timestamp, value, unit):
        # Dodanie nowego wpisu do bufora
        self.buffer.append([timestamp.isoformat(), sensor_id, value, unit])
        # Zapis do pliku, jeśli bufor osiągnął zadany rozmiar
        if len(self.buffer) >= self.buffer_size:
            self._flush()
        # Sprawdzenie, czy potrzebna jest rotacja pliku
        if self._rotation_needed():
            self._rotate()

    def _flush(self):  # Zapisanie wszystkich danych z bufora do pliku
        if self.writer and self.buffer:
            self.writer.writerows(self.buffer)
            self.current_line_count += len(self.buffer)
            self.buffer = []
            self.current_file.flush()

    def _rotation_needed(self): # Sprawdzenie, czy plik powinien być zrotowany (czas, rozmiar, liczba linii)
        if (datetime.now() - self.last_rotation_time) >= timedelta(hours=self.rotate_every_hours):
            return True

        if os.path.exists(self.current_filename):
            size_mb = os.path.getsize(self.current_filename) / (1024 * 1024)
            if size_mb >= self.max_size_mb:
                return True

        if self.rotate_after_lines and self.current_line_count >= self.rotate_after_lines:
            return True

        return False

    def _rotate(self): # Rotacja: zamknięcie pliku, archiwizacja, czyszczenie starych archiwów, otwarcie nowego
        self.stop()
        self._archive(self.current_filename)
        self._old_archive_delete()
        self.start()

    def _archive(self, file_path: str): # Archiwizacja zamkniętego pliku
        file_name = os.path.basename(file_path)
        archive_path = os.path.join(self.log_dir, 'archive', file_name + '.zip')

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, arcname=file_name)

        os.remove(file_path)

    def _old_archive_delete(self): # Usuwanie starszych archiwów
        current_time = datetime.now()
        archive_dir = os.path.join(self.log_dir, 'archive')

        for file_name in os.listdir(archive_dir):
            file_path = os.path.join(archive_dir, file_name)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if (current_time - file_time).days > self.retention_days:
                    os.remove(file_path)

    def read_logs(self, start, end, sensor_id: Optional[str] = None) -> Iterator[Dict]:
        # Odczyt logów z CSV i ZIP z danego zakresu czasu i danego czujnika (podanie konkretnego czujnika jest opcjonalne)

        def parse_row(row): # Parsowanie wiersza CSV do słownika
            return {"timestamp": datetime.fromisoformat(row[0]), "sensor_id": row[1], "value": float(row[2]), "unit": row[3]}

        def csv_interator(path): # Iterowanie CSV
            with open(path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Pominięcie nagłówka
                for row in reader:
                    record = parse_row(row)
                    if start <= record["timestamp"] <= end:
                        if sensor_id is None or record["sensor_id"] == sensor_id:
                            yield record

        def zip_iterator(path): # Iterowanie ZIP
            with zipfile.ZipFile(path, 'r') as zip_file:
                for name in zip_file.namelist():
                    with zip_file.open(name) as file:
                        reader = csv.reader(line.decode('utf-8') for line in file)
                        next(reader)  # Pominięcie nagłówka
                        for row in reader:
                            record = parse_row(row)
                            if start <= record["timestamp"] <= end:
                                if sensor_id is None or record["sensor_id"] == sensor_id:
                                    yield record

        # Przejście przez wszystkie pliki CSV
        for file_name in os.listdir(self.log_dir):
            if file_name.endswith('.csv'):
                yield from csv_interator(os.path.join(self.log_dir, file_name))

        # Przejście przez wszystkie pliki ZIP
        archive_dir = os.path.join(self.log_dir, 'archive')
        for file_name in os.listdir(archive_dir):
            if file_name.endswith('.zip'):
                yield from zip_iterator(os.path.join(archive_dir, file_name))
