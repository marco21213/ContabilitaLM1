"""
Script per inizializzare le tabelle del database necessarie per il modulo Laboratorio.
Gestisce ricette di vernici, categorie, ingredienti e appunti.
"""
import os
import sys
from pathlib import Path

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from db_manager import get_connection


def init_laboratorio_tables():
    """Crea tutte le tabelle necessarie per il modulo Laboratorio."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Tabella: categorie_laboratorio
        print("   - Creo tabella categorie_laboratorio...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorie_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione TEXT NOT NULL,
                codifica TEXT,
                informazioni TEXT
            )
        """)
        
        # Tabella: riferimenti_laboratorio
        print("   - Creo tabella riferimenti_laboratorio...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS riferimenti_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione TEXT NOT NULL
            )
        """)
        
        # Tabella: righe_colori_laboratorio
        print("   - Creo tabella righe_colori_laboratorio...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS righe_colori_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione TEXT NOT NULL,
                quantita REAL NOT NULL,
                colore INTEGER NOT NULL,
                FOREIGN KEY (colore) REFERENCES colori_laboratorio(id) ON DELETE CASCADE
            )
        """)
        
        # Tabella: colori_laboratorio (ricette)
        print("   - Creo tabella colori_laboratorio...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS colori_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                codice TEXT NOT NULL,
                nome TEXT NOT NULL,
                riferimento INTEGER,
                categoria INTEGER,
                note TEXT,
                FOREIGN KEY (riferimento) REFERENCES riferimenti_laboratorio(id),
                FOREIGN KEY (categoria) REFERENCES categorie_laboratorio(id)
            )
        """)
        
        # Tabella: ingredienti
        print("   - Creo tabella ingredienti...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codice TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                descrizione TEXT,
                fornitore TEXT,
                unita_misura TEXT DEFAULT 'kg',
                prezzo_unitario REAL,
                note TEXT,
                attivo BOOLEAN DEFAULT 1,
                data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabella: ricette
        print("   - Creo tabella ricette...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ricette (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codice TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                categoria_id INTEGER,
                descrizione TEXT,
                procedura TEXT,
                note TEXT,
                versione TEXT DEFAULT '1.0',
                data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_ultima_produzione DATE,
                attivo BOOLEAN DEFAULT 1,
                FOREIGN KEY (categoria_id) REFERENCES categorie_laboratorio(id)
            )
        """)
        
        # Tabella: ricette_ingredienti (composizione ricette)
        print("   - Creo tabella ricette_ingredienti...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ricette_ingredienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ricetta_id INTEGER NOT NULL,
                ingrediente_id INTEGER NOT NULL,
                quantita REAL NOT NULL,
                percentuale REAL,
                ordine INTEGER DEFAULT 0,
                note TEXT,
                FOREIGN KEY (ricetta_id) REFERENCES ricette(id) ON DELETE CASCADE,
                FOREIGN KEY (ingrediente_id) REFERENCES ingredienti(id),
                UNIQUE(ricetta_id, ingrediente_id, ordine)
            )
        """)
        
        # Tabella: appunti_laboratorio
        print("   - Creo tabella appunti_laboratorio...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appunti_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titolo TEXT NOT NULL,
                contenuto TEXT,
                categoria TEXT,
                ricetta_id INTEGER,
                data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP,
                importante BOOLEAN DEFAULT 0,
                FOREIGN KEY (ricetta_id) REFERENCES ricette(id) ON DELETE SET NULL
            )
        """)
        
        # Crea indici per migliorare le performance
        print("   - Creo indici...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categorie_laboratorio_codifica ON categorie_laboratorio(codifica)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_categoria ON colori_laboratorio(categoria)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_riferimento ON colori_laboratorio(riferimento)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_data ON colori_laboratorio(data)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_righe_colori_laboratorio_colore ON righe_colori_laboratorio(colore)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ricette_categoria ON ricette(categoria_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ricette_codice ON ricette(codice)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ricette_ingredienti_ricetta ON ricette_ingredienti(ricetta_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ricette_ingredienti_ingrediente ON ricette_ingredienti(ingrediente_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appunti_ricetta ON appunti_laboratorio(ricetta_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appunti_categoria ON appunti_laboratorio(categoria)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredienti_codice ON ingredienti(codice)")
        
        conn.commit()
        print("   ✓ Tabelle laboratorio create con successo!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"   ✗ Errore durante la creazione delle tabelle: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("Inizializzazione database Laboratorio...")
    init_laboratorio_tables()
    print("Completato!")
