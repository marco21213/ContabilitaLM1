#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per completare la struttura del database se mancano tabelle
"""

import sqlite3
import sys
from pathlib import Path
import configparser

config_path = Path(__file__).parent.parent / "config.ini"
db_path = None

if config_path.exists():
    config = configparser.ConfigParser()
    config.read(config_path)
    db_path = config.get("Autenticazione", "percorso_database", fallback=None)
    if not db_path or not Path(db_path).exists():
        db_path = config.get("Database", "link", fallback=None)

if not db_path:
    print("Errore: Impossibile trovare il percorso del database")
    sys.exit(1)

print(f"Verifico database: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verifica tabelle esistenti
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables_existenti = [t[0] for t in cursor.fetchall()]

# Verifica se manca associazioni_pagamenti
if 'associazioni_pagamenti' not in tables_existenti:
    print("Creo tabella associazioni_pagamenti...")
    cursor.execute("""
        CREATE TABLE associazioni_pagamenti (
            id_associazione INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pagamento INTEGER NOT NULL,
            id_documento INTEGER NOT NULL,
            importo_associato REAL NOT NULL,
            data_associazione TEXT DEFAULT CURRENT_TIMESTAMP,
            tipo_associazione TEXT NOT NULL,
            FOREIGN KEY (id_pagamento) REFERENCES pagamenti(id),
            FOREIGN KEY (id_documento) REFERENCES documenti(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_pagamento ON associazioni_pagamenti(id_pagamento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_documento ON associazioni_pagamenti(id_documento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_tipo ON associazioni_pagamenti(tipo_associazione)")
    print("  ✓ Tabella creata")
else:
    print("  ✓ Tabella associazioni_pagamenti già presente")

# Verifica vista_movimenti
cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='vista_movimenti'")
if not cursor.fetchone():
    print("\nRicreo vista vista_movimenti...")
    cursor.execute("DROP VIEW IF EXISTS vista_movimenti")
    cursor.execute("""
        CREATE VIEW vista_movimenti AS 
        SELECT
            s.id AS soggetto_id,
            s.ragione_sociale,
            substr(d.data_documento, 7, 4) || '-' || substr(d.data_documento, 4, 2) || '-' || substr(d.data_documento, 1, 2) AS data_movimento,
            'Documento ' || d.tipo_documento || ' n.' || d.numero_documento AS descrizione,
            CASE WHEN d.segno = 1 THEN d.totale ELSE 0 END AS dare,
            CASE WHEN d.segno = -1 THEN d.totale ELSE 0 END AS avere
        FROM soggetti s
        JOIN documenti d ON s.id = d.soggetto_id
        
        UNION ALL
        
        SELECT
            s.id AS soggetto_id,
            s.ragione_sociale,
            CASE 
                WHEN length(p.data_pagamento) = 10 AND substr(p.data_pagamento, 5, 1) = '-' THEN
                    p.data_pagamento
                WHEN length(p.data_pagamento) = 10 AND substr(p.data_pagamento, 3, 1) = '/' THEN
                    substr(p.data_pagamento, 7, 4) || '-' || substr(p.data_pagamento, 4, 2) || '-' || substr(p.data_pagamento, 1, 2)
                ELSE
                    p.data_pagamento
            END AS data_movimento,
            CASE 
                WHEN p.modalita_pagamento = 'STORNO_NOTA_CREDITO' THEN
                    'Storno Nota Credito - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                ELSE
                    'Pagamento ' || COALESCE(p.modalita_pagamento, '') || ' - Doc. ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
            END AS descrizione,
            CASE 
                WHEN p.tipo_movimento = 'PAGAMENTO' THEN ap.importo_associato
                WHEN p.tipo_movimento IS NULL AND d.segno = -1 THEN ap.importo_associato
                ELSE 0
            END AS dare,
            CASE 
                WHEN p.tipo_movimento = 'INCASSO' THEN ap.importo_associato
                WHEN p.tipo_movimento IS NULL AND d.segno = 1 THEN ap.importo_associato
                ELSE 0
            END AS avere
        FROM soggetti s
        JOIN documenti d ON s.id = d.soggetto_id
        JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
        JOIN pagamenti p ON ap.id_pagamento = p.id
        WHERE ap.tipo_associazione = 'PAGAMENTO'
    """)
    print("  ✓ Vista creata")
else:
    print("  ✓ Vista vista_movimenti già presente")

conn.commit()
conn.close()

print("\n✅ Verifica completata!")

