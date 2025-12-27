# check_spese_bancarie.py
import xml.etree.ElementTree as ET
import sqlite3
import os
import sys
import configparser
from pathlib import Path

# Calcola il percorso per accedere a parametri_db
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
scripts_path = os.path.join(project_root, "scripts")

# Aggiungi scripts al path se non presente
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# Prova a importare parametri_db
try:
    from parametri_db import get_db_path
except ImportError:
    # Fallback: implementa get_db_path direttamente
    def get_db_path(config_path: str = "config.ini") -> str:
        """Legge il percorso del database da config.ini"""
        config = configparser.ConfigParser()
        config_path_full = os.path.join(project_root, config_path)
        config.read(config_path_full, encoding="utf-8")
        
        if "Autenticazione" not in config or "percorso_database" not in config["Autenticazione"]:
            return str(Path(project_root) / "database.db")
        
        db_path = config.get("Autenticazione", "percorso_database", fallback="database.db")
        return db_path


def check_spese_bancarie(root):
    """
    Verifica se per i clienti/fornitori con spese_bancarie = "SI" nel database
    sono effettivamente presenti le spese bancarie nella fattura.
    
    Le spese bancarie nell'XML hanno:
    - TipoCessionePrestazione = "AC"
    - Descrizione = "Spese Bancarie" (case-insensitive)
    
    Args:
        root: Element root dell'XML della fattura
        
    Returns:
        Lista di problemi (dizionari con 'messaggio')
    """
    problemi = []
    
    try:
        # Determina se è fattura di acquisto o vendita
        # Per fatture di ACQUISTO: CedentePrestatore è il fornitore (noi siamo il cliente)
        # Per fatture di VENDITA: CessionarioCommittente è il cliente (noi siamo il venditore)
        
        # Prova prima CessionarioCommittente (fatture vendita - il cliente)
        partita_iva = root.findtext(".//CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice", "").strip()
        tipo_soggetto_atteso = "CLIENTE"
        
        # Se non trovato, prova CedentePrestatore (fatture acquisto - il fornitore)
        if not partita_iva:
            partita_iva = root.findtext(".//CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice", "").strip()
            tipo_soggetto_atteso = "FORNITORE"
        
        if not partita_iva:
            # Se non c'è partita IVA, non possiamo verificare nel database
            # Ma possiamo comunque verificare se ci sono spese bancarie nell'XML
            pass
        else:
            # Connetti al database
            db_path = get_db_path()
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Cerca il soggetto nel database e verifica spese_bancarie
                cursor.execute("""
                    SELECT spese_bancarie, ragione_sociale, tipo_soggetto
                    FROM soggetti
                    WHERE partita_iva = ?
                """, (partita_iva,))
                
                soggetto = cursor.fetchone()
                conn.close()
                
                if soggetto:
                    spese_bancarie_db = soggetto["spese_bancarie"]
                    ragione_sociale = soggetto["ragione_sociale"]
                    tipo_soggetto_db = soggetto["tipo_soggetto"]
                    
                    # Verifica se il tipo_soggetto corrisponde
                    if tipo_soggetto_db and tipo_soggetto_db.upper() != tipo_soggetto_atteso:
                        # Se il tipo non corrisponde, potrebbe essere "ENTRAMBI", quindi continuiamo
                        if tipo_soggetto_db.upper() != "ENTRAMBI":
                            # Tipo non corrispondente, non verifichiamo le spese bancarie
                            pass
                        else:
                            # È "ENTRAMBI", quindi verifichiamo
                            if spese_bancarie_db and spese_bancarie_db.upper().strip() == "SI":
                                # Il soggetto ha spese_bancarie = "SI", verifica se sono presenti nell'XML
                                if not verifica_spese_bancarie_in_xml(root):
                                    problemi.append({
                                        "messaggio": (
                                            f"Spese bancarie mancanti: "
                                            f"Il soggetto {ragione_sociale} (P.IVA: {partita_iva}) "
                                            f"ha spese_bancarie = 'SI' nel database, "
                                            f"ma non sono presenti nella fattura"
                                        )
                                    })
                    else:
                        # Tipo corrisponde, verifica spese_bancarie
                        if spese_bancarie_db and spese_bancarie_db.upper().strip() == "SI":
                            # Il soggetto ha spese_bancarie = "SI", verifica se sono presenti nell'XML
                            if not verifica_spese_bancarie_in_xml(root):
                                problemi.append({
                                    "messaggio": (
                                        f"Spese bancarie mancanti: "
                                        f"Il soggetto {ragione_sociale} (P.IVA: {partita_iva}) "
                                        f"ha spese_bancarie = 'SI' nel database, "
                                        f"ma non sono presenti nella fattura"
                                    )
                                })
        
        # Verifica anche se ci sono spese bancarie nell'XML (per informazione)
        # Questo può essere utile per vedere se ci sono spese bancarie non attese
        spese_trovate = verifica_spese_bancarie_in_xml(root)
        if spese_trovate:
            # Se ci sono spese bancarie, verifica se il soggetto le ha nel database
            if partita_iva:
                db_path = get_db_path()
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT spese_bancarie, ragione_sociale
                        FROM soggetti
                        WHERE partita_iva = ?
                    """, (partita_iva,))
                    
                    soggetto = cursor.fetchone()
                    conn.close()
                    
                    if soggetto:
                        spese_bancarie_db = soggetto["spese_bancarie"]
                        ragione_sociale = soggetto["ragione_sociale"]
                        
                        # Se nel database è "NO" o NULL, ma nell'XML ci sono, potrebbe essere un problema
                        if not spese_bancarie_db or spese_bancarie_db.upper().strip() != "SI":
                            # Non è un errore critico, ma potrebbe essere utile segnalarlo
                            pass  # Per ora non segnaliamo questo caso
    
    except sqlite3.Error as e:
        problemi.append({
            "messaggio": f"Errore database durante controllo spese bancarie: {str(e)}"
        })
    except Exception as e:
        problemi.append({
            "messaggio": f"Errore durante il controllo spese bancarie: {str(e)}"
        })
    
    return problemi


def verifica_spese_bancarie_in_xml(root):
    """
    Verifica se nell'XML sono presenti spese bancarie.
    
    Args:
        root: Element root dell'XML della fattura
        
    Returns:
        True se sono presenti, False altrimenti
    """
    try:
        # Trova tutte le linee
        linee = root.findall(".//DettaglioLinee")
        
        for linea in linee:
            # Estrai TipoCessionePrestazione e Descrizione
            tipo_cessione = linea.findtext("TipoCessionePrestazione", "").strip()
            descrizione = linea.findtext("Descrizione", "").strip()
            
            # Verifica se è una spesa bancaria
            # TipoCessionePrestazione deve essere "AC" e Descrizione deve contenere "Spese Bancarie"
            # Controllo case-insensitive per la descrizione
            if tipo_cessione == "AC" and "spese bancarie" in descrizione.lower():
                return True
        
        return False
    except Exception:
        return False

