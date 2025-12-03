"""
Script per aggiornare la vista vista_movimenti
per usare la nuova struttura associazioni_pagamenti
invece della vecchia pagamenti_scadenze
"""

import sqlite3
import configparser
import os
import sys

# Aggiungi il percorso della root del progetto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def aggiorna_vista_movimenti():
    """Aggiorna la vista vista_movimenti per usare associazioni_pagamenti"""
    
    # Carica configurazione
    config = configparser.ConfigParser()
    config_path = os.path.join(project_root, 'config.ini')
    config.read(config_path, encoding='utf-8')
    db_path = config.get('Autenticazione', 'percorso_database')
    
    # Se il percorso è relativo, risolvilo rispetto alla root del progetto
    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)
    
    print(f"Database: {db_path}")
    print(f"Esiste: {os.path.exists(db_path)}")
    print()
    
    if not os.path.exists(db_path):
        print("ERRORE: Database non trovato!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Verifica se esiste associazioni_pagamenti
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='associazioni_pagamenti'")
        has_associazioni = cur.fetchone() is not None
        
        # Verifica se esiste tipo_movimento
        cur.execute("PRAGMA table_info(pagamenti)")
        colonne_pag = [col[1] for col in cur.fetchall()]
        has_tipo_movimento = 'tipo_movimento' in colonne_pag
        
        print(f"Tabella associazioni_pagamenti esiste: {has_associazioni}")
        print(f"Colonna tipo_movimento esiste: {has_tipo_movimento}")
        print()
        
        if not has_associazioni:
            print("ATTENZIONE: La tabella associazioni_pagamenti non esiste.")
            print("La vista verrà aggiornata per usare pagamenti_scadenze (vecchia struttura).")
            print()
        
        # Elimina la vecchia vista
        print("Elimino la vecchia vista vista_movimenti...")
        cur.execute("DROP VIEW IF EXISTS vista_movimenti")
        print("✓ Vista eliminata")
        print()
        
        # Crea la nuova vista
        print("Creo la nuova vista vista_movimenti...")
        
        if has_associazioni:
            # Nuova struttura con associazioni_pagamenti
            if has_tipo_movimento:
                # Con tipo_movimento
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
                
                -- Pagamenti dalla nuova struttura associazioni_pagamenti
                SELECT
                    s.id AS soggetto_id,
                    s.ragione_sociale,
                    p.data_pagamento AS data_movimento,
                    CASE 
                        WHEN p.modalita_pagamento = 'STORNO_NOTA_CREDITO' THEN
                            'Storno Nota Credito - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                        ELSE
                            'Pagamento ' || COALESCE(p.modalita_pagamento, '') || ' - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                    END AS descrizione,
                    CASE 
                        WHEN p.tipo_movimento = 'INCASSO' OR (p.tipo_movimento IS NULL AND d.segno = 1) THEN
                            ap.importo_associato
                        ELSE 0
                    END AS dare,
                    CASE 
                        WHEN p.tipo_movimento = 'PAGAMENTO' OR (p.tipo_movimento IS NULL AND d.segno = -1) THEN
                            ap.importo_associato
                        ELSE 0
                    END AS avere
                FROM soggetti s
                JOIN documenti d ON s.id = d.soggetto_id
                JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                JOIN pagamenti p ON ap.id_pagamento = p.id
                WHERE ap.tipo_associazione = 'PAGAMENTO'
                """
            else:
                # Senza tipo_movimento, usa solo segno
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
                
                -- Pagamenti dalla nuova struttura associazioni_pagamenti
                SELECT
                    s.id AS soggetto_id,
                    s.ragione_sociale,
                    p.data_pagamento AS data_movimento,
                    CASE 
                        WHEN p.modalita_pagamento = 'STORNO_NOTA_CREDITO' THEN
                            'Storno Nota Credito - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                        ELSE
                            'Pagamento ' || COALESCE(p.modalita_pagamento, '') || ' - ' || COALESCE(d.tipo_documento || ' ' || d.numero_documento, '')
                    END AS descrizione,
                    CASE WHEN d.segno = 1 THEN ap.importo_associato ELSE 0 END AS dare,
                    CASE WHEN d.segno = -1 THEN ap.importo_associato ELSE 0 END AS avere
                FROM soggetti s
                JOIN documenti d ON s.id = d.soggetto_id
                JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                JOIN pagamenti p ON ap.id_pagamento = p.id
                WHERE ap.tipo_associazione = 'PAGAMENTO'
                """
        else:
            # Vecchia struttura con pagamenti_scadenze (mantenuta per compatibilità)
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
            
            -- Movimenti da pagamenti (vecchia struttura pagamenti_scadenze)
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
        print("✓ Vista creata con successo")
        print()
        
        # Verifica che la vista sia stata creata
        cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='vista_movimenti'")
        if cur.fetchone():
            print("✓ Verifica: Vista vista_movimenti creata correttamente")
        else:
            print("✗ ERRORE: La vista non è stata creata!")
            return False
        
        # Test: conta i movimenti
        cur.execute("SELECT COUNT(*) FROM vista_movimenti")
        count = cur.fetchone()[0]
        print(f"✓ Test: La vista contiene {count} movimenti")
        print()
        
        conn.close()
        print("=== AGGIORNAMENTO COMPLETATO ===")
        return True
        
    except Exception as e:
        print(f"ERRORE durante l'aggiornamento: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AGGIORNAMENTO VISTA vista_movimenti")
    print("=" * 60)
    print()
    
    success = aggiorna_vista_movimenti()
    
    if success:
        print("\n✓ Operazione completata con successo!")
        sys.exit(0)
    else:
        print("\n✗ Operazione fallita!")
        sys.exit(1)

