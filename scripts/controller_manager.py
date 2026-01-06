# controller_manager.py

import xml.etree.ElementTree as ET
import os
import sys

# Calcola il path assoluto della cartella scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
scripts_path = os.path.join(project_root, "scripts")

# Aggiunge /scripts al path (fondamentale!)
if scripts_path not in sys.path:
    sys.path.append(scripts_path)

from check_quantita_prezzo import check_quantita_prezzo
from check_tipo_documento import check_tipo_documento
from check_spese_bancarie import check_spese_bancarie
from check_dichiarazione_intento import check_dichiarazione_intento


class ControllerManager:

    def __init__(self):
        # Qui potrai aggiungere altri controlli
        self.controlli = [
            ("Quantità e Prezzo", check_quantita_prezzo),
            ("Tipo Documento", check_tipo_documento),
            ("Spese Bancarie", check_spese_bancarie),
            ("Dichiarazione d'Intento", check_dichiarazione_intento)
        ]

    def esegui_controlli(self, xml_file, controlli_selezionati=None):
        """
        Esegue i controlli sul file XML.
        
        Args:
            xml_file: Percorso del file XML da controllare
            controlli_selezionati: Lista di nomi dei controlli da eseguire. 
                                  Se None, esegue tutti i controlli.
        """
        tree = ET.parse(xml_file)
        root = tree.getroot()

        risultati = []

        for nome_controllo, funzione in self.controlli:
            # Se sono specificati controlli da eseguire, salta quelli non selezionati
            if controlli_selezionati is not None and nome_controllo not in controlli_selezionati:
                continue
                
            problemi = funzione(root)

            risultati.append({
                "nome_controllo": nome_controllo,
                "problemi": problemi
            })

        return risultati
    
    def get_lista_controlli(self):
        """Restituisce la lista dei nomi dei controlli disponibili."""
        return [nome for nome, _ in self.controlli]
