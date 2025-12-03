"""
Script per inizializzare le tabelle del database necessarie per il sistema IA di controllo prezzi.
"""
import os
import sys
from pathlib import Path

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from db_manager import get_connection


def init_ai_tables():
    """Crea tutte le tabelle necessarie per il sistema IA."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Tabella: righe_fattura
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS righe_fattura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_id INTEGER NOT NULL,
                numero_riga INTEGER NOT NULL,
                descrizione TEXT NOT NULL,
                codice_articolo TEXT,
                prezzo_unitario REAL NOT NULL,
                quantita REAL DEFAULT 1.0,
                unita_misura TEXT,
                prezzo_totale REAL NOT NULL,
                FOREIGN KEY (documento_id) REFERENCES Documenti(id),
                UNIQUE(documento_id, numero_riga)
            )
        """)
        
        # Tabella: listini
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listini (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                fornitore_id INTEGER,
                data_validita_inizio DATE,
                data_validita_fine DATE,
                attivo BOOLEAN DEFAULT 1,
                FOREIGN KEY (fornitore_id) REFERENCES Soggetti(id)
            )
        """)
        
        # Tabella: righe_listino
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS righe_listino (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listino_id INTEGER NOT NULL,
                codice_articolo TEXT,
                descrizione TEXT NOT NULL,
                prezzo REAL NOT NULL,
                unita_misura TEXT,
                note TEXT,
                FOREIGN KEY (listino_id) REFERENCES listini(id)
            )
        """)
        
        # Tabella: associazioni_verificate (Sistema di apprendimento)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associazioni_verificate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione_fattura TEXT NOT NULL,
                codice_articolo_listino TEXT,
                descrizione_listino TEXT NOT NULL,
                listino_id INTEGER,
                verifica_utente BOOLEAN NOT NULL,
                data_verifica DATE DEFAULT CURRENT_DATE,
                confidence_originale REAL,
                FOREIGN KEY (listino_id) REFERENCES listini(id),
                UNIQUE(descrizione_fattura, descrizione_listino, listino_id)
            )
        """)
        
        # Tabella: controlli_prezzi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS controlli_prezzi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                riga_fattura_id INTEGER NOT NULL,
                riga_listino_id INTEGER,
                prezzo_fattura REAL NOT NULL,
                prezzo_listino REAL,
                differenza REAL,
                percentuale_diff REAL,
                match_confidenza REAL,
                stato TEXT DEFAULT 'DA_VERIFICARE',
                data_controllo DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (riga_fattura_id) REFERENCES righe_fattura(id),
                FOREIGN KEY (riga_listino_id) REFERENCES righe_listino(id)
            )
        """)
        
        # Crea indici per migliorare le performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_righe_fattura_documento 
            ON righe_fattura(documento_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_righe_listino_listino 
            ON righe_listino(listino_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_associazioni_descrizione 
            ON associazioni_verificate(descrizione_fattura, listino_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_controlli_riga_fattura 
            ON controlli_prezzi(riga_fattura_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listini_fornitore 
            ON listini(fornitore_id)
        """)
        
        conn.commit()
        print("✅ Tabelle create con successo!")
        print("   - righe_fattura")
        print("   - listini")
        print("   - righe_listino")
        print("   - associazioni_verificate")
        print("   - controlli_prezzi")
        print("   - Indicii creati")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Errore nella creazione delle tabelle: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("Inizializzazione database per sistema IA controllo prezzi...")
    init_ai_tables()
    print("✅ Completato!")

