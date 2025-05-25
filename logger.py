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

        config_dir = os.path.dirname(os.path.abspath(config_path))
        log_dir_from_config = self.config['log_dir']
        if os.path.isabs(log_dir_from_config):
            self.log_dir = log_dir_from_config
        else:
            self.log_dir = os.path.join(config_dir, log_dir_from_config)

        self.filename_pattern = self.config['filename_pattern']
        self.buffer_size = self.config['buffer_size']
        self.rotate_every_hours = self.config['rotate_every_hours']
        self.max_size_mb = self.config['max_size_mb']
        self.rotate_after_lines = self.config.get('rotate_after_lines')
        self.retention_days = self.config['retention_days']

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'archive'), exist_ok=True)

        self.current_file = None
        self.writer = None
        self.buffer = []
        self.last_rotation_time = datetime.now()
        self.current_line_count = 0
        self.current_filename = ""

    def _get_log_filename(self, dt: Optional[datetime] = None):
        if not dt:
            dt = datetime.now()
        return os.path.join(self.log_dir, dt.strftime(self.filename_pattern))

    def start(self):
        self.current_filename = self._get_log_filename()
        is_new_file = not os.path.exists(self.current_filename) or os.path.getsize(self.current_filename) == 0
        self.current_file = open(self.current_filename, mode='a', newline='', encoding='utf-8')
        self.writer = csv.writer(self.current_file, delimiter=',')
        if is_new_file:
            print("[LOGGER] Wpisywanie nagłówków CSV")
            self.writer.writerow(["timestamp", "sensor_id", "value", "unit"])
            self.current_file.flush()

        # Count existing lines (excluding header)
        with open(self.current_filename, 'r', encoding='utf-8') as f:
            self.current_line_count = sum(1 for _ in f) - 1

        self.last_rotation_time = datetime.now()

    def stop(self):
        self._flush()
        if self.current_file:
            self.current_file.close()
            self.current_file = None
            print(f"[LOGGER] Zamknięto plik: {self.current_filename}")

    def log_reading(self, timestamp,sensor_id, value, unit):
        if isinstance(timestamp, (float, int)):
            timestamp = datetime.fromtimestamp(timestamp)

        self.buffer.append([timestamp.isoformat(), sensor_id, value, unit])

        if len(self.buffer) >= self.buffer_size:
            print(f"[LOGGER] Buffor: {len(self.buffer)} osiągnięty, nastąpi flush")
            self._flush()

        if self._rotation_needed():
            print("[LOGGER] Rotuję")
            self._rotate()

    def _flush(self):
        if self.writer and self.buffer:
            self.writer.writerows(self.buffer)
            self.current_line_count += len(self.buffer)
            print(f"[LOGGER] Zrobiono flush")
            self.buffer = []
            self.current_file.flush()

    def _rotation_needed(self):
        if (datetime.now() - self.last_rotation_time) >= timedelta(hours=self.rotate_every_hours):
            print("[LOGGER] Niedługo rotacja przez czas")
            return True

        if os.path.exists(self.current_filename):
            size_mb = os.path.getsize(self.current_filename) / (1024 * 1024)
            if size_mb >= self.max_size_mb:
                print("[LOGGER] Niedługo rotacja wielkosc pliku")
                return True

        if self.rotate_after_lines and self.current_line_count >= self.rotate_after_lines:
            print("[LOGGER] Niedługo rotacja przez ilość rzędów")
            return True

        return False

    def _rotate(self):
        self.stop()
        self._archive(self.current_filename)
        self._old_archive_delete()
        self.start()

    def _archive(self, file_path: str):
        file_name = os.path.basename(file_path)
        archive_path = os.path.join(self.log_dir, 'archive', file_name + '.zip')

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, arcname=file_name)
        print(f"[LOGGER] Zarchiwizowano w:{archive_path}")

        os.remove(file_path)

    def _old_archive_delete(self):
        current_time = datetime.now()
        archive_dir = os.path.join(self.log_dir, 'archive')

        for file_name in os.listdir(archive_dir):
            file_path = os.path.join(archive_dir, file_name)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if (current_time - file_time).days > self.retention_days:
                    os.remove(file_path)
                    print(f"[LOGGER] Usunięto stare archiwum: {file_name}")


