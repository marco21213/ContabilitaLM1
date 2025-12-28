"""
Script per estrarre le righe delle fatture dagli XML e salvarle nel database.
"""
import os
import sys
from pathlib import Path
from lxml import etree
from typing import List, Dict, Optional
from datetime import datetime
import sqlite3

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)

from db_manager import get_connection


class RigheFatturaExtractor:
    """Classe per estrarre le righe delle fatture dagli XML."""
    
    def __init__(self):
        self.conn = get_connection()
    
    def extract_righe_from_xml(self, xml_path: str) -> List[Dict]:
        """
        Estrae le righe di dettaglio da un file XML fattura.
        
        Args:
            xml_path: Percorso del file XML
            
        Returns:
            Lista di dizionari con i dati delle righe
        """
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            
            # Namespace per FatturaPA
            ns = {'ns': 'http://www.fatturapa.gov.it/sdi/fatturapa/v1.2'}
            
            # Estrai dati documento
            numero_doc = root.findtext(".//ns:DatiGeneraliDocumento/ns:Numero", namespaces=ns, default="")
            data_doc = root.findtext(".//ns:DatiGeneraliDocumento/ns:Data", namespaces=ns, default="")
            
            # Converti data da yyyy-mm-dd a formato datetime
            try:
                if data_doc and len(data_doc) == 10:
                    data_doc_obj = datetime.strptime(data_doc, "%Y-%m-%d")
                else:
                    data_doc_obj = datetime.now()
            except:
                data_doc_obj = datetime.now()
            
            # Cerca il documento nel database per ottenere l'ID
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id FROM Documenti 
                WHERE numero_documento = ? AND data_documento = ?
            """, (numero_doc, data_doc_obj.date()))
            doc_result = cursor.fetchone()
            
            if not doc_result:
                print(f"Documento {numero_doc} del {data_doc} non trovato nel database. Saltato.")
                return []
            
            documento_id = doc_result[0]
            
            # Estrai tutte le righe DettaglioLinee
            righe = []
            dettaglio_linee = root.findall(".//ns:DettaglioLinee", namespaces=ns)
            
            for idx, dettaglio in enumerate(dettaglio_linee, start=1):
                descrizione = dettaglio.findtext("ns:Descrizione", namespaces=ns, default="")
                codice_articolo = dettaglio.findtext("ns:CodiceArticolo/ns:CodiceValore", namespaces=ns, default="")
                
                # Prezzo unitario
                prezzo_unitario_text = dettaglio.findtext("ns:PrezzoUnitario", namespaces=ns, default="0")
                try:
                    prezzo_unitario = float(prezzo_unitario_text.replace(",", "."))
                except:
                    prezzo_unitario = 0.0
                
                # Quantità
                quantita_text = dettaglio.findtext("ns:Quantita", namespaces=ns, default="1")
                try:
                    quantita = float(quantita_text.replace(",", "."))
                except:
                    quantita = 1.0
                
                # Unità di misura
                unita_misura = dettaglio.findtext("ns:UnitaMisura", namespaces=ns, default="")
                
                # Prezzo totale
                prezzo_totale_text = dettaglio.findtext("ns:PrezzoTotale", namespaces=ns, default="0")
                try:
                    prezzo_totale = float(prezzo_totale_text.replace(",", "."))
                except:
                    # Calcola se non presente
                    prezzo_totale = prezzo_unitario * quantita
                
                righe.append({
                    'documento_id': documento_id,
                    'numero_riga': idx,
                    'descrizione': descrizione.strip(),
                    'codice_articolo': codice_articolo.strip(),
                    'prezzo_unitario': prezzo_unitario,
                    'quantita': quantita,
                    'unita_misura': unita_misura.strip(),
                    'prezzo_totale': prezzo_totale
                })
            
            return righe
            
        except Exception as e:
            print(f"Errore nell'estrazione righe da {xml_path}: {e}")
            return []
    
    def save_righe_to_db(self, righe: List[Dict]) -> int:
        """
        Salva le righe nel database.
        
        Args:
            righe: Lista di dizionari con i dati delle righe
            
        Returns:
            Numero di righe salvate
        """
        if not righe:
            return 0
        
        cursor = self.conn.cursor()
        count = 0
        
        for riga in righe:
            try:
                # Verifica se la riga esiste già
                cursor.execute("""
                    SELECT id FROM righe_fattura 
                    WHERE documento_id = ? AND numero_riga = ?
                """, (riga['documento_id'], riga['numero_riga']))
                
                if cursor.fetchone():
                    # Aggiorna se esiste
                    cursor.execute("""
                        UPDATE righe_fattura 
                        SET descrizione = ?, codice_articolo = ?, prezzo_unitario = ?,
                            quantita = ?, unita_misura = ?, prezzo_totale = ?
                        WHERE documento_id = ? AND numero_riga = ?
                    """, (
                        riga['descrizione'],
                        riga['codice_articolo'],
                        riga['prezzo_unitario'],
                        riga['quantita'],
                        riga['unita_misura'],
                        riga['prezzo_totale'],
                        riga['documento_id'],
                        riga['numero_riga']
                    ))
                else:
                    # Inserisci se non esiste
                    cursor.execute("""
                        INSERT INTO righe_fattura 
                        (documento_id, numero_riga, descrizione, codice_articolo,
                         prezzo_unitario, quantita, unita_misura, prezzo_totale)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        riga['documento_id'],
                        riga['numero_riga'],
                        riga['descrizione'],
                        riga['codice_articolo'],
                        riga['prezzo_unitario'],
                        riga['quantita'],
                        riga['unita_misura'],
                        riga['prezzo_totale']
                    ))
                count += 1
            except Exception as e:
                print(f"Errore nel salvataggio riga: {e}")
                continue
        
        self.conn.commit()
        return count
    
    def process_xml_file(self, xml_path: str) -> int:
        """
        Processa un file XML completo: estrae e salva le righe.
        
        Args:
            xml_path: Percorso del file XML
            
        Returns:
            Numero di righe processate
        """
        righe = self.extract_righe_from_xml(xml_path)
        if righe:
            return self.save_righe_to_db(righe)
        return 0
    
    def process_folder(self, folder_path: str) -> Dict[str, int]:
        """
        Processa tutti i file XML in una cartella.
        
        Args:
            folder_path: Percorso della cartella
            
        Returns:
            Dizionario con statistiche
        """
        folder = Path(folder_path)
        if not folder.exists():
            print(f"Cartella non trovata: {folder_path}")
            return {'processed': 0, 'total_righe': 0, 'errors': 0}
        
        xml_files = list(folder.glob("*.xml"))
        stats = {'processed': 0, 'total_righe': 0, 'errors': 0}
        
        for xml_file in xml_files:
            try:
                count = self.process_xml_file(str(xml_file))
                stats['total_righe'] += count
                stats['processed'] += 1
                print(f"Processato {xml_file.name}: {count} righe")
            except Exception as e:
                stats['errors'] += 1
                print(f"Errore nel processare {xml_file.name}: {e}")
        
        return stats
    
    def close(self):
        """Chiude la connessione al database."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    import configparser
    
    # Ottieni cartella da processare dal database
    sys.path.append(str(Path(__file__).parent.parent))
    from scripts.parametri_db import get_cartella_ricevute
    
    cartella = get_cartella_ricevute()
    
    if not cartella or not Path(cartella).exists():
        print(f"Cartella non configurata o non trovata: {cartella}")
        sys.exit(1)
    
    extractor = RigheFatturaExtractor()
    try:
        stats = extractor.process_folder(cartella)
        print(f"\nRiepilogo:")
        print(f"  File processati: {stats['processed']}")
        print(f"  Righe totali: {stats['total_righe']}")
        print(f"  Errori: {stats['errors']}")
    finally:
        extractor.close()

