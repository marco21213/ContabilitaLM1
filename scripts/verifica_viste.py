#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
db_path = config.get('Autenticazione', 'percorso_database')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
views = cursor.fetchall()

print("=" * 60)
print("VISTE PRESENTI NEL DATABASE")
print("=" * 60)
if views:
    for v in views:
        print(f"  ✓ {v[0]}")
else:
    print("  ⚠️  Nessuna vista trovata")

# Verifica specifica
viste_richieste = ['vista_movimenti', 'scaduto_clienti', 'scaduto_fornitori']
viste_presenti = [v[0] for v in views]
viste_mancanti = [v for v in viste_richieste if v not in viste_presenti]

if viste_mancanti:
    print(f"\n⚠️  Viste mancanti: {', '.join(viste_mancanti)}")
else:
    print("\n✅ Tutte le viste richieste sono presenti")

conn.close()

