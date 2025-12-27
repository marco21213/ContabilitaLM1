"""
Script per rimuovere il campo id_dichiarazione_intento dalla tabella documenti.
ATTENZIONE: Questa operazione elimina il campo e tutti i dati in esso contenuti.
"""
import sqlite3
import configparser
import os

def rimuovi_campo_dichiarazione_intento():
    """Rimuove il campo id_dichiarazione_intento dalla tabella documenti."""
    
    # Leggi il percorso del database da config.ini
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
    config.read(config_path, encoding="utf-8")
    
    db_path = config.get("Autenticazione", "percorso_database", fallback="database.db")
    
    if not os.path.exists(db_path):
        print(f"⚠️  Database non trovato: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la colonna esiste
        cursor.execute("PRAGMA table_info(documenti)")
        colonne = cursor.fetchall()
        colonne_nomi = [col[1] for col in colonne]
        
        if "id_dichiarazione_intento" not in colonne_nomi:
            print("✓ Campo id_dichiarazione_intento non presente nella tabella documenti")
            conn.close()
            return True
        
        print("⚠️  ATTENZIONE: Stai per rimuovere il campo id_dichiarazione_intento")
        print("   Questa operazione eliminerà tutti i dati in quel campo.")
        risposta = input("   Continuare? (s/n): ")
        
        if risposta.lower() != 's':
            print("Operazione annullata.")
            conn.close()
            return False
        
        # SQLite non supporta DROP COLUMN direttamente, dobbiamo ricreare la tabella
        print("Rimuovo campo id_dichiarazione_intento dalla tabella documenti...")
        
        # Leggi la struttura attuale
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='documenti'")
        create_sql = cursor.fetchone()[0]
        
        # Crea una tabella temporanea senza il campo
        cursor.execute("""
            CREATE TABLE documenti_new AS 
            SELECT 
                id,
                soggetto_id,
                tipo_documento,
                numero_documento,
                data_documento,
                data_registrazione,
                totale,
                importo_imponibile,
                segno
            FROM documenti
        """)
        
        # Elimina la vecchia tabella
        cursor.execute("DROP TABLE documenti")
        
        # Rinomina la nuova tabella
        cursor.execute("ALTER TABLE documenti_new RENAME TO documenti")
        
        conn.commit()
        conn.close()
        
        print("✓ Campo id_dichiarazione_intento rimosso con successo")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Errore SQLite: {e}")
        return False
    except Exception as e:
        print(f"✗ Errore: {e}")
        return False

if __name__ == "__main__":
    rimuovi_campo_dichiarazione_intento()

