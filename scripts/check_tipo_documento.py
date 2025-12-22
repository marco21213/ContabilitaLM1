# check_tipo_documento.py
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


def check_tipo_documento(root):
    """
    Controlla se il TipoDocumento nell'XML corrisponde al tipo_fattura
    salvato nel database per il soggetto (fornitore o cliente).
    
    Args:
        root: Element root dell'XML della fattura
        
    Returns:
        Lista di problemi (dizionari con 'messaggio')
    """
    problemi = []
    
    try:
        # Estrai TipoDocumento dall'XML
        tipo_documento_xml = root.findtext(".//DatiGenerali/DatiGeneraliDocumento/TipoDocumento", "").strip()
        
        if not tipo_documento_xml:
            problemi.append({
                "messaggio": "TipoDocumento non trovato nell'XML"
            })
            return problemi
        
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
            problemi.append({
                "messaggio": "Partita IVA non trovata nell'XML (né CessionarioCommittente né CedentePrestatore)"
            })
            return problemi
        
        # Connetti al database
        db_path = get_db_path()
        if not os.path.exists(db_path):
            problemi.append({
                "messaggio": f"Database non trovato: {db_path}"
            })
            return problemi
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Cerca il soggetto nel database
        cursor.execute("""
            SELECT tipo_fattura, ragione_sociale, tipo_soggetto
            FROM soggetti
            WHERE partita_iva = ?
        """, (partita_iva,))
        
        soggetto = cursor.fetchone()
        conn.close()
        
        if not soggetto:
            problemi.append({
                "messaggio": f"Soggetto con P.IVA {partita_iva} non trovato nel database"
            })
            return problemi
        
        tipo_fattura_db = soggetto["tipo_fattura"]
        ragione_sociale = soggetto["ragione_sociale"]
        tipo_soggetto_db = soggetto["tipo_soggetto"]
        
        # Verifica che il tipo_soggetto corrisponda
        if tipo_soggetto_db and tipo_soggetto_db.upper() != tipo_soggetto_atteso:
            problemi.append({
                "messaggio": (
                    f"Tipo soggetto non corrisponde: "
                    f"atteso {tipo_soggetto_atteso}, trovato {tipo_soggetto_db} "
                    f"(P.IVA: {partita_iva}, Soggetto: {ragione_sociale})"
                )
            })
        
        # Confronta TipoDocumento XML con tipo_fattura nel database
        if tipo_fattura_db:
            # Normalizza i valori per il confronto (rimuovi spazi, converti in maiuscolo)
            tipo_doc_xml_norm = tipo_documento_xml.upper().strip()
            tipo_fattura_db_norm = tipo_fattura_db.upper().strip()
            
            # Gestisci TD24 con testo dopo (es. "TD24 - Fattura differita")
            if tipo_doc_xml_norm.startswith('TD24'):
                tipo_doc_xml_norm = 'TD24'
            elif tipo_doc_xml_norm == 'TD01':
                tipo_doc_xml_norm = 'TD01'
            
            if tipo_fattura_db_norm.startswith('TD24'):
                tipo_fattura_db_norm = 'TD24'
            elif tipo_fattura_db_norm == 'TD01':
                tipo_fattura_db_norm = 'TD01'
            
            if tipo_doc_xml_norm != tipo_fattura_db_norm:
                problemi.append({
                    "messaggio": (
                        f"TipoDocumento non corrisponde: "
                        f"XML={tipo_documento_xml}, Database={tipo_fattura_db} "
                        f"(P.IVA: {partita_iva}, Soggetto: {ragione_sociale})"
                    )
                })
        else:
            # Se tipo_fattura è NULL nel database, segnala come problema
            problemi.append({
                "messaggio": (
                    f"tipo_fattura non impostato nel database per il soggetto "
                    f"(P.IVA: {partita_iva}, Soggetto: {ragione_sociale}, "
                    f"TipoDocumento XML: {tipo_documento_xml})"
                )
            })
    
    except sqlite3.Error as e:
        problemi.append({
            "messaggio": f"Errore database: {str(e)}"
        })
    except Exception as e:
        problemi.append({
            "messaggio": f"Errore durante il controllo: {str(e)}"
        })
    
    return problemi

