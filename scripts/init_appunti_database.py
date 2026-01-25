"""
Script per inizializzare la tabella appunti nel database.
Gestisce appunti generici suddivisi per argomento.
"""
import os
import sys
from pathlib import Path

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from db_manager import get_connection


def init_appunti_tables():
    """Crea la tabella appunti nel database e gestisce la migrazione dalla vecchia struttura."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verifica se la tabella esiste già
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='appunti'
        """)
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Verifica la struttura della tabella esistente
            cursor.execute("PRAGMA table_info(appunti)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Se esiste la colonna argomento, dobbiamo migrare
            if 'argomento' in columns:
                print("   - Trovata vecchia struttura con argomento, eseguo migrazione...")
                
                # Crea tabella temporanea con nuova struttura
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appunti_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        titolo TEXT NOT NULL,
                        contenuto TEXT,
                        data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                        data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Copia i dati (ignorando argomento e altri campi vecchi)
                cursor.execute("""
                    INSERT INTO appunti_new (id, titolo, contenuto, data_creazione, data_modifica)
                    SELECT id, titolo, contenuto, data_creazione, data_modifica
                    FROM appunti
                """)
                
                # Elimina vecchia tabella
                cursor.execute("DROP TABLE appunti")
                
                # Rinomina nuova tabella
                cursor.execute("ALTER TABLE appunti_new RENAME TO appunti")
                
                print("   ✓ Migrazione completata!")
            else:
                # Tabella esiste già con struttura corretta
                print("   ✓ Tabella appunti già esistente con struttura corretta")
        else:
            # Crea nuova tabella
            print("   - Creo tabella appunti...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appunti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titolo TEXT NOT NULL,
                    contenuto TEXT,
                    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Tabella appunti creata con successo!")
        
        # Crea indici per migliorare le performance
        print("   - Creo indici...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appunti_data_creazione ON appunti(data_creazione)")
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"   ✗ Errore durante la creazione/migrazione della tabella appunti: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("Inizializzazione database Appunti...")
    init_appunti_tables()
    print("Completato!")
