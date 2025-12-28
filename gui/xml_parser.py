import os
import glob
from lxml import etree
import configparser
from typing import List, Dict, Optional, Tuple
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.parametri_db import get_cartella_stampa

class XMLParser:
    def __init__(self):
        pass
    
    def get_xml_files(self) -> List[str]:
        """Restituisce la lista dei file XML nella cartella specificata."""
        try:
            folder_path = get_cartella_stampa()
            if not folder_path or not os.path.exists(folder_path):
                return []
            
            return glob.glob(os.path.join(folder_path, '*.xml'))
        except Exception:
            return []
    
    def extract_basic_data(self, file_path: str) -> Optional[Dict]:
        """Estrae i dati base dal file XML."""
        try:
            tree = etree.parse(file_path)
        
             # Estrai i dati richiesti
            data = tree.findtext(".//DatiGenerali/DatiGeneraliDocumento/Data", default="N/A")
            numero = tree.findtext(".//DatiGenerali/DatiGeneraliDocumento/Numero", default="N/A")
        
             # Prima prova a prendere la Denominazione
            soggetto = tree.findtext(".//CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione")
        
            if not soggetto or soggetto.strip() == "":
                # Se Denominazione non esiste, concatena Cognome + Nome
                cognome = tree.findtext(".//CedentePrestatore/DatiAnagrafici/Anagrafica/Cognome", default="")
                nome = tree.findtext(".//CedentePrestatore/DatiAnagrafici/Anagrafica/Nome", default="")
                soggetto = f"{cognome} {nome}".strip() if (cognome or nome) else "N/A"
        
        # Formatta la data in dd/mm/yyyy
            if data != "N/A" and len(data) == 10:  # formato yyyy-mm-dd
                try:
                    year, month, day = data.split('-')
                    data = f"{day}/{month}/{year}"
                except:
                    pass
        
            return {
                'data': data,
                'numero': numero,
                'soggetto': soggetto,
                'file_path': file_path
        }
        
        except Exception as e:
            print(f"Errore nel parsing del file {file_path}: {e}")
            return None

    
    def get_all_basic_data(self) -> List[Dict]:
        """Restituisce tutti i dati base dei file XML."""
        files = self.get_xml_files()
        data_list = []
        
        for file in files:
            data = self.extract_basic_data(file)
            if data:
                data_list.append(data)
        
        return data_list
    
    def get_full_xml_content(self, file_path: str) -> str:
        """Restituisce il contenuto completo del file XML."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Errore nella lettura del file {file_path}: {e}")
            return f"<error>Errore nel caricamento del file: {e}</error>"
    
    def apply_xsl_stylesheet(self, xml_content: str, xsl_path: str) -> str:
        """Applica un foglio di stile XSL al contenuto XML."""
        try:
            xml_tree = etree.fromstring(xml_content.encode('utf-8'))
            xsl_tree = etree.parse(xsl_path)
            transform = etree.XSLT(xsl_tree)
            return str(transform(xml_tree))
        except Exception as e:
            print(f"Errore nell'applicazione dello stile XSL: {e}")
            return xml_content