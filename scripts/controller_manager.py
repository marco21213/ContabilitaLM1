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


class ControllerManager:

    def __init__(self):
        # Qui potrai aggiungere altri controlli
        self.controlli = [
            ("Quantità e Prezzo", check_quantita_prezzo)
        ]

    def esegui_controlli(self, xml_file):
        """Esegue tutti i controlli sul file XML."""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        risultati = []

        for nome_controllo, funzione in self.controlli:
            problemi = funzione(root)

            risultati.append({
                "nome_controllo": nome_controllo,
                "problemi": problemi
            })

        return risultati
