#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per elencare tutte le tabelle del database
"""

import sqlite3
import sys
from pathlib import Path
import configparser

# Percorso del database dal config
config_path = Path(__file__).parent.parent / "config.ini"
db_path = None

if config_path.exists():
    config = configparser.ConfigParser()
    config.read(config_path)
    db_path = config.get("Autenticazione", "percorso_database", fallback=None)
    if not db_path or not Path(db_path).exists():
        db_path = config.get("Database", "link", fallback=None)

if not db_path:
    print("Errore: Impossibile trovare il percorso del database nel config.ini")
    sys.exit(1)

print(f"Database: {db_path}\n")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Elenca tutte le tabelle
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"Trovate {len(tables)} tabelle:\n")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} righe")
    
    # Elenca anche le viste
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = cursor.fetchall()
    
    if views:
        print(f"\nTrovate {len(views)} viste:\n")
        for view in views:
            print(f"  - {view[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Errore: {e}")
    sys.exit(1)

