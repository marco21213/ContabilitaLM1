# scripts/config_loader.py
# Piccolo helper opzionale per centralizzare la lettura di config.ini (non indispensabile se usi direttamente db_manager.get_connection)
from __future__ import annotations
from pathlib import Path
import configparser
import os

def find_config_path() -> Path:
    candidates = [
        os.environ.get("CONFIG_INI_PATH"),
        Path.cwd() / "config.ini",
        Path(__file__).resolve().parents[1] / "config.ini",
        Path(__file__).resolve().parent.parent / "config.ini",
    ]
    for c in candidates:
        if not c:
            continue
        p = Path(c).expanduser().resolve()
        if p.exists():
            return p
    raise FileNotFoundError("config.ini non trovato; imposta $CONFIG_INI_PATH o posizionalo nella root del progetto.")

def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    p = find_config_path()
    cfg.read(p, encoding="utf-8")
    return cfg
