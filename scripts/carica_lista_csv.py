"""
Script per caricare una lista di fatture da un file CSV e creare un file JSON
nella cartella corretta (anno/mese) delle fatture acquisti.
"""
import csv
import json
import os
import sys
import re
import configparser
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def get_config_path():
    """Ottiene il percorso del file config.ini"""
    # Se eseguito come script, cerca config.ini nella directory padre
    if __name__ == "__main__":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, "config.ini")
    else:
        # Se importato, usa il percorso relativo
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config.ini")
    return config_path


def get_cartella_ricevute() -> Optional[str]:
    """Legge il percorso della cartella ricevute da config.ini"""
    try:
        config = configparser.ConfigParser()
        config_path = get_config_path()
        config.read(config_path, encoding="utf-8")
        
        cartella = config.get("Parametri", "cartellaricevute", fallback="")
        
        if not cartella:
            print(f"❌ Errore: Parametro 'cartellaricevute' non trovato nel file config.ini")
            return None
        
        if not os.path.exists(cartella):
            print(f"❌ Errore: Cartella fatture ricevute non trovata: {cartella}")
            return None
        
        return cartella
    except Exception as e:
        print(f"❌ Errore nella lettura di config.ini: {e}")
        return None


def verifica_formato_csv(file_path: str) -> bool:
    """
    Verifica che il file sia un CSV valido.
    
    Args:
        file_path: Percorso del file da verificare
        
    Returns:
        True se il file è un CSV valido, False altrimenti
    """
    if not os.path.exists(file_path):
        print(f"❌ Errore: Il file non esiste: {file_path}")
        return False
    
    # Verifica estensione
    if not file_path.lower().endswith('.csv'):
        print(f"❌ Errore: Il file deve essere un CSV (.csv)")
        return False
    
    # Prova a leggere il file come CSV
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Prova a leggere almeno una riga per verificare che sia un CSV valido
            # Usa il punto e virgola come delimitatore
            reader = csv.reader(f, delimiter=';')
            first_row = next(reader, None)
            if first_row is None:
                print(f"❌ Errore: Il file CSV è vuoto")
                return False
    except UnicodeDecodeError:
        # Prova con encoding diverso
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter=';')
                first_row = next(reader, None)
                if first_row is None:
                    print(f"❌ Errore: Il file CSV è vuoto")
                    return False
        except Exception as e:
            print(f"❌ Errore nella lettura del file CSV: {e}")
            return False
    except Exception as e:
        print(f"❌ Errore nella lettura del file CSV: {e}")
        return False
    
    return True


def rimuovi_apici(valore: str) -> str:
    """
    Rimuove gli apici singoli (') dall'inizio e dalla fine del valore.
    
    Args:
        valore: Stringa da pulire
        
    Returns:
        Stringa senza apici
    """
    if not valore:
        return ""
    valore = valore.strip()
    # Rimuovi apici singoli all'inizio e alla fine
    if valore.startswith("'") and valore.endswith("'"):
        valore = valore[1:-1]
    return valore.strip()


def pulisci_numero_fattura(numero: str) -> str:
    """
    Rimuove i caratteri '/' e '\' dal numero di fattura.
    Rimuove anche TUTTI gli spazi dal numero di fattura.
    NON aggiunge spazi, rimuove completamente i caratteri.
    
    Args:
        numero: Numero di fattura da pulire
        
    Returns:
        Numero di fattura senza '/', '\' e spazi
    """
    if not numero:
        return ""
    # Rimuovi spazi prima e dopo / e \
    numero = re.sub(r'\s*[/\\]\s*', '', numero)
    # Rimuovi anche / e \ rimanenti (senza spazi)
    numero = numero.replace('/', '').replace('\\', '')
    # Rimuovi TUTTI gli spazi (non solo normalizza)
    numero = re.sub(r'\s+', '', numero)
    return numero.strip()


def pulisci_caratteri_speciali(valore: str) -> str:
    """
    Rimuove i caratteri '/' e '\' da qualsiasi campo.
    Rimuove anche TUTTI gli spazi dal valore.
    NON aggiunge spazi, rimuove completamente i caratteri.
    
    Args:
        valore: Stringa da pulire
        
    Returns:
        Stringa senza '/', '\' e spazi
    """
    if not valore:
        return ""
    # Rimuovi spazi prima e dopo / e \
    valore = re.sub(r'\s*[/\\]\s*', '', valore)
    # Rimuovi anche / e \ rimanenti (senza spazi)
    valore = valore.replace('/', '').replace('\\', '')
    # Rimuovi TUTTI gli spazi (non solo normalizza)
    valore = re.sub(r'\s+', '', valore)
    return valore.strip()


def estrai_anno_mese_da_data(data_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Estrae anno e mese da una stringa data.
    Supporta vari formati: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, ecc.
    
    Args:
        data_str: Stringa con la data
        
    Returns:
        Tupla (anno, mese) o (None, None) se non valida
    """
    if not data_str:
        return None, None
    
    data_str = data_str.strip()
    
    # Prova formato DD/MM/YYYY o DD-MM-YYYY
    separatori = ['/', '-', '.']
    for sep in separatori:
        if sep in data_str:
            parti = data_str.split(sep)
            if len(parti) >= 3:
                try:
                    # Prova a capire se è DD/MM/YYYY o YYYY/MM/DD
                    giorno = int(parti[0])
                    mese = int(parti[1])
                    anno = int(parti[2])
                    
                    # Se il giorno è > 31, probabilmente è YYYY/MM/DD
                    if giorno > 31:
                        anno = giorno
                        mese = int(parti[1])
                        giorno = int(parti[2])
                    
                    # Se l'anno ha solo 2 cifre, assumiamo 20XX
                    if anno < 100:
                        anno += 2000
                    
                    if 1 <= mese <= 12 and 1900 <= anno <= 2100:
                        return anno, mese
                except (ValueError, IndexError):
                    continue
    
    return None, None


def calcola_codice_fattura(anno: Optional[int], mese: Optional[int], 
                           partita_iva: str, numero: str) -> str:
    """
    Calcola il codice fattura nel formato: Anno-Mese-PartitaIVA-Numero
    Rimuove i caratteri '/' e '\' da partita_iva e numero.
    
    Args:
        anno: Anno estratto dalla data
        mese: Mese estratto dalla data
        partita_iva: Partita IVA fornitore
        numero: Numero fattura
        
    Returns:
        Stringa nel formato Anno-Mese-PartitaIVA-Numero (senza / e \)
    """
    anno_str = str(anno) if anno else "0000"
    mese_str = f"{mese:02d}" if mese else "00"
    # Pulisci partita_iva e numero da / e \
    piva_str = pulisci_caratteri_speciali(partita_iva) if partita_iva else ""
    num_str = pulisci_caratteri_speciali(numero) if numero else ""
    
    return f"{anno_str}-{mese_str}-{piva_str}-{num_str}"


def leggi_csv_estero(file_path: str) -> List[Dict]:
    """
    Legge il file CSV per acquisti estero e estrae le colonne specificate:
    - Colonna G (indice 6): Data emissione
    - Colonna D (indice 3): Denominazione fornitore
    - Partita IVA: default "ESTERO"
    - Colonna F (indice 5): Numero fattura
    - Colonna M (indice 12): Imponibile
    
    Rimuove gli apici singoli dai valori e calcola un codice aggiuntivo.
    
    Args:
        file_path: Percorso del file CSV
        
    Returns:
        Lista di dizionari con i dati estratti
    """
    dati = []
    
    # Indici delle colonne (0-based)
    COL_G = 6  # Data emissione
    COL_D = 3  # Denominazione fornitore
    COL_F = 5  # Numero fattura
    COL_M = 12  # Imponibile
    PARTITA_IVA_DEFAULT = "ESTERO"
    
    try:
        # Prova prima con UTF-8
        encoding = 'utf-8'
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Usa il punto e virgola come delimitatore
                reader = csv.reader(f, delimiter=';')
                # Salta l'intestazione se presente
                first_row = next(reader, None)
                if first_row is None:
                    return []
                
                print(f"✓ Intestazione rilevata (estero): {len(first_row)} colonne")
                
                # Leggi tutte le righe
                for idx, row in enumerate(reader, start=2):
                    if len(row) <= max(COL_G, COL_D, COL_F, COL_M):
                        # Riga troppo corta, salta
                        print(f"⚠ Riga {idx} saltata (estero): troppo corta ({len(row)} colonne)")
                        continue
                    
                    # Estrai i valori dalle colonne specificate
                    data_emissione = rimuovi_apici(row[COL_G]) if len(row) > COL_G else ""
                    denominazione = rimuovi_apici(row[COL_D]) if len(row) > COL_D else ""
                    numero_raw = rimuovi_apici(row[COL_F]) if len(row) > COL_F else ""
                    numero = pulisci_numero_fattura(numero_raw)  # Rimuovi / e \ completamente
                    imponibile = rimuovi_apici(row[COL_M]) if len(row) > COL_M else ""
                    partita_iva = PARTITA_IVA_DEFAULT
                    # Pulisci anche la partita IVA da / e \
                    partita_iva = pulisci_caratteri_speciali(partita_iva)
                    
                    # Estrai anno e mese dalla data
                    anno, mese = estrai_anno_mese_da_data(data_emissione)
                    
                    # Calcola il codice fattura
                    codice_fattura = calcola_codice_fattura(anno, mese, partita_iva, numero)
                    
                    # Crea il dizionario con i dati estratti
                    fattura = {
                        "numero_fattura": numero,
                        "data_emissione": data_emissione,
                        "partita_iva_fornitore": partita_iva,
                        "denominazione_fornitore": denominazione,
                        "imponibile": imponibile,
                        "anno": anno,
                        "mese": mese,
                        "codice_fattura": codice_fattura
                    }
                    
                    dati.append(fattura)
                    
        except UnicodeDecodeError:
            # Se fallisce, prova con latin-1
            encoding = 'latin-1'
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=';')
                first_row = next(reader, None)
                if first_row is None:
                    return []
                
                print(f"✓ Intestazione rilevata (estero): {len(first_row)} colonne (encoding: latin-1)")
                
                for idx, row in enumerate(reader, start=2):
                    if len(row) <= max(COL_G, COL_D, COL_F, COL_M):
                        print(f"⚠ Riga {idx} saltata (estero): troppo corta ({len(row)} colonne)")
                        continue
                    
                    data_emissione = rimuovi_apici(row[COL_G]) if len(row) > COL_G else ""
                    denominazione = rimuovi_apici(row[COL_D]) if len(row) > COL_D else ""
                    numero_raw = rimuovi_apici(row[COL_F]) if len(row) > COL_F else ""
                    numero = pulisci_numero_fattura(numero_raw)  # Rimuovi / e \ completamente
                    imponibile = rimuovi_apici(row[COL_M]) if len(row) > COL_M else ""
                    partita_iva = PARTITA_IVA_DEFAULT
                    # Pulisci anche la partita IVA da / e \
                    partita_iva = pulisci_caratteri_speciali(partita_iva)
                    
                    anno, mese = estrai_anno_mese_da_data(data_emissione)
                    codice_fattura = calcola_codice_fattura(anno, mese, partita_iva, numero)
                    
                    fattura = {
                        "numero_fattura": numero,
                        "data_emissione": data_emissione,
                        "partita_iva_fornitore": partita_iva,
                        "denominazione_fornitore": denominazione,
                        "imponibile": imponibile,
                        "anno": anno,
                        "mese": mese,
                        "codice_fattura": codice_fattura
                    }
                    
                    dati.append(fattura)
    
    except Exception as e:
        print(f"❌ Errore nella lettura del CSV estero: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return dati


def leggi_csv(file_path: str) -> List[Dict]:
    """
    Legge il file CSV e estrae le colonne specificate:
    - Colonna C (indice 2): Numero fattura / Documento
    - Colonna D (indice 3): Data emissione
    - Colonna G (indice 6): Partita IVA fornitore
    - Colonna H (indice 7): Denominazione fornitore
    - Colonna L (indice 11): Imponibile
    
    Rimuove gli apici singoli dai valori e calcola un codice aggiuntivo.
    
    Args:
        file_path: Percorso del file CSV
        
    Returns:
        Lista di dizionari con i dati estratti
    """
    dati = []
    
    # Indici delle colonne (0-based)
    COL_C = 2  # Numero fattura / Documento
    COL_D = 3  # Data emissione
    COL_G = 6  # Partita IVA fornitore
    COL_H = 7  # Denominazione fornitore
    COL_L = 11  # Imponibile
    
    try:
        # Prova prima con UTF-8
        encoding = 'utf-8'
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Usa il punto e virgola come delimitatore (formato italiano/Europeo)
                reader = csv.reader(f, delimiter=';')
                # Salta l'intestazione se presente
                first_row = next(reader, None)
                if first_row is None:
                    return []
                
                print(f"✓ Intestazione rilevata: {len(first_row)} colonne")
                
                # Leggi tutte le righe
                for idx, row in enumerate(reader, start=2):  # start=2 perché la prima riga è l'intestazione
                    if len(row) <= max(COL_C, COL_D, COL_G, COL_H, COL_L):
                        # Riga troppo corta, salta
                        print(f"⚠ Riga {idx} saltata: troppo corta ({len(row)} colonne)")
                        continue
                    
                    # Estrai i valori dalle colonne specificate
                    numero_raw = rimuovi_apici(row[COL_C]) if len(row) > COL_C else ""
                    numero = pulisci_numero_fattura(numero_raw)  # Rimuovi / e \ completamente
                    data_emissione = rimuovi_apici(row[COL_D]) if len(row) > COL_D else ""
                    partita_iva_raw = rimuovi_apici(row[COL_G]) if len(row) > COL_G else ""
                    partita_iva = pulisci_caratteri_speciali(partita_iva_raw)  # Rimuovi / e \ completamente
                    denominazione = rimuovi_apici(row[COL_H]) if len(row) > COL_H else ""
                    imponibile = rimuovi_apici(row[COL_L]) if len(row) > COL_L else ""
                    
                    # Estrai anno e mese dalla data
                    anno, mese = estrai_anno_mese_da_data(data_emissione)
                    
                    # Calcola il codice fattura
                    codice_fattura = calcola_codice_fattura(anno, mese, partita_iva, numero)
                    
                    # Crea il dizionario con i dati estratti
                    fattura = {
                        "numero_fattura": numero,
                        "data_emissione": data_emissione,
                        "partita_iva_fornitore": partita_iva,
                        "denominazione_fornitore": denominazione,
                        "imponibile": imponibile,
                        "anno": anno,
                        "mese": mese,
                        "codice_fattura": codice_fattura
                    }
                    
                    dati.append(fattura)
                    
        except UnicodeDecodeError:
            # Se fallisce, prova con latin-1
            encoding = 'latin-1'
            with open(file_path, 'r', encoding=encoding) as f:
                # Usa il punto e virgola come delimitatore
                reader = csv.reader(f, delimiter=';')
                first_row = next(reader, None)
                if first_row is None:
                    return []
                
                print(f"✓ Intestazione rilevata: {len(first_row)} colonne (encoding: latin-1)")
                
                for idx, row in enumerate(reader, start=2):
                    if len(row) <= max(COL_C, COL_D, COL_G, COL_H, COL_L):
                        print(f"⚠ Riga {idx} saltata: troppo corta ({len(row)} colonne)")
                        continue
                    
                    numero_raw = rimuovi_apici(row[COL_C]) if len(row) > COL_C else ""
                    numero = pulisci_numero_fattura(numero_raw)  # Rimuovi / e \ completamente
                    data_emissione = rimuovi_apici(row[COL_D]) if len(row) > COL_D else ""
                    partita_iva_raw = rimuovi_apici(row[COL_G]) if len(row) > COL_G else ""
                    partita_iva = pulisci_caratteri_speciali(partita_iva_raw)  # Rimuovi / e \ completamente
                    denominazione = rimuovi_apici(row[COL_H]) if len(row) > COL_H else ""
                    imponibile = rimuovi_apici(row[COL_L]) if len(row) > COL_L else ""
                    
                    anno, mese = estrai_anno_mese_da_data(data_emissione)
                    codice_fattura = calcola_codice_fattura(anno, mese, partita_iva, numero)
                    
                    fattura = {
                        "numero_fattura": numero,
                        "data_emissione": data_emissione,
                        "partita_iva_fornitore": partita_iva,
                        "denominazione_fornitore": denominazione,
                        "imponibile": imponibile,
                        "anno": anno,
                        "mese": mese,
                        "codice_fattura": codice_fattura
                    }
                    
                    dati.append(fattura)
    
    except Exception as e:
        print(f"❌ Errore nella lettura del CSV: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return dati


def crea_cartella_se_non_esiste(cartella_path: str) -> bool:
    """
    Crea la cartella se non esiste.
    
    Args:
        cartella_path: Percorso della cartella da creare
        
    Returns:
        True se la cartella esiste o è stata creata, False altrimenti
    """
    try:
        if not os.path.exists(cartella_path):
            os.makedirs(cartella_path)
            print(f"✓ Cartella creata: {cartella_path}")
        return True
    except Exception as e:
        print(f"❌ Errore nella creazione della cartella {cartella_path}: {e}")
        return False


def verifica_file_esistente(percorso_json: str) -> bool:
    """
    Verifica se il file JSON esiste già.
    
    Args:
        percorso_json: Percorso del file JSON da verificare
        
    Returns:
        True se il file esiste, False altrimenti
    """
    return os.path.exists(percorso_json)


def salva_json(dati_italia: List[Dict], dati_estero: List[Dict], anno: int, mese: int, 
                cartella_base: str, sovrascrivi: bool = False) -> tuple[Optional[str], Optional[str]]:
    """
    Salva i dati in un file JSON nella cartella corretta (anno/mese).
    
    Args:
        dati_italia: Lista di dizionari con i dati delle fatture Italia
        dati_estero: Lista di dizionari con i dati delle fatture Estero
        anno: Anno selezionato
        mese: Mese selezionato (1-12)
        cartella_base: Cartella base delle fatture ricevute
        sovrascrivi: Se True, sovrascrive il file esistente senza chiedere
        
    Returns:
        Tupla (percorso_file, messaggio_errore)
        - Se successo: (percorso_file, None)
        - Se file esiste e non sovrascrivere: (None, "file_esistente")
        - Se errore: (None, messaggio_errore)
    """
    try:
        # Costruisci il percorso della cartella anno/mese
        cartella_anno = os.path.join(cartella_base, str(anno))
        cartella_mese = os.path.join(cartella_anno, f"{mese:02d}")
        
        # Crea le cartelle se non esistono
        if not crea_cartella_se_non_esiste(cartella_anno):
            return None
        if not crea_cartella_se_non_esiste(cartella_mese):
            return None
        
        # Nome del file JSON
        nome_file = f"lista_fatture_{anno}_{mese:02d}.json"
        percorso_json = os.path.join(cartella_mese, nome_file)
        
        # Verifica se il file esiste già
        if verifica_file_esistente(percorso_json) and not sovrascrivi:
            return None, "file_esistente"
        
        # Prepara i dati da salvare
        # Formato data: dd/mm/yyyy
        data_caricamento = datetime.now().strftime("%d/%m/%Y")
        
        totale_italia = len(dati_italia)
        totale_estero = len(dati_estero)
        totale_complessivo = totale_italia + totale_estero
        
        # Combina le fatture (prima Italia, poi Estero)
        tutte_fatture = dati_italia + dati_estero
        
        json_data = {
            "anno": anno,
            "mese": mese,
            "data_caricamento": data_caricamento,
            "fatture": tutte_fatture,
            "totale_fatture": totale_complessivo,
            "totale_fatture_italia": totale_italia,
            "totale_fatture_estero": totale_estero
        }
        
        # Salva il JSON
        with open(percorso_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ File JSON creato: {percorso_json}")
        print(f"✓ Totale fatture Italia: {totale_italia}")
        print(f"✓ Totale fatture Estero: {totale_estero}")
        print(f"✓ Totale fatture caricate: {totale_complessivo}")
        
        return percorso_json, None
    
    except Exception as e:
        print(f"❌ Errore nel salvataggio del JSON: {e}")
        return None, str(e)


def processa_carica_lista(csv_path: str, anno: int, mese: int, 
                         file_estero: Optional[str] = None,
                         sovrascrivi: bool = False) -> tuple[bool, str, Optional[str]]:
    """
    Funzione principale per processare il caricamento della lista da CSV.
    
    Args:
        csv_path: Percorso del file CSV Italia
        anno: Anno selezionato
        mese: Mese selezionato (1-12)
        file_estero: Percorso del file CSV Estero (opzionale)
        sovrascrivi: Se True, sovrascrive il file esistente senza chiedere
        
    Returns:
        Tupla (successo, messaggio, percorso_json)
        - Se serve conferma: (False, "file_esistente", percorso_json)
        - Se successo: (True, messaggio, percorso_json)
        - Se errore: (False, messaggio_errore, None)
    """
    # 1. Verifica formato CSV Italia
    if not verifica_formato_csv(csv_path):
        return False, "Il file Italia non è un CSV valido", None
    
    # 2. Leggi il CSV Italia
    print(f"📖 Lettura del file CSV Italia: {csv_path}")
    dati_italia = leggi_csv(csv_path)
    
    if not dati_italia:
        return False, "Nessun dato trovato nel file CSV Italia. Verifica che il file contenga le colonne richieste (C, D, G, H, L).", None
    
    print(f"✓ Righe lette dal CSV Italia: {len(dati_italia)}")
    print(f"✓ Fatture Italia estratte: {len(dati_italia)}")
    
    # 3. Leggi il CSV Estero se presente
    dati_estero = []
    if file_estero:
        if not verifica_formato_csv(file_estero):
            return False, "Il file Estero non è un CSV valido", None
        
        print(f"📖 Lettura del file CSV Estero: {file_estero}")
        dati_estero = leggi_csv_estero(file_estero)
        
        if dati_estero:
            print(f"✓ Righe lette dal CSV Estero: {len(dati_estero)}")
            print(f"✓ Fatture Estero estratte: {len(dati_estero)}")
        else:
            print("⚠ Nessun dato trovato nel file CSV Estero")
    
    # 4. Ottieni la cartella base
    cartella_base = get_cartella_ricevute()
    if not cartella_base:
        return False, "Impossibile trovare la cartella delle fatture ricevute", None
    
    # 5. Salva il JSON nella cartella corretta
    percorso_json, errore = salva_json(dati_italia, dati_estero, anno, mese, cartella_base, sovrascrivi)
    
    if errore == "file_esistente":
        # Costruisci il percorso per restituirlo
        cartella_anno = os.path.join(cartella_base, str(anno))
        cartella_mese = os.path.join(cartella_anno, f"{mese:02d}")
        nome_file = f"lista_fatture_{anno}_{mese:02d}.json"
        percorso_completo = os.path.join(cartella_mese, nome_file)
        return False, "file_esistente", percorso_completo
    
    if errore:
        return False, f"Errore nel salvataggio del file JSON: {errore}", None
    
    if not percorso_json:
        return False, "Errore nel salvataggio del file JSON", None
    
    totale_italia = len(dati_italia)
    totale_estero = len(dati_estero)
    totale_complessivo = totale_italia + totale_estero
    
    messaggio = f"Lista caricata con successo!\nFile salvato: {os.path.basename(percorso_json)}\n"
    messaggio += f"Totale fatture Italia: {totale_italia}\n"
    if totale_estero > 0:
        messaggio += f"Totale fatture Estero: {totale_estero}\n"
    messaggio += f"Totale complessivo: {totale_complessivo}"
    
    return True, messaggio, percorso_json


if __name__ == "__main__":
    # Test dello script
    if len(sys.argv) < 4:
        print("Uso: python carica_lista_csv.py <csv_path> <anno> <mese>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    anno = int(sys.argv[2])
    mese = int(sys.argv[3])
    
    successo, messaggio = processa_carica_lista(csv_path, anno, mese)
    
    if successo:
        print(f"✓ {messaggio}")
        sys.exit(0)
    else:
        print(f"❌ {messaggio}")
        sys.exit(1)

