#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per inserire dati di test completi per la nuova struttura pagamenti
Testa tutti i casi d'uso: pagamenti parziali, note di credito, pagamenti multipli, ecc.
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
    db_path = config.get("Autenticazione", "percorso_database", fallback=None)
    if not db_path or not Path(db_path).exists():
        db_path = config.get("Database", "link", fallback=None)

if not db_path:
    print("Errore: Impossibile trovare il percorso del database nel config.ini")
    sys.exit(1)

print(f"Connessione al database: {db_path}")
print("\n=== INSERIMENTO DATI DI TEST - NUOVA STRUTTURA ===\n")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Data di riferimento
    oggi = datetime.now()
    
    # 1. Crea o recupera un cliente di test
    print("1. Creazione cliente di test...")
    cur.execute("""
        SELECT id FROM soggetti 
        WHERE ragione_sociale = 'CLIENTE TEST NUOVA STRUTTURA'
    """)
    cliente_test = cur.fetchone()
    
    if cliente_test:
        cliente_id = cliente_test[0]
        print(f"   Cliente esistente trovato (ID: {cliente_id})")
    else:
        cur.execute("PRAGMA table_info(soggetti)")
        colonne_soggetti = [col[1] for col in cur.fetchall()]
        
        if 'tipo_soggetto' in colonne_soggetti:
            cur.execute("""
                INSERT INTO soggetti (ragione_sociale, codice_soggetto, tipo_soggetto)
                VALUES (?, ?, ?)
            """, ("CLIENTE TEST NUOVA STRUTTURA", "CLI-TEST-NS", "CLIENTE"))
        else:
            cur.execute("""
                INSERT INTO soggetti (ragione_sociale, codice_soggetto)
                VALUES (?, ?)
            """, ("CLIENTE TEST NUOVA STRUTTURA", "CLI-TEST-NS"))
        cliente_id = cur.lastrowid
        print(f"   Cliente creato (ID: {cliente_id})")
    
    # 2. TEST 1: Fattura totalmente stornata da nota di credito
    print("\n2. TEST 1: Fattura totalmente stornata da NC...")
    data_fattura_1 = (oggi - timedelta(days=30)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-NS-001", data_fattura_1, 
          oggi.strftime("%d/%m/%Y"), 1000.00, 820.00, 1))
    doc_id_1 = cur.lastrowid
    
    data_scadenza_1 = (oggi + timedelta(days=30)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_1, data_scadenza_1, "BONIFICO", 1000.00))
    scadenza_id_1 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_1}, Scadenza ID: {scadenza_id_1}, Importo: €1000.00)")
    
    # Nota di credito che copre completamente
    data_nc_1 = (oggi - timedelta(days=5)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "NC_CLIENTE", "NC-NS-001", data_nc_1, 
          oggi.strftime("%d/%m/%Y"), -1000.00, -820.00, -1))
    doc_nc_id_1 = cur.lastrowid
    
    data_scadenza_nc_1 = (oggi + timedelta(days=60)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_nc_id_1, data_scadenza_nc_1, "BONIFICO", -1000.00))
    scadenza_nc_id_1 = cur.lastrowid
    print(f"   Nota di credito creata (ID: {doc_nc_id_1}, Scadenza ID: {scadenza_nc_id_1}, Importo: €1000.00)")
    
    # Crea pagamento e associazione per lo storno
    # Usa 'NOTA_CREDITO_APPLICATA' per la modalità (valore valido nel constraint)
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (oggi.strftime("%d/%m/%Y"), 0, 0, "NOTA_CREDITO_APPLICATA", 0, "INCASSO"))
    pagamento_nc_1_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_nc_1_id, doc_id_1, 1000.00, "STORNO_NOTA_CREDITO", oggi.strftime("%d/%m/%Y")))
    print(f"   ✓ Storno creato: NC-NS-001 → FT-NS-001 (€1000.00)")
    
    # 3. TEST 2: Storno parziale + pagamento
    print("\n3. TEST 2: Storno parziale + pagamento...")
    data_fattura_2 = (oggi - timedelta(days=25)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-NS-002", data_fattura_2, 
          oggi.strftime("%d/%m/%Y"), 5000.00, 4100.00, 1))
    doc_id_2 = cur.lastrowid
    
    data_scadenza_2 = (oggi + timedelta(days=35)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_2, data_scadenza_2, "BONIFICO", 5000.00))
    scadenza_id_2 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_2}, Scadenza ID: {scadenza_id_2}, Importo: €5000.00)")
    
    # Nota di credito parziale
    data_nc_2 = (oggi - timedelta(days=3)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "NC_CLIENTE", "NC-NS-002", data_nc_2, 
          oggi.strftime("%d/%m/%Y"), -1000.00, -820.00, -1))
    doc_nc_id_2 = cur.lastrowid
    
    data_scadenza_nc_2 = (oggi + timedelta(days=90)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_nc_id_2, data_scadenza_nc_2, "BONIFICO", -1000.00))
    scadenza_nc_id_2 = cur.lastrowid
    print(f"   Nota di credito creata (ID: {doc_nc_id_2}, Scadenza ID: {scadenza_nc_id_2}, Importo: €1000.00)")
    
    # Storno parziale
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (oggi.strftime("%d/%m/%Y"), 0, 0, "NOTA_CREDITO_APPLICATA", 0, "INCASSO"))
    pagamento_nc_2_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_nc_2_id, doc_id_2, 1000.00, "STORNO_NOTA_CREDITO", oggi.strftime("%d/%m/%Y")))
    print(f"   ✓ Storno creato: NC-NS-002 → FT-NS-002 (€1000.00)")
    
    # Pagamento parziale
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (oggi.strftime("%d/%m/%Y"), 4000.00, 4000.00, "BONIFICO", 0, "INCASSO"))
    pagamento_2_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_2_id, doc_id_2, 4000.00, "PAGAMENTO", oggi.strftime("%d/%m/%Y")))
    print(f"   ✓ Pagamento creato: FT-NS-002 (€4000.00)")
    print(f"   → Residuo atteso: €0.00 (5000 - 1000 - 4000)")
    
    # 4. TEST 3: Pagamenti parziali multipli
    print("\n4. TEST 3: Pagamenti parziali multipli...")
    data_fattura_3 = (oggi - timedelta(days=20)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-NS-003", data_fattura_3, 
          oggi.strftime("%d/%m/%Y"), 10000.00, 8200.00, 1))
    doc_id_3 = cur.lastrowid
    
    data_scadenza_3 = (oggi + timedelta(days=40)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_3, data_scadenza_3, "BONIFICO", 10000.00))
    scadenza_id_3 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_3}, Scadenza ID: {scadenza_id_3}, Importo: €10000.00)")
    
    # Primo pagamento parziale
    data_pag_3_1 = (oggi - timedelta(days=15)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data_pag_3_1, 3000.00, 3000.00, "BONIFICO", 0, "INCASSO"))
    pagamento_3_1_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_3_1_id, doc_id_3, 3000.00, "PAGAMENTO", data_pag_3_1))
    print(f"   ✓ Pagamento 1: €3000.00 ({data_pag_3_1})")
    
    # Secondo pagamento parziale
    data_pag_3_2 = (oggi - timedelta(days=10)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data_pag_3_2, 2000.00, 2000.00, "ASSEGNO BANCARIO", 0, "INCASSO"))
    pagamento_3_2_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_3_2_id, doc_id_3, 2000.00, "PAGAMENTO", data_pag_3_2))
    print(f"   ✓ Pagamento 2: €2000.00 ({data_pag_3_2})")
    
    # Terzo pagamento parziale (chiude la fattura)
    data_pag_3_3 = (oggi - timedelta(days=5)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data_pag_3_3, 5000.00, 5000.00, "BONIFICO", 0, "INCASSO"))
    pagamento_3_3_id = cur.lastrowid
    
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_3_3_id, doc_id_3, 5000.00, "PAGAMENTO", data_pag_3_3))
    print(f"   ✓ Pagamento 3: €5000.00 ({data_pag_3_3})")
    print(f"   → Totale pagato: €10000.00 (fattura saldata)")
    
    # 5. TEST 4: Pagamento multi-fattura
    print("\n5. TEST 4: Pagamento multi-fattura...")
    # Crea 3 fatture
    fatture_multi = []
    for i in range(3):
        data_fatt = (oggi - timedelta(days=15-i*2)).strftime("%d/%m/%Y")
        cur.execute("""
            INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                                  data_documento, data_registrazione, totale, importo_imponibile, segno)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, "FT_VENDITA", f"FT-NS-004-{i+1}", data_fatt, 
              oggi.strftime("%d/%m/%Y"), (3000 + i*500), (2460 + i*410), 1))
        doc_id = cur.lastrowid
        
        data_scad = (oggi + timedelta(days=30+i*5)).strftime("%d/%m/%Y")
        cur.execute("""
            INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
            VALUES (?, ?, ?, ?)
        """, (doc_id, data_scad, "BONIFICO", (3000 + i*500)))
        scadenza_id = cur.lastrowid
        fatture_multi.append((doc_id, 3000 + i*500))
        print(f"   Fattura {i+1} creata (ID: {doc_id}, Importo: €{3000 + i*500:.2f})")
    
    # Un solo pagamento per tutte e 3
    data_pag_multi = oggi.strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data_pag_multi, 8000.00, 8000.00, "BONIFICO", 0, "INCASSO"))
    pagamento_multi_id = cur.lastrowid
    
    # Associa a tutte e 3 le fatture
    for doc_id, importo in fatture_multi:
        cur.execute("""
            INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
            VALUES (?, ?, ?, ?, ?)
        """, (pagamento_multi_id, doc_id, importo, "PAGAMENTO", data_pag_multi))
    print(f"   ✓ Pagamento unico (ID: {pagamento_multi_id}) associato a 3 fatture (€8000.00)")
    
    # 6. TEST 5: Bonifico con costi bancari
    print("\n6. TEST 5: Bonifico con costi bancari...")
    data_fattura_5 = (oggi - timedelta(days=10)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO documenti (soggetto_id, tipo_documento, numero_documento, 
                              data_documento, data_registrazione, totale, importo_imponibile, segno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, "FT_VENDITA", "FT-NS-005", data_fattura_5, 
          oggi.strftime("%d/%m/%Y"), 5000.00, 4100.00, 1))
    doc_id_5 = cur.lastrowid
    
    data_scadenza_5 = (oggi + timedelta(days=20)).strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
        VALUES (?, ?, ?, ?)
    """, (doc_id_5, data_scadenza_5, "BONIFICO", 5000.00))
    scadenza_id_5 = cur.lastrowid
    print(f"   Fattura creata (ID: {doc_id_5}, Scadenza ID: {scadenza_id_5}, Importo: €5000.00)")
    
    # Pagamento con costi bancari
    data_pag_5 = oggi.strftime("%d/%m/%Y")
    cur.execute("""
        INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data_pag_5, 4965.00, 5000.00, "BONIFICO", 35.00, "INCASSO"))
    pagamento_5_id = cur.lastrowid
    
    # Associa solo l'importo netto al documento
    cur.execute("""
        INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione)
        VALUES (?, ?, ?, ?, ?)
    """, (pagamento_5_id, doc_id_5, 4965.00, "PAGAMENTO", data_pag_5))
    print(f"   ✓ Pagamento creato: €4965.00 (lordi €5000.00, costi €35.00)")
    print(f"   → Costi bancari registrati ma non associati al documento")
    
    # Commit delle modifiche
    conn.commit()
    
    print("\n=== RIEPILOGO DATI INSERITI ===\n")
    print(f"Cliente Test: CLIENTE TEST NUOVA STRUTTURA (ID: {cliente_id})\n")
    print("TEST 1 - Fattura totalmente stornata:")
    print(f"  - Fattura FT-NS-001: €1000.00")
    print(f"  - Nota Credito NC-NS-001: €1000.00")
    print(f"  → Storno completo (residuo: €0.00)\n")
    
    print("TEST 2 - Storno parziale + pagamento:")
    print(f"  - Fattura FT-NS-002: €5000.00")
    print(f"  - Nota Credito NC-NS-002: €1000.00 (storno)")
    print(f"  - Pagamento: €4000.00")
    print(f"  → Residuo: €0.00\n")
    
    print("TEST 3 - Pagamenti parziali multipli:")
    print(f"  - Fattura FT-NS-003: €10000.00")
    print(f"  - Pagamento 1: €3000.00")
    print(f"  - Pagamento 2: €2000.00")
    print(f"  - Pagamento 3: €5000.00")
    print(f"  → Totale pagato: €10000.00 (fattura saldata)\n")
    
    print("TEST 4 - Pagamento multi-fattura:")
    print(f"  - 3 Fatture: €3000.00, €3500.00, €4000.00")
    print(f"  - Pagamento unico: €8000.00")
    print(f"  → Un solo movimento bancario, 3 associazioni\n")
    
    print("TEST 5 - Bonifico con costi:")
    print(f"  - Fattura FT-NS-005: €5000.00")
    print(f"  - Pagamento: €4965.00 (costi €35.00)")
    print(f"  → Costi registrati ma non associati al documento\n")
    
    print("✅ Dati di test inseriti con successo!")
    print("\nOra puoi testare la nuova struttura nella sezione Pagamenti.")
    
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

