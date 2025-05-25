import yaml
import json
import os
from typing import Dict

def load_config(config_path: str) -> dict:
    """Wczytuje konfigurację z pliku YAML."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            print("[DEBUG] Wczytana konfiguracja YAML:", config)
            return config
    except FileNotFoundError:
        raise RuntimeError(f"Brak pliku konfiguracyjnego: {config_path}")

def load_log_config(log_config_path: str) -> Dict:
    """Wczytuje konfigurację logowania z pliku JSON."""
    try:
        with open(log_config_path, "r") as f:
            config = json.load(f)
            print("[DEBUG] Wczytana konfiguracja logowania:", config)
            return config
    except FileNotFoundError:
        raise RuntimeError(f"Brak pliku log_config: {log_config_path}")
