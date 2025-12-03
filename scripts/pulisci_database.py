#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per pulire completamente il database e ricreare la struttura da zero.
ATTENZIONE: Questo script elimina TUTTI i dati!
"""

import sqlite3
import sys
import shutil
from pathlib import Path
from datetime import datetime
import configparser

# Controlla se è stato passato il parametro --yes
skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv

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

db_path = Path(db_path)

print("=" * 60)
print("PULIZIA COMPLETA DATABASE")
print("=" * 60)
print(f"\nDatabase: {db_path}")
print(f"ATTENZIONE: Tutti i dati verranno eliminati!")

if not skip_confirmation:
    print("\nVuoi continuare? (s/n): ", end="")
    risposta = input().strip().lower()
    if risposta != 's':
        print("Operazione annullata.")
        sys.exit(0)
else:
    print("\nConferma saltata (--yes)")

# Crea backup
backup_dir = db_path.parent / "backup"
backup_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backup_dir / f"database_backup_{timestamp}.db"

print(f"\n1. Creo backup in: {backup_path}")
try:
    shutil.copy2(db_path, backup_path)
    print("   ✓ Backup creato con successo")
except Exception as e:
    print(f"   ⚠ Errore nel backup: {e}")
    print("   Continuo comunque...")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n2. Elimino tutte le tabelle (mantengo le viste)...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            print(f"   ✓ Eliminata tabella: {table[0]}")
        except Exception as e:
            print(f"   ⚠ Errore eliminando tabella {table[0]}: {e}")
    
    conn.commit()
    
    print("\n4. Ricreo la struttura del database...")
    
    # Tabella: soggetti
    print("   - Creo tabella soggetti...")
    cursor.execute("""
        CREATE TABLE soggetti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice_soggetto TEXT UNIQUE NOT NULL,
            ragione_sociale TEXT NOT NULL,
            tipo_soggetto TEXT,
            codice_fiscale TEXT,
            partita_iva TEXT,
            indirizzo TEXT,
            citta TEXT,
            cap TEXT,
            provincia TEXT,
            telefono TEXT,
            email TEXT,
            codice_univoco TEXT
        )
    """)
    
    # Tabella: documenti
    print("   - Creo tabella documenti...")
    cursor.execute("""
        CREATE TABLE documenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            soggetto_id INTEGER NOT NULL,
            tipo_documento TEXT NOT NULL,
            numero_documento TEXT NOT NULL,
            data_documento TEXT NOT NULL,
            data_registrazione TEXT,
            totale REAL NOT NULL,
            importo_imponibile REAL,
            segno INTEGER DEFAULT 1,
            FOREIGN KEY (soggetto_id) REFERENCES soggetti(id)
        )
    """)
    
    # Tabella: scadenze
    print("   - Creo tabella scadenze...")
    cursor.execute("""
        CREATE TABLE scadenze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_documento INTEGER NOT NULL,
            numero_rata INTEGER DEFAULT 1,
            data_scadenza TEXT NOT NULL,
            tipo_pagamento TEXT,
            importo_scadenza REAL NOT NULL,
            FOREIGN KEY (id_documento) REFERENCES documenti(id)
        )
    """)
    
    # Tabella: pagamenti
    print("   - Creo tabella pagamenti...")
    cursor.execute("""
        CREATE TABLE pagamenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_pagamento TEXT NOT NULL,
            importo_pagamento REAL NOT NULL,
            totale REAL NOT NULL,
            modalita_pagamento TEXT,
            spese REAL DEFAULT 0,
            tipo_movimento TEXT DEFAULT 'INCASSO'
        )
    """)
    
    # Tabella: associazioni_pagamenti
    print("   - Creo tabella associazioni_pagamenti...")
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
    
    # Tabella: utenti
    print("   - Creo tabella utenti...")
    cursor.execute("""
        CREATE TABLE utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            ruolo TEXT NOT NULL CHECK(ruolo IN ('Amministratore', 'Utente', 'Sola Lettura')),
            attivo BOOLEAN DEFAULT 1,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inserisci utente admin predefinito
    import hashlib
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
        INSERT INTO utenti (username, password_hash, ruolo, attivo)
        VALUES (?, ?, ?, 1)
    """, ('admin', admin_password, 'Amministratore'))
    
    # Tabella: banche
    print("   - Creo tabella banche...")
    cursor.execute("""
        CREATE TABLE banche (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice_abi TEXT,
            codice_cab TEXT,
            denominazione TEXT NOT NULL,
            indirizzo TEXT,
            citta TEXT,
            cap TEXT
        )
    """)
    
    # Tabella: riba
    print("   - Creo tabella riba...")
    cursor.execute("""
        CREATE TABLE riba (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scadenza_id INTEGER NOT NULL,
            numero_riba TEXT,
            data_riba TEXT,
            stato TEXT DEFAULT 'PENDING',
            FOREIGN KEY (scadenza_id) REFERENCES scadenze(id)
        )
    """)
    
    # Tabella: distinte_riba
    print("   - Creo tabella distinte_riba...")
    cursor.execute("""
        CREATE TABLE distinte_riba (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_distinta TEXT UNIQUE NOT NULL,
            data_distinta TEXT NOT NULL,
            banca_id INTEGER,
            stato TEXT DEFAULT 'PENDING',
            FOREIGN KEY (banca_id) REFERENCES banche(id)
        )
    """)
    
    # Tabella: lockouts
    print("   - Creo tabella lockouts...")
    cursor.execute("""
        CREATE TABLE lockouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            tentativi INTEGER DEFAULT 0,
            data_blocco DATETIME,
            FOREIGN KEY (username) REFERENCES utenti(username)
        )
    """)
    
    # Tabella: login_logs
    print("   - Creo tabella login_logs...")
    cursor.execute("""
        CREATE TABLE login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            data_login DATETIME DEFAULT CURRENT_TIMESTAMP,
            esito TEXT NOT NULL,
            ip_address TEXT
        )
    """)
    
    # Crea indici per migliorare le performance
    print("\n5. Creo indici...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documenti_soggetto ON documenti(soggetto_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scadenze_documento ON scadenze(id_documento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_pagamento ON associazioni_pagamenti(id_pagamento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_documento ON associazioni_pagamenti(id_documento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_associazioni_tipo ON associazioni_pagamenti(tipo_associazione)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_riba_scadenza ON riba(scadenza_id)")
    
    conn.commit()
    
    print("\n6. Ricreo la vista vista_movimenti...")
    cursor.execute("DROP VIEW IF EXISTS vista_movimenti")
    cursor.execute("""
        CREATE VIEW vista_movimenti AS 
        -- PARTE 1: Documenti (fatture, note di credito, ecc.)
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
        
        -- PARTE 2: Pagamenti dalla nuova struttura associazioni_pagamenti
        SELECT
            s.id AS soggetto_id,
            s.ragione_sociale,
            -- Assicura che la data sia in formato ISO (YYYY-MM-DD)
            CASE 
                WHEN length(p.data_pagamento) = 10 AND substr(p.data_pagamento, 5, 1) = '-' THEN
                    p.data_pagamento  -- Già in formato ISO
                WHEN length(p.data_pagamento) = 10 AND substr(p.data_pagamento, 3, 1) = '/' THEN
                    -- Converti da DD/MM/YYYY a YYYY-MM-DD
                    substr(p.data_pagamento, 7, 4) || '-' || substr(p.data_pagamento, 4, 2) || '-' || substr(p.data_pagamento, 1, 2)
                ELSE
                    p.data_pagamento  -- Fallback
            END AS data_movimento,
            CASE 
                WHEN p.modalita_pagamento = 'STORNO_NOTA_CREDITO' THEN
                    'Storno Nota Credito - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                ELSE
                    'Pagamento ' || COALESCE(p.modalita_pagamento, '') || ' - Doc. ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
            END AS descrizione,
            -- Logica corretta per libro mastro:
            -- INCASSO (ricevuto da cliente) → Avere (diminuisce il credito)
            -- PAGAMENTO (pagato a fornitore) → Dare (diminuisce il debito)
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
    print("   ✓ Vista vista_movimenti creata")
    
    print("\n7. Ricreo le viste scaduto_clienti e scaduto_fornitori...")
    cursor.execute("DROP VIEW IF EXISTS scaduto_clienti")
    cursor.execute("DROP VIEW IF EXISTS scaduto_fornitori")
    
    # Vista per clienti (documenti con segno=1, fatture attive)
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
    
    # Vista per fornitori (documenti con segno=-1, fatture passive)
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
    
    conn.commit()
    
    print("\n" + "=" * 60)
    print("✅ PULIZIA COMPLETATA CON SUCCESSO!")
    print("=" * 60)
    print(f"\nBackup salvato in: {backup_path}")
    print("\nIl database è stato completamente ripulito e ricreato.")
    print("Utente admin predefinito creato:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nOra puoi iniziare a inserire nuovi dati di test.")
    
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

