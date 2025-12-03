#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read('config.ini')
db_path = config.get('Autenticazione', 'percorso_database')

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=" * 70)
print("VERIFICA STATO DATABASE")
print("=" * 70)

# Tabelle
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [t[0] for t in cur.fetchall()]
print(f"\n📊 TABELLE ({len(tables)}):")
tabelle_richieste = ['soggetti', 'documenti', 'scadenze', 'pagamenti', 'associazioni_pagamenti', 'utenti', 'banche', 'riba', 'distinte_riba', 'lockouts', 'login_logs']
for t in tabelle_richieste:
    if t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"  ✓ {t:25} {count:>5} righe")
    else:
        print(f"  ✗ {t:25} MANCANTE")

# Viste
cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
views = [v[0] for v in cur.fetchall()]
print(f"\n👁️  VISTE ({len(views)}):")
for v in views:
    print(f"  ✓ {v}")

# Utente admin
cur.execute("SELECT COUNT(*) FROM utenti WHERE username='admin'")
admin_presente = cur.fetchone()[0] > 0
print(f"\n👤 UTENTE ADMIN: {'✓ Presente' if admin_presente else '✗ Mancante'}")

# Verifica struttura pagamenti
cur.execute("PRAGMA table_info(pagamenti)")
colonne_pag = [c[1] for c in cur.fetchall()]
has_tipo_movimento = 'tipo_movimento' in colonne_pag
print(f"\n🔍 STRUTTURA PAGAMENTI:")
print(f"  tipo_movimento: {'✓ Presente' if has_tipo_movimento else '✗ Mancante'}")

# Verifica struttura documenti
cur.execute("PRAGMA table_info(documenti)")
colonne_doc = [c[1] for c in cur.fetchall()]
has_segno = 'segno' in colonne_doc
print(f"\n🔍 STRUTTURA DOCUMENTI:")
print(f"  segno: {'✓ Presente' if has_segno else '✗ Mancante'}")

print("\n" + "=" * 70)
if all(t in tables for t in tabelle_richieste) and admin_presente and has_tipo_movimento and has_segno:
    print("✅ DATABASE PRONTO PER I TEST")
else:
    print("⚠️  ALCUNI ELEMENTI MANCANO - VERIFICARE")
print("=" * 70)

conn.close()

