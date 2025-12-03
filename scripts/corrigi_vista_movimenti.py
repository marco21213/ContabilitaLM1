"""
Script per correggere direttamente la vista vista_movimenti nel database
Assicura che i pagamenti vengano visualizzati correttamente
"""

import sqlite3
import configparser
import os
import sys

# Aggiungi il percorso della root del progetto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def correggi_vista_movimenti():
    """Corregge la vista vista_movimenti per includere correttamente i pagamenti"""
    
    # Carica configurazione
    config = configparser.ConfigParser()
    config_path = os.path.join(project_root, 'config.ini')
    config.read(config_path, encoding='utf-8')
    db_path = config.get('Autenticazione', 'percorso_database')
    
    # Se il percorso è relativo, risolvilo rispetto alla root del progetto
    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)
    
    print("=" * 70)
    print("CORREZIONE VISTA vista_movimenti")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"Esiste: {os.path.exists(db_path)}\n")
    
    if not os.path.exists(db_path):
        print("ERRORE: Database non trovato!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Verifica struttura database
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='associazioni_pagamenti'")
        has_associazioni = cur.fetchone() is not None
        
        cur.execute("PRAGMA table_info(pagamenti)")
        colonne_pag = [col[1] for col in cur.fetchall()]
        has_tipo_movimento = 'tipo_movimento' in colonne_pag
        has_segno = 'segno' in [col[1] for col in cur.execute("PRAGMA table_info(documenti)").fetchall()]
        
        print(f"✓ Tabella associazioni_pagamenti: {has_associazioni}")
        print(f"✓ Colonna tipo_movimento: {has_tipo_movimento}")
        print(f"✓ Colonna segno in documenti: {has_segno}")
        print()
        
        # Elimina la vecchia vista
        print("1. Elimino la vecchia vista...")
        cur.execute("DROP VIEW IF EXISTS vista_movimenti")
        conn.commit()
        print("   ✓ Vista eliminata\n")
        
        # Crea la nuova vista con logica corretta
        print("2. Creo la nuova vista con logica corretta...")
        
        if has_associazioni:
            # Usa associazioni_pagamenti (nuova struttura)
            if has_tipo_movimento and has_segno:
                # Logica completa: usa tipo_movimento e segno
                vista_sql = """
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
                """
            elif has_segno:
                # Solo segno, senza tipo_movimento
                vista_sql = """
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
                    -- Logica corretta: pagamenti a fornitori → Dare, incassi da clienti → Avere
                    CASE WHEN d.segno = -1 THEN ap.importo_associato ELSE 0 END AS dare,
                    CASE WHEN d.segno = 1 THEN ap.importo_associato ELSE 0 END AS avere
                FROM soggetti s
                JOIN documenti d ON s.id = d.soggetto_id
                JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                JOIN pagamenti p ON ap.id_pagamento = p.id
                WHERE ap.tipo_associazione = 'PAGAMENTO'
                """
            else:
                # Fallback: solo tipo_movimento
                vista_sql = """
                CREATE VIEW vista_movimenti AS 
                SELECT
                    s.id AS soggetto_id,
                    s.ragione_sociale,
                    substr(d.data_documento, 7, 4) || '-' || substr(d.data_documento, 4, 2) || '-' || substr(d.data_documento, 1, 2) AS data_movimento,
                    'Documento ' || d.tipo_documento || ' n.' || d.numero_documento AS descrizione,
                    0 AS dare,
                    d.totale AS avere
                FROM soggetti s
                JOIN documenti d ON s.id = d.soggetto_id
                
                UNION ALL
                
                SELECT
                    s.id AS soggetto_id,
                    s.ragione_sociale,
                    p.data_pagamento AS data_movimento,
                    'Pagamento ' || COALESCE(p.modalita_pagamento, '') || ' - Doc. ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '') AS descrizione,
                    CASE WHEN p.tipo_movimento = 'INCASSO' THEN ap.importo_associato ELSE 0 END AS dare,
                    CASE WHEN p.tipo_movimento = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END AS avere
                FROM soggetti s
                JOIN documenti d ON s.id = d.soggetto_id
                JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                JOIN pagamenti p ON ap.id_pagamento = p.id
                WHERE ap.tipo_associazione = 'PAGAMENTO'
                """
        else:
            # Vecchia struttura con pagamenti_scadenze
            vista_sql = """
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
                p.data_pagamento AS data_movimento,
                'Pagamento ' || p.modalita_pagamento AS descrizione,
                CASE WHEN d.segno = -1 THEN ps.importo ELSE 0 END AS dare,
                CASE WHEN d.segno = 1 THEN ps.importo ELSE 0 END AS avere
            FROM soggetti s
            JOIN documenti d ON s.id = d.soggetto_id
            JOIN scadenze sc ON d.id = sc.id_documento
            JOIN pagamenti_scadenze ps ON sc.id = ps.scadenza_id
            JOIN pagamenti p ON ps.pagamento_id = p.id
            """
        
        cur.execute(vista_sql)
        conn.commit()
        print("   ✓ Vista creata\n")
        
        # Verifica
        print("3. Verifica della vista...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='vista_movimenti'")
        if not cur.fetchone():
            print("   ✗ ERRORE: Vista non creata!")
            return False
        print("   ✓ Vista esistente\n")
        
        # Test: conta movimenti
        cur.execute("SELECT COUNT(*) FROM vista_movimenti")
        count_totale = cur.fetchone()[0]
        print(f"   ✓ Movimenti totali: {count_totale}")
        
        # Test: conta pagamenti
        cur.execute("SELECT COUNT(*) FROM vista_movimenti WHERE descrizione LIKE 'Pagamento%' OR descrizione LIKE 'Storno%'")
        count_pagamenti = cur.fetchone()[0]
        print(f"   ✓ Pagamenti trovati: {count_pagamenti}")
        
        # Test: esempio movimenti
        print("\n4. Esempio movimenti (primi 5):")
        cur.execute("SELECT data_movimento, descrizione, dare, avere FROM vista_movimenti ORDER BY data_movimento LIMIT 5")
        for row in cur.fetchall():
            print(f"   {row[0]} | {row[1][:50]:50} | Dare: {row[2]:>10.2f} | Avere: {row[3]:>10.2f}")
        
        # Test: esempio pagamenti
        print("\n5. Esempio pagamenti (primi 3):")
        cur.execute("SELECT data_movimento, descrizione, dare, avere FROM vista_movimenti WHERE descrizione LIKE 'Pagamento%' OR descrizione LIKE 'Storno%' ORDER BY data_movimento LIMIT 3")
        pagamenti = cur.fetchall()
        if pagamenti:
            for row in pagamenti:
                print(f"   {row[0]} | {row[1][:50]:50} | Dare: {row[2]:>10.2f} | Avere: {row[3]:>10.2f}")
        else:
            print("   ⚠ Nessun pagamento trovato nella vista!")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ CORREZIONE COMPLETATA")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = correggi_vista_movimenti()
    sys.exit(0 if success else 1)

