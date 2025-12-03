import configparser
import os

def load_config():
    """Carica il file di configurazione."""
    config = configparser.ConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(current_dir))
    config_path = os.path.join(project_dir, 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"File config.ini non trovato: {config_path}")
    
    config.read(config_path)
    return config

def save_config(config, start_date, end_date, date_option, venoacq):
    """Salva le configurazioni nel file."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(project_dir, 'config.ini')
        
        config.set('Parametri', 'dal', start_date.replace('/', ''))
        config.set('Parametri', 'al', end_date.replace('/', ''))
        config.set('Parametri', 'tipo', '1' if date_option == "ricezione" else '2')
        config.set('Parametri', 'venoacq', 'A' if venoacq == "Acquisti" else 'V')

        with open(config_path, 'w') as configfile:
            config.write(configfile)
            
    except Exception as e:
        raise Exception(f"Errore durante l'aggiornamento del file di configurazione: {e}")