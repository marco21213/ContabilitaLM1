import os
import shutil
import configparser
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
import argparse

class XMLRenamer:
    def __init__(self):
        self.log_file_path = "rinomina_log.txt"
        
    def log_message(self, message):
        """Scrive un messaggio nel file di log."""
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] {message}\n")
    
    def create_year_month_dirs(self, base_dir, year, month):
        """Crea la struttura di cartelle Anno/Mese."""
        year_dir = os.path.join(base_dir, year)
        month_dir = os.path.join(year_dir, month)
        os.makedirs(month_dir, exist_ok=True)
        return month_dir
            
    def extract_fattura_data(self, xml_path):
        """Estrae i dati necessari dal file XML della fattura.
        
        Returns:
            Tupla (anno_mese, id_codice, numero, soggetto, data_formattata) se tutti i dati sono presenti,
            oppure None se mancano dati essenziali.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Gestione namespace se presente
            ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
            ns_path = 'ns:' if ns else ''
            
            # Cerca i nodi con e senza namespace
            paths = {
                'data': [
                    f'.//{ns_path}DatiGenerali/{ns_path}DatiGeneraliDocumento/{ns_path}Data',
                    './/DatiGenerali/DatiGeneraliDocumento/Data'
                ],
                'id_codice': [
                    f'.//{ns_path}CedentePrestatore/{ns_path}DatiAnagrafici/{ns_path}IdFiscaleIVA/{ns_path}IdCodice',
                    './/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice'
                ],
                'numero': [
                    f'.//{ns_path}DatiGenerali/{ns_path}DatiGeneraliDocumento/{ns_path}Numero',
                    './/DatiGenerali/DatiGeneraliDocumento/Numero'
                ],
                'denominazione': [
                    f'.//{ns_path}CedentePrestatore/{ns_path}DatiAnagrafici/{ns_path}Anagrafica/{ns_path}Denominazione',
                    './/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione'
                ],
                'cognome': [
                    f'.//{ns_path}CedentePrestatore/{ns_path}DatiAnagrafici/{ns_path}Anagrafica/{ns_path}Cognome',
                    './/CedentePrestatore/DatiAnagrafici/Anagrafica/Cognome'
                ],
                'nome': [
                    f'.//{ns_path}CedentePrestatore/{ns_path}DatiAnagrafici/{ns_path}Anagrafica/{ns_path}Nome',
                    './/CedentePrestatore/DatiAnagrafici/Anagrafica/Nome'
                ]
            }
            
            data = None
            id_codice = None
            numero = None
            denominazione = None
            cognome = None
            nome = None
            
            # Prova tutti i possibili percorsi per ogni elemento
            for path in paths['data']:
                node = root.find(path, ns)
                if node is not None:
                    data = node.text
                    break
                    
            for path in paths['id_codice']:
                node = root.find(path, ns)
                if node is not None:
                    id_codice = node.text
                    break
                    
            for path in paths['numero']:
                node = root.find(path, ns)
                if node is not None:
                    numero = node.text
                    break
            
            # Estrai il soggetto (Denominazione o Cognome+Nome)
            for path in paths['denominazione']:
                node = root.find(path, ns)
                if node is not None and node.text:
                    denominazione = node.text.strip()
                    break
            
            if not denominazione:
                # Prova con Cognome e Nome
                for path in paths['cognome']:
                    node = root.find(path, ns)
                    if node is not None:
                        cognome = node.text.strip() if node.text else ""
                        break
                
                for path in paths['nome']:
                    node = root.find(path, ns)
                    if node is not None:
                        nome = node.text.strip() if node.text else ""
                        break
                
                if cognome or nome:
                    denominazione = f"{cognome} {nome}".strip()
            
            if all([data, id_codice, numero]):
                # Pulisci il numero da caratteri non validi
                numero_pulito = numero.replace('/', '').replace('\\', '').replace(' ', '')
                # Estrai anno e mese dalla data
                anno_mese = data[:7]  # yyyy-mm
                
                # Formatta la data in dd/mm/yyyy
                data_formattata = data
                if len(data) == 10:  # formato yyyy-mm-dd
                    try:
                        year, month, day = data.split('-')
                        data_formattata = f"{day}/{month}/{year}"
                    except:
                        pass
                
                # Soggetto: usa denominazione se disponibile, altrimenti "N/A"
                soggetto = denominazione if denominazione else "N/A"
                
                return anno_mese, id_codice, numero_pulito, soggetto, data_formattata
                
            missing = []
            if not data: missing.append("Data")
            if not id_codice: missing.append("IdCodice")
            if not numero: missing.append("Numero")
            self.log_message(f"Dati mancanti in {xml_path}: {', '.join(missing)}")
            return None
            
        except ET.ParseError as e:
            self.log_message(f"Errore nel parsing XML del file {xml_path}: {str(e)}")
            return None
        except Exception as e:
            self.log_message(f"Errore nell'estrazione dei dati dal file {xml_path}: {str(e)}")
            return None

    def process_xml_files(self, source_dir, archive_dir, print_dir, copy_to_stampa=True):
        """Processa i file XML: rinomina e archivia.
        
        Args:
            source_dir: Directory sorgente dei file XML
            archive_dir: Directory di destinazione per l'archiviazione
            print_dir: Directory per la stampa (opzionale)
            copy_to_stampa: Se True, copia i file nella cartella stampa (default: True)
        
        Returns:
            Tupla (processed_count, error_count, fatture_processate) dove:
            - processed_count: numero di file processati con successo
            - error_count: numero di file con errori
            - fatture_processate: lista di dizionari con i dati delle fatture processate
                                  (numero, soggetto, data)
        """
        if not os.path.isdir(source_dir):
            self.log_message(f"La directory {source_dir} non esiste")
            print(f"La directory {source_dir} non esiste")
            return 0, 0, []
            
        processed_count = 0
        error_count = 0
        fatture_processate = []
        
        for filename in os.listdir(source_dir):
            if filename.endswith('.xml'):
                file_path = os.path.join(source_dir, filename)
                print(f"\nProcesso il file: {filename}")
                
                # Estrai i dati dalla fattura
                result = self.extract_fattura_data(file_path)
                
                if result:
                    anno_mese, id_codice, numero, soggetto, data_formattata = result
                    nuovo_nome = f"{anno_mese}-{id_codice}-{numero}.xml"
                    
                    # Estrai anno e mese dal nuovo nome
                    year, month = anno_mese.split('-')
                    
                    # Crea le cartelle di destinazione
                    archive_month_dir = self.create_year_month_dirs(archive_dir, year, month)
                    archive_path = os.path.join(archive_month_dir, nuovo_nome)
                    
                    try:
                        # Verifica se il file esiste già nell'archivio
                        if os.path.exists(archive_path):
                            self.log_message(f"File {nuovo_nome} già presente in archivio - rimuovo il file sorgente")
                            os.remove(file_path)  # Rimuove il file sorgente anche se è un duplicato
                            print(f"✗ File già esistente in archivio: {nuovo_nome} - rimosso file sorgente")
                            error_count += 1
                            continue
                        
                        # Sposta il file nell'archivio
                        shutil.move(file_path, archive_path)
                        self.log_message(f"File {filename} archiviato come {nuovo_nome}")
                        processed_count += 1
                        print(f"✓ Archiviato: {filename} -> {nuovo_nome}")
                        
                        # Aggiungi i dati della fattura alla lista
                        fatture_processate.append({
                            'numero': numero,
                            'soggetto': soggetto,
                            'data': data_formattata
                        })
                        
                        # Copia nella cartella stampa solo se richiesto
                        if copy_to_stampa and print_dir:
                            print_path = os.path.join(print_dir, nuovo_nome)
                            shutil.copy2(archive_path, print_path)
                            self.log_message(f"File {nuovo_nome} copiato in cartella stampa")
                            print(f"✓ Copiato in stampa: {nuovo_nome}")
                            
                    except Exception as e:
                        self.log_message(f"Errore nell'archiviazione del file {filename}: {str(e)}")
                        error_count += 1
                        print(f"✗ Errore nell'archiviazione: {filename}")
                else:
                    error_count += 1
                    print(f"✗ Impossibile estrarre i dati: {filename}")
                    
        return processed_count, error_count, fatture_processate

def main():
    try:
        # Parser per gli argomenti da riga di comando
        parser = argparse.ArgumentParser(description='Rinomina e archivia file XML fatture')
        parser.add_argument('--no-stampa', action='store_true', 
                          help='Non copiare i file nella cartella stampa (solo per download periodo/mensile)')
        args = parser.parse_args()
        
        # Determina se copiare in Stampa (default: True, False solo se --no-stampa è passato)
        copy_to_stampa = not args.no_stampa
        
        # Leggi il file di configurazione
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Recupera i percorsi dal config
        cartella_emesse = config['Parametri']['cartellaemesse']
        cartella_ricevute = config['Parametri']['cartellaricevute']
        cartella_stampa = config['Parametri']['cartellastampa']
        
        print("\nArchivazione file XML Fatture")
        if copy_to_stampa:
            print("Modalità: Download Rapido (copia in Stampa abilitata)")
        else:
            print("Modalità: Download Periodo/Mensile (copia in Stampa disabilitata)")
        print("-" * 50)
        
        renamer = XMLRenamer()
        
        # Assicurati che le cartelle esistano
        os.makedirs(cartella_stampa, exist_ok=True)
        
        # Pulisci la cartella stampa solo se dobbiamo copiare i file
        if copy_to_stampa:
            for file in os.listdir(cartella_stampa):
                file_path = os.path.join(cartella_stampa, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Rimosso file esistente da cartella stampa: {file}")
        
        # Processa le cartelle
        source_dirs = {
            'Emesse': {'source': cartella_emesse, 'archive': cartella_emesse},
            'Ricevute': {'source': cartella_ricevute, 'archive': cartella_ricevute}
        }
        
        # Raccogli tutte le fatture processate per lo storico
        tutte_fatture_processate = []
        
        for name, dirs in source_dirs.items():
            if os.path.exists(dirs['source']):
                print(f"\nProcesso {name}:")
                print("-" * 50)
                processed, errors, fatture = renamer.process_xml_files(
                    dirs['source'], 
                    dirs['archive'],
                    cartella_stampa if copy_to_stampa else None,  # Passa None se non dobbiamo copiare
                    copy_to_stampa=copy_to_stampa
                )
                print(f"\nRiepilogo {name}:")
                print(f"File archiviati con successo: {processed}")
                print(f"File con errori: {errors}")
                
                # Aggiungi le fatture processate alla lista totale
                tutte_fatture_processate.extend(fatture)
            else:
                print(f"\nLa cartella {dirs['source']} non esiste.")
        
        # Salva le fatture processate in un file JSON temporaneo per lo storico
        # (solo se ci sono fatture processate e se è un download rapido)
        if tutte_fatture_processate and copy_to_stampa:
            try:
                import json
                temp_history_file = "temp_download_fatture.json"
                with open(temp_history_file, 'w', encoding='utf-8') as f:
                    json.dump(tutte_fatture_processate, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Avviso: impossibile salvare lo storico delle fatture: {e}")

        print("\nOperazione completata!")

    except configparser.Error as e:
        print(f"Errore nella lettura del file di configurazione: {str(e)}")
    except Exception as e:
        print(f"Errore imprevisto: {str(e)}")

if __name__ == "__main__":
    main()