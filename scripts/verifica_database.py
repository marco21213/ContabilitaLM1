#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica rapida dello stato del database"""

import sqlite3
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read('config.ini')
db_path = config.get('Autenticazione', 'percorso_database')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("VERIFICA DATABASE")
print("=" * 60)

# Elenca tabelle
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]
print(f"\nTabelle create ({len(tables)}):")
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    count = cursor.fetchone()[0]
    print(f"  ✓ {t}: {count} righe")

# Verifica tabella importante
tabelle_richieste = ['soggetti', 'documenti', 'scadenze', 'pagamenti', 'associazioni_pagamenti', 'utenti']
tabelle_mancanti = [t for t in tabelle_richieste if t not in tables]

if tabelle_mancanti:
    print(f"\n⚠️  Tabelle mancanti: {', '.join(tabelle_mancanti)}")
else:
    print("\n✅ Tutte le tabelle principali sono presenti")

# Verifica utente admin
cursor.execute("SELECT COUNT(*) FROM utenti WHERE username='admin'")
if cursor.fetchone()[0] > 0:
    print("✅ Utente admin presente")
else:
    print("⚠️  Utente admin mancante")

# Verifica vista
cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
views = [v[0] for v in cursor.fetchall()]
print(f"\nViste create ({len(views)}):")
for v in views:
    print(f"  ✓ {v}")

conn.close()

