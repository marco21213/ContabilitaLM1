#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di migrazione per la nuova struttura pagamenti
- Aggiunge colonna tipo_movimento a pagamenti
- Crea tabella associazioni_pagamenti
- Migra dati da pagamenti_scadenze e note_credito_applicate
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Percorso del database dal config
config_path = Path(__file__).parent.parent / "config.ini"
db_path = None
conn = None

if config_path.exists():
    import configparser
    config = configparser.ConfigParser()
    config.read(config_path)
    # Prova prima il percorso locale, poi quello di rete
    db_path = config.get("Autenticazione", "percorso_database", fallback=None)
    if not db_path or not Path(db_path).exists():
        db_path = config.get("Database", "link", fallback=None)

if not db_path:
    print("Errore: Impossibile trovare il percorso del database nel config.ini")
    sys.exit(1)

print(f"Connessione al database: {db_path}")
print("\n=== MIGRAZIONE NUOVA STRUTTURA PAGAMENTI ===\n")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # STEP 1: Verifica se tipo_movimento esiste già
    print("STEP 1: Verifica colonna tipo_movimento...")
    cur.execute("PRAGMA table_info(pagamenti)")
    colonne_pagamenti = [col[1] for col in cur.fetchall()]
    
    if 'tipo_movimento' not in colonne_pagamenti:
        print("   Aggiungo colonna tipo_movimento...")
        cur.execute("ALTER TABLE pagamenti ADD COLUMN tipo_movimento TEXT DEFAULT 'INCASSO'")
        print("   ✓ Colonna aggiunta")
    else:
        print("   ✓ Colonna tipo_movimento già esistente")
    
    # STEP 2: Determina tipo_movimento per pagamenti esistenti
    print("\nSTEP 2: Aggiorno tipo_movimento per pagamenti esistenti...")
    cur.execute("""
        UPDATE pagamenti 
        SET tipo_movimento = CASE 
            WHEN EXISTS (
                SELECT 1 FROM pagamenti_scadenze ps
                JOIN scadenze sc ON ps.scadenza_id = sc.id
                JOIN documenti d ON sc.id_documento = d.id
                WHERE ps.pagamento_id = pagamenti.id AND d.segno = 1
            ) THEN 'INCASSO'
            WHEN EXISTS (
                SELECT 1 FROM pagamenti_scadenze ps
                JOIN scadenze sc ON ps.scadenza_id = sc.id
                JOIN documenti d ON sc.id_documento = d.id
                WHERE ps.pagamento_id = pagamenti.id AND d.segno = -1
            ) THEN 'PAGAMENTO'
            ELSE 'INCASSO'  -- Default
        END
        WHERE tipo_movimento IS NULL OR tipo_movimento = 'INCASSO'
    """)
    count_updated = cur.rowcount
    print(f"   ✓ Aggiornati {count_updated} pagamenti")
    
    # STEP 3: Crea tabella associazioni_pagamenti
    print("\nSTEP 3: Creo tabella associazioni_pagamenti...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS associazioni_pagamenti (
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
    
    # Crea indici per performance
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_associazioni_pagamento 
        ON associazioni_pagamenti(id_pagamento)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_associazioni_documento 
        ON associazioni_pagamenti(id_documento)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_associazioni_tipo 
        ON associazioni_pagamenti(tipo_associazione)
    """)
    print("   ✓ Tabella e indici creati")
    
    # STEP 4: Migra dati da pagamenti_scadenze
    print("\nSTEP 4: Migro dati da pagamenti_scadenze...")
    cur.execute("SELECT COUNT(*) FROM pagamenti_scadenze")
    count_ps = cur.fetchone()[0]
    
    if count_ps > 0:
        cur.execute("""
            INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
            SELECT DISTINCT
                ps.pagamento_id,
                sc.id_documento,
                SUM(ps.importo) AS importo_totale,
                'PAGAMENTO',
                COALESCE(p.data_pagamento, CURRENT_TIMESTAMP)
            FROM pagamenti_scadenze ps
            JOIN scadenze sc ON ps.scadenza_id = sc.id
            JOIN pagamenti p ON ps.pagamento_id = p.id
            WHERE NOT EXISTS (
                SELECT 1 FROM associazioni_pagamenti ap
                WHERE ap.id_pagamento = ps.pagamento_id 
                AND ap.id_documento = sc.id_documento
            )
            GROUP BY ps.pagamento_id, sc.id_documento
        """)
        count_migrated_ps = cur.rowcount
        print(f"   ✓ Migrate {count_migrated_ps} associazioni da pagamenti_scadenze")
    else:
        print("   ℹ Nessun dato da migrare da pagamenti_scadenze")
    
    # STEP 5: Migra dati da note_credito_applicate
    print("\nSTEP 5: Migro dati da note_credito_applicate...")
    
    # Verifica se la tabella esiste
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='note_credito_applicate'
    """)
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM note_credito_applicate")
        count_nca = cur.fetchone()[0]
        
        if count_nca > 0:
            # Per ogni nota di credito applicata, crea un pagamento virtuale se non esiste
            # e poi crea l'associazione
            cur.execute("""
                INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, tipo_movimento, spese)
                SELECT DISTINCT
                    COALESCE(nca.data_applicazione, CURRENT_TIMESTAMP),
                    0,
                    0,
                    'STORNO_NOTA_CREDITO',
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM scadenze sc2
                            JOIN documenti d2 ON sc2.id_documento = d2.id
                            WHERE sc2.id = nca.nota_credito_scadenza_id AND d2.segno = -1
                        ) THEN 'INCASSO'
                        ELSE 'PAGAMENTO'
                    END,
                    0
                FROM note_credito_applicate nca
                WHERE NOT EXISTS (
                    SELECT 1 FROM pagamenti p
                    WHERE p.modalita_pagamento = 'STORNO_NOTA_CREDITO'
                    AND p.data_pagamento = COALESCE(nca.data_applicazione, CURRENT_TIMESTAMP)
                    AND ABS(p.importo_pagamento) < 0.01
                )
            """)
            
            # Ora crea le associazioni
            cur.execute("""
                INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
                SELECT 
                    p.id,
                    sc.id_documento,
                    nca.importo_applicato,
                    'STORNO_NOTA_CREDITO',
                    COALESCE(nca.data_applicazione, CURRENT_TIMESTAMP)
                FROM note_credito_applicate nca
                JOIN scadenze sc ON nca.scadenza_id = sc.id
                JOIN scadenze sc_nc ON nca.nota_credito_scadenza_id = sc_nc.id
                JOIN documenti d_nc ON sc_nc.id_documento = d_nc.id
                JOIN pagamenti p ON p.modalita_pagamento = 'STORNO_NOTA_CREDITO'
                    AND p.tipo_movimento = CASE 
                        WHEN d_nc.segno = -1 THEN 'INCASSO'
                        ELSE 'PAGAMENTO'
                    END
                    AND ABS(p.importo_pagamento) < 0.01
                WHERE NOT EXISTS (
                    SELECT 1 FROM associazioni_pagamenti ap
                    WHERE ap.id_pagamento = p.id 
                    AND ap.id_documento = sc.id_documento
                    AND ap.tipo_associazione = 'STORNO_NOTA_CREDITO'
                )
                GROUP BY p.id, sc.id_documento, nca.importo_applicato, nca.data_applicazione
            """)
            count_migrated_nca = cur.rowcount
            print(f"   ✓ Migrate {count_migrated_nca} associazioni da note_credito_applicate")
        else:
            print("   ℹ Nessun dato da migrare da note_credito_applicate")
    else:
        print("   ℹ Tabella note_credito_applicate non esiste")
    
    # Commit delle modifiche
    conn.commit()
    
    # Verifica risultati
    print("\n=== VERIFICA MIGRAZIONE ===\n")
    cur.execute("SELECT COUNT(*) FROM pagamenti WHERE tipo_movimento IS NOT NULL")
    count_pagamenti = cur.fetchone()[0]
    print(f"Pagamenti con tipo_movimento: {count_pagamenti}")
    
    cur.execute("SELECT COUNT(*) FROM associazioni_pagamenti")
    count_associazioni = cur.fetchone()[0]
    print(f"Associazioni create: {count_associazioni}")
    
    cur.execute("SELECT COUNT(*) FROM associazioni_pagamenti WHERE tipo_associazione = 'PAGAMENTO'")
    count_pagamenti_assoc = cur.fetchone()[0]
    print(f"  - Tipo PAGAMENTO: {count_pagamenti_assoc}")
    
    cur.execute("SELECT COUNT(*) FROM associazioni_pagamenti WHERE tipo_associazione = 'STORNO_NOTA_CREDITO'")
    count_storni_assoc = cur.fetchone()[0]
    print(f"  - Tipo STORNO_NOTA_CREDITO: {count_storni_assoc}")
    
    print("\n✅ Migrazione completata con successo!")
    print("\nNOTA: Le tabelle vecchie (pagamenti_scadenze, note_credito_applicate)")
    print("      sono state mantenute per sicurezza. Possono essere rimosse dopo")
    print("      aver verificato che tutto funzioni correttamente.")
    
    conn.close()
    
except sqlite3.Error as e:
    print(f"\n❌ Errore database: {e}")
    if 'conn' in locals() and conn:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Errore generico: {e}")
    import traceback
    traceback.print_exc()
    if 'conn' in locals() and conn:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
    sys.exit(1)

