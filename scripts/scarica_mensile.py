import subprocess
import os
from configparser import ConfigParser
from datetime import datetime, timedelta
import calendar

def calcola_date_mese(mese, anno):
    """Calcola il primo e ultimo giorno del mese specificato."""
    primo_giorno = datetime(anno, mese, 1)
    ultimo_giorno_numero = calendar.monthrange(anno, mese)[1]
    ultimo_giorno = datetime(anno, mese, ultimo_giorno_numero)
    
    return primo_giorno.strftime("%d/%m/%Y"), ultimo_giorno.strftime("%d/%m/%Y")

def aggiorna_config_mensile(mese, anno, tipo_documento):
    """Aggiorna il file config.ini con i parametri per il download mensile."""
    config_path = "config.ini"
    config = ConfigParser()
    config.read(config_path)
    
    # Calcola le date del mese
    data_inizio, data_fine = calcola_date_mese(mese, anno)
    
    # Aggiorna i parametri
    if 'Parametri' not in config:
        config.add_section('Parametri')
    
    config['Parametri']['dal'] = data_inizio.replace('/', '')
    config['Parametri']['al'] = data_fine.replace('/', '')
    config['Parametri']['tipo'] = '2'  # MODIFICATO: Data di emissione (invece di 1 - Data di ricezione)
    config['Parametri']['venoacq'] = 'A' if tipo_documento == 'acquisti' else 'V'
    
    # Aggiorna timestamp
    data_odierna = datetime.now().strftime("%d/%m/%Y")
    if 'Parametri' not in config:
        config.add_section('Parametri')
    config['Parametri']['aggiornamento'] = data_odierna
    
    with open(config_path, "w") as config_file:
        config.write(config_file)
    
    print(f"Config aggiornato per {calendar.month_name[mese]} {anno} ({tipo_documento})")
    print(f"Periodo: {data_inizio} - {data_fine}")

def esegui_download_mensile(mese, anno, tipo_documento='acquisti'):
    """Esegue il download mensile completo."""
    
    # Ottieni il percorso della directory corrente dello script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Usa il percorso padre se necessario
    scripts_path = os.path.join(os.path.dirname(script_dir), "scripts")
    
    # Verifica l'esistenza del percorso
    if not os.path.exists(scripts_path):
        scripts_path = os.path.join(script_dir, "scripts")
    
    try:
        # 1. Aggiorna configurazione con i parametri mensili
        aggiorna_config_mensile(mese, anno, tipo_documento)
        
        print("Inizio download mensile...")
        
        # 2. Esegui gli script in sequenza (RIMOSSO speed_download.py)
        # MODIFICATO: Eliminata l'esecuzione di speed_download.py
        
        print("Esecuzione scarfec32.py...")
        subprocess.run(["python", os.path.join(scripts_path, "scarfec32.py")], check=True)
        
        print("Esecuzione rinomina.py...")
        subprocess.run(["python", os.path.join(scripts_path, "rinomina.py"), "--no-stampa"], check=True)
        
        print("Operazioni completate con successo!")
        
    except subprocess.CalledProcessError as e:
        print(f"Errore durante l'esecuzione di uno script: {e}")
        raise
    except Exception as e:
        print(f"Errore generale: {e}")
        raise

if __name__ == "__main__":
    # Esempio di utilizzo
    # Per uso da GUI, questi parametri verranno passati come argomenti
    import sys
    
    if len(sys.argv) >= 4:
        mese = int(sys.argv[1])
        anno = int(sys.argv[2])
        tipo_documento = sys.argv[3]  # 'acquisti' o 'vendite'
        esegui_download_mensile(mese, anno, tipo_documento)
    else:
        # Valori di default per test
        mese_corrente = datetime.now().month
        anno_corrente = datetime.now().year
        esegui_download_mensile(mese_corrente, anno_corrente, 'acquisti')