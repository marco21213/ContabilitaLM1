#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per ricreare le viste scaduto_clienti e scaduto_fornitori
"""

import sqlite3
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read('config.ini')
db_path = config.get('Autenticazione', 'percorso_database')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("RICREAZIONE VISTE SCADUTI")
print("=" * 60)

# Verifica se esiste la colonna segno
cursor.execute("PRAGMA table_info(documenti)")
colonne_info = cursor.fetchall()
colonne_nomi = [col[1] for col in colonne_info]
has_segno = 'segno' in colonne_nomi

if not has_segno:
    print("⚠️  ATTENZIONE: La colonna 'segno' non esiste nella tabella documenti")
    print("   Le viste potrebbero non funzionare correttamente")

print("\n1. Elimino le viste esistenti...")
cursor.execute("DROP VIEW IF EXISTS scaduto_clienti")
cursor.execute("DROP VIEW IF EXISTS scaduto_fornitori")
print("   ✓ Viste eliminate")

print("\n2. Creo la vista scaduto_clienti...")
# Vista per clienti (documenti con segno=1, fatture attive)
try:
    cursor.execute("""
    CREATE VIEW scaduto_clienti AS
    SELECT 
        s.id AS soggetto_id,
        s.codice_soggetto,
        s.ragione_sociale,
        COUNT(DISTINCT CASE 
            WHEN date(substr(sc.data_scadenza, 7, 4) || '-' || 
                      substr(sc.data_scadenza, 4, 2) || '-' || 
                      substr(sc.data_scadenza, 1, 2)) < date('now')
            THEN sc.id 
        END) AS numero_scadenze_scadute,
        COALESCE(SUM(sc.importo_scadenza), 0) AS totale_scadenze,
        COALESCE(SUM(
            CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
        ), 0) AS totale_pagato,
        COALESCE(SUM(sc.importo_scadenza), 0) - 
        COALESCE(SUM(
            CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
        ), 0) AS saldo_scaduto
    FROM soggetti s
    JOIN documenti d ON s.id = d.soggetto_id
    JOIN scadenze sc ON d.id = sc.id_documento
    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
    WHERE d.segno = 1
      AND date(substr(sc.data_scadenza, 7, 4) || '-' || 
               substr(sc.data_scadenza, 4, 2) || '-' || 
               substr(sc.data_scadenza, 1, 2)) < date('now')
    GROUP BY s.id, s.codice_soggetto, s.ragione_sociale
    HAVING (COALESCE(SUM(sc.importo_scadenza), 0) - 
            COALESCE(SUM(
                CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
            ), 0)) > 0.01
""")
    print("   ✓ Vista scaduto_clienti creata")
except Exception as e:
    print(f"   ❌ Errore creando scaduto_clienti: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Creo la vista scaduto_fornitori...")
# Vista per fornitori (documenti con segno=-1, fatture passive)
try:
    cursor.execute("""
    CREATE VIEW scaduto_fornitori AS
    SELECT 
        s.id AS soggetto_id,
        s.codice_soggetto,
        s.ragione_sociale,
        COUNT(DISTINCT CASE 
            WHEN date(substr(sc.data_scadenza, 7, 4) || '-' || 
                      substr(sc.data_scadenza, 4, 2) || '-' || 
                      substr(sc.data_scadenza, 1, 2)) < date('now')
            THEN sc.id 
        END) AS numero_scadenze_scadute,
        COALESCE(SUM(sc.importo_scadenza), 0) AS totale_scadenze,
        COALESCE(SUM(
            CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
        ), 0) AS totale_pagato,
        COALESCE(SUM(sc.importo_scadenza), 0) - 
        COALESCE(SUM(
            CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
        ), 0) AS saldo_scaduto
    FROM soggetti s
    JOIN documenti d ON s.id = d.soggetto_id
    JOIN scadenze sc ON d.id = sc.id_documento
    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
    WHERE d.segno = -1
      AND date(substr(sc.data_scadenza, 7, 4) || '-' || 
               substr(sc.data_scadenza, 4, 2) || '-' || 
               substr(sc.data_scadenza, 1, 2)) < date('now')
    GROUP BY s.id, s.codice_soggetto, s.ragione_sociale
    HAVING (COALESCE(SUM(sc.importo_scadenza), 0) - 
            COALESCE(SUM(
                CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END
            ), 0)) > 0.01
""")
    print("   ✓ Vista scaduto_fornitori creata")
except Exception as e:
    print(f"   ❌ Errore creando scaduto_fornitori: {e}")
    import traceback
    traceback.print_exc()

try:
    conn.commit()
    conn.close()
except Exception as e:
    print(f"   ❌ Errore nel commit: {e}")
    conn.rollback()
    conn.close()

print("\n" + "=" * 60)
print("✅ VISTE RICREATE CON SUCCESSO!")
print("=" * 60)

