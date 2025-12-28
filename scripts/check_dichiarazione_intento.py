# check_dichiarazione_intento.py
import xml.etree.ElementTree as ET
import sqlite3
import os
import sys
import configparser
from pathlib import Path
from datetime import datetime

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


def check_dichiarazione_intento(root):
    """
    Verifica se per i clienti con dichiarazione d'intento valida:
    1. Tutte le righe della fattura hanno IVA a 0 e codice N3.5
    2. L'imponibile con aliquota N3.5 non supera il plafond residuo
    
    Args:
        root: Element root dell'XML della fattura
        
    Returns:
        Lista di problemi (dizionari con 'messaggio')
    """
    problemi = []
    
    try:
        # Estrai partita IVA del cliente (CessionarioCommittente per fatture vendita)
        partita_iva = root.findtext(".//CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice", "").strip()
        
        if not partita_iva:
            # Se non c'è partita IVA del cliente, non possiamo verificare
            return problemi
        
        # Estrai data fattura per determinare l'anno
        data_fattura_str = root.findtext(".//DatiGenerali/DatiGeneraliDocumento/Data", "").strip()
        if not data_fattura_str:
            return problemi
        
        # Converti data in oggetto datetime per estrarre l'anno
        try:
            # Prova formato yyyy-mm-dd
            data_fattura = datetime.strptime(data_fattura_str, "%Y-%m-%d")
            anno_fattura = data_fattura.year
        except ValueError:
            # Prova formato dd/mm/yyyy
            try:
                data_fattura = datetime.strptime(data_fattura_str, "%d/%m/%Y")
                anno_fattura = data_fattura.year
            except ValueError:
                # Formato data non riconosciuto
                return problemi
        
        # Connetti al database
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return problemi
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Cerca il soggetto nel database
        cursor.execute("""
            SELECT id, ragione_sociale
            FROM soggetti
            WHERE partita_iva = ?
        """, (partita_iva,))
        
        soggetto = cursor.fetchone()
        if not soggetto:
            conn.close()
            return problemi
        
        soggetto_id = soggetto["id"]
        ragione_sociale = soggetto["ragione_sociale"]
        
        # Verifica se il cliente ha una dichiarazione d'intento valida per la data della fattura
        # con plafond_residuo > 0 (usando la vista vw_dichiarazioni_intento)
        # Le date nel database sono in formato yyyy-mm-dd
        data_fattura_db = data_fattura.strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id, numero_dichiarazione, plafond_residuo, data_inizio, data_fine
            FROM vw_dichiarazioni_intento
            WHERE id_soggetto = ? 
              AND plafond_residuo > 0
              AND data_inizio <= ?
              AND data_fine >= ?
            ORDER BY data_inizio DESC
            LIMIT 1
        """, (soggetto_id, data_fattura_db, data_fattura_db))
        
        dichiarazione = cursor.fetchone()
        conn.close()
        
        if not dichiarazione:
            # Il cliente non ha una dichiarazione d'intento valida, non è un problema
            return problemi
        
        # Il cliente ha una dichiarazione d'intento valida
        numero_dichiarazione = dichiarazione["numero_dichiarazione"]
        plafond_residuo = float(dichiarazione["plafond_residuo"])
        
        # Verifica tutte le righe in DatiRiepilogo
        riepiloghi = root.findall('.//DatiRiepilogo')
        
        if not riepiloghi:
            problemi.append({
                "messaggio": (
                    f"Dichiarazione d'intento attiva (n. {numero_dichiarazione}) per {ragione_sociale}, "
                    f"ma nessun DatiRiepilogo trovato nella fattura"
                )
            })
            return problemi
        
        imponibile_n35_totale = 0.0
        righe_non_conformi = []
        
        for idx, riepilogo in enumerate(riepiloghi, start=1):
            aliquota_iva_text = riepilogo.findtext('AliquotaIVA', '').strip()
            natura = riepilogo.findtext('Natura', '').strip()
            imponibile_text = riepilogo.findtext('ImponibileImporto', '').strip()
            
            try:
                aliquota_iva = float(aliquota_iva_text) if aliquota_iva_text else None
                imponibile = float(imponibile_text.replace(',', '.')) if imponibile_text else 0.0
            except (ValueError, TypeError):
                continue
            
            # Verifica se la riga è conforme (IVA = 0 e Natura = N3.5)
            if aliquota_iva != 0.00 or natura.upper() != 'N3.5':
                righe_non_conformi.append({
                    'riga': idx,
                    'aliquota': aliquota_iva,
                    'natura': natura
                })
            
            # Se è N3.5, aggiungi all'imponibile totale
            if aliquota_iva == 0.00 and natura.upper() == 'N3.5':
                imponibile_n35_totale += imponibile
        
        # Verifica 1: Tutte le righe devono avere IVA = 0 e Natura = N3.5
        if righe_non_conformi:
            messaggio_righe = []
            for riga_info in righe_non_conformi:
                messaggio_righe.append(
                    f"Riga {riga_info['riga']}: AliquotaIVA={riga_info['aliquota']}, Natura={riga_info['natura']}"
                )
            
            problemi.append({
                "messaggio": (
                    f"Dichiarazione d'intento attiva (n. {numero_dichiarazione}) per {ragione_sociale}, "
                    f"ma righe non conformi:\n" + "\n".join(messaggio_righe)
                )
            })
        
        # Verifica 2: L'imponibile N3.5 non deve superare il plafond residuo
        if imponibile_n35_totale > plafond_residuo:
            problemi.append({
                "messaggio": (
                    f"Dichiarazione d'intento attiva (n. {numero_dichiarazione}) per {ragione_sociale}: "
                    f"imponibile fattura (€ {imponibile_n35_totale:,.2f}) supera il plafond residuo "
                    f"(€ {plafond_residuo:,.2f})"
                )
            })
    
    except sqlite3.Error as e:
        problemi.append({
            "messaggio": f"Errore database durante controllo dichiarazione d'intento: {str(e)}"
        })
    except Exception as e:
        problemi.append({
            "messaggio": f"Errore durante il controllo dichiarazione d'intento: {str(e)}"
        })
    
    return problemi

