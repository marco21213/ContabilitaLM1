#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per inserire dati di test per le note di credito
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

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

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Data di riferimento
    oggi = datetime.now()
    
    print("\n=== INSERIMENTO DATI DI TEST PER NOTE DI CREDITO ===\n")
    
    # 1. Crea o recupera un cliente di test
    print("1. Creazione cliente di test...")
    cur.execute("""
        SELECT id FROM soggetti 
        WHERE ragione_sociale = 'CLIENTE TEST NOTE CREDITO'
    """)
    cliente_test = cur.fetchone()
    
    if cliente_test:
        cliente_id = cliente_test[0]
        print(f"   Cliente esistente trovato (ID: {cliente_id})")
    else:
        # Verifica le colonne disponibili nella tabella soggetti
        cur.execute("PRAGMA table_info(soggetti)")
        colonne_soggetti = [col[1] for col in cur.fetchall()]
        
        if 'tipo_soggetto' in colonne_soggetti:
            cur.execute("""
                INSERT INTO soggetti (ragione_sociale, codice_soggetto, tipo_soggetto)
                VALUES (?, ?, ?)
            """, ("CLIENTE TEST NOTE CREDITO", "CLI-TEST-NC", "CLIENTE"))
        elif 'tipo' in colonne_soggetti:
            cur.execute("""
                INSERT INTO soggetti (ragione_sociale, codice_soggetto, tipo)
                VALUES (?, ?, ?)
            """, ("CLIENTE TEST NOTE CREDITO", "CLI-TEST-NC", "cliente"))
        else:
            cur.execute("""
                INSERT INTO soggetti (ragione_sociale, codice_soggetto)
                VALUES (?, ?)
            """, ("CLIENTE TEST NOTE CREDITO", "CLI-TEST-NC"))
        cliente_id = cur.lastrowid
        print(f"   Cliente creato (ID: {cliente_id})")
    
    # 2. TEST 1: Fattura cliente che verrà coperta completamente da una nota di credito
    print("\n2. TEST 1: Fattura cliente (coperta completamente da NC)...")
    data_fattura_1 = (oggi - timedelta(days=30)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-TEST-001", data_fattura_1, 
          oggi.strftime("%d/%m/%Y"), 1000.00, 820.00, 1))
    doc_id_1 = cur.lastrowid
    
    # Scadenza fattura 1
    data_scadenza_1 = (oggi + timedelta(days=30)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_1, data_scadenza_1, "BONIFICO", 1000.00))
    scadenza_id_1 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_1}, Scadenza ID: {scadenza_id_1}, Importo: €1000.00)")
    
    # Nota di credito che copre completamente la fattura 1
    data_nc_1 = (oggi - timedelta(days=5)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "NC_CLIENTE", "NC-TEST-001", data_nc_1, 
          oggi.strftime("%d/%m/%Y"), -1000.00, -820.00, -1))
    doc_nc_id_1 = cur.lastrowid
    
    # Scadenza nota di credito 1
    data_scadenza_nc_1 = (oggi + timedelta(days=60)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_nc_id_1, data_scadenza_nc_1, "BONIFICO", -1000.00))
    scadenza_nc_id_1 = cur.lastrowid
    print(f"   Nota di credito creata (ID: {doc_nc_id_1}, Scadenza ID: {scadenza_nc_id_1}, Importo: €1000.00)")
    
    # 3. TEST 2: Fattura cliente che verrà coperta parzialmente da una nota di credito
    print("\n3. TEST 2: Fattura cliente (coperta parzialmente da NC)...")
    data_fattura_2 = (oggi - timedelta(days=25)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-TEST-002", data_fattura_2, 
          oggi.strftime("%d/%m/%Y"), 2000.00, 1640.00, 1))
    doc_id_2 = cur.lastrowid
    
    # Scadenza fattura 2
    data_scadenza_2 = (oggi + timedelta(days=35)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_2, data_scadenza_2, "BONIFICO", 2000.00))
    scadenza_id_2 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_2}, Scadenza ID: {scadenza_id_2}, Importo: €2000.00)")
    
    # Nota di credito che copre parzialmente la fattura 2 (solo 800€ su 2000€)
    data_nc_2 = (oggi - timedelta(days=3)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "NC_CLIENTE", "NC-TEST-002", data_nc_2, 
          oggi.strftime("%d/%m/%Y"), -800.00, -656.00, -1))
    doc_nc_id_2 = cur.lastrowid
    
    # Scadenza nota di credito 2
    data_scadenza_nc_2 = (oggi + timedelta(days=90)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_nc_id_2, data_scadenza_nc_2, "BONIFICO", -800.00))
    scadenza_nc_id_2 = cur.lastrowid
    print(f"   Nota di credito creata (ID: {doc_nc_id_2}, Scadenza ID: {scadenza_nc_id_2}, Importo: €800.00)")
    print(f"   (Da applicare €800.00 su fattura da €2000.00 - residuo atteso: €1200.00)")
    
    # 4. TEST 3: Fattura cliente con RIBA che verrà coperta da una nota di credito
    print("\n4. TEST 3: Fattura cliente con RIBA (coperta da NC)...")
    data_fattura_3 = (oggi - timedelta(days=20)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-TEST-003", data_fattura_3, 
          oggi.strftime("%d/%m/%Y"), 1500.00, 1230.00, 1))
    doc_id_3 = cur.lastrowid
    
    # Scadenza fattura 3 con RIBA
    data_scadenza_3 = (oggi + timedelta(days=40)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_3, data_scadenza_3, "RIBA", 1500.00))
    scadenza_id_3 = cur.lastrowid
    
    # Crea la RIBA per la scadenza 3
    # Verifica se la tabella riba esiste e la sua struttura
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='riba'
    """)
    if cur.fetchone():
        # Verifica le colonne disponibili
        cur.execute("PRAGMA table_info(riba)")
        colonne_riba = [col[1] for col in cur.fetchall()]
        
        if 'distinta_numero' in colonne_riba and 'data_distinta' in colonne_riba:
            cur.execute("""
                INSERT INTO riba (scadenza_id, stato, distinta_numero, data_distinta)
                VALUES (?, ?, ?, ?)
            """, (scadenza_id_3, "Emessa", "RIBA-TEST-001", oggi.strftime("%d/%m/%Y")))
        elif 'data_scadenza' in colonne_riba and 'importo' in colonne_riba:
            cur.execute("""
                INSERT INTO riba (scadenza_id, data_scadenza, importo, stato)
                VALUES (?, ?, ?, ?)
            """, (scadenza_id_3, data_scadenza_3, 1500.00, "Emessa"))
        else:
            # Struttura minima
            cur.execute("""
                INSERT INTO riba (scadenza_id, stato)
                VALUES (?, ?)
            """, (scadenza_id_3, "Emessa"))
        
        riba_id = cur.lastrowid
        print(f"   Fattura con RIBA creata (ID: {doc_id_3}, Scadenza ID: {scadenza_id_3}, RIBA ID: {riba_id}, Importo: €1500.00)")
    else:
        print(f"   Fattura creata (ID: {doc_id_3}, Scadenza ID: {scadenza_id_3}, Importo: €1500.00)")
        print(f"   (Tabella RIBA non trovata - verrà creata automaticamente quando necessario)")
    
    # Nota di credito che copre completamente la fattura 3 con RIBA
    data_nc_3 = (oggi - timedelta(days=1)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "NC_CLIENTE", "NC-TEST-003", data_nc_3, 
          oggi.strftime("%d/%m/%Y"), -1500.00, -1230.00, -1))
    doc_nc_id_3 = cur.lastrowid
    
    # Scadenza nota di credito 3
    data_scadenza_nc_3 = (oggi + timedelta(days=120)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_nc_id_3, data_scadenza_nc_3, "BONIFICO", -1500.00))
    scadenza_nc_id_3 = cur.lastrowid
    print(f"   Nota di credito creata (ID: {doc_nc_id_3}, Scadenza ID: {scadenza_nc_id_3}, Importo: €1500.00)")
    print(f"   (Da applicare alla fattura con RIBA - la RIBA dovrebbe essere aggiornata a 'Pagata')")
    
    # Commit delle modifiche
    conn.commit()
    
    print("\n=== RIEPILOGO DATI INSERITI ===\n")
    print(f"Cliente Test: CLIENTE TEST NOTE CREDITO (ID: {cliente_id})\n")
    print("TEST 1 - NC che copre intera fattura:")
    print(f"  - Fattura FT-TEST-001: €1000.00 (Scadenza ID: {scadenza_id_1})")
    print(f"  - Nota Credito NC-TEST-001: €1000.00 (Scadenza ID: {scadenza_nc_id_1})")
    print(f"  → Applicare NC-TEST-001 a FT-TEST-001 per testare copertura completa\n")
    
    print("TEST 2 - NC che copre fattura in parte:")
    print(f"  - Fattura FT-TEST-002: €2000.00 (Scadenza ID: {scadenza_id_2})")
    print(f"  - Nota Credito NC-TEST-002: €800.00 (Scadenza ID: {scadenza_nc_id_2})")
    print(f"  → Applicare NC-TEST-002 a FT-TEST-002 per testare copertura parziale")
    print(f"  → Residuo atteso dopo applicazione: €1200.00\n")
    
    print("TEST 3 - NC con RIBA:")
    print(f"  - Fattura FT-TEST-003: €1500.00 con RIBA (Scadenza ID: {scadenza_id_3})")
    print(f"  - Nota Credito NC-TEST-003: €1500.00 (Scadenza ID: {scadenza_nc_id_3})")
    print(f"  → Applicare NC-TEST-003 a FT-TEST-003 per testare con RIBA")
    print(f"  → La RIBA dovrebbe essere aggiornata a 'Pagata' quando la NC viene applicata\n")
    
    print("✅ Dati di test inseriti con successo!")
    print("\nOra puoi testare l'applicazione delle note di credito nella sezione Pagamenti.")
    
    conn.close()
    
except sqlite3.Error as e:
    print(f"Errore database: {e}")
    if 'conn' in locals() and conn:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
    sys.exit(1)
except Exception as e:
    print(f"Errore generico: {e}")
    import traceback
    traceback.print_exc()
    if 'conn' in locals() and conn:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
    sys.exit(1)

