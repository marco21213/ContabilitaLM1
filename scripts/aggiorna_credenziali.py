import configparser
import os

def aggiorna_credenziali(codice_fiscale, pin, password):
    # Ottieni il percorso assoluto della directory principale
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, '../config.ini')
    
    # Inizializza il parser del file config
    config = configparser.ConfigParser()
    
    # Leggi il file config.ini esistente
    config.read(config_path)
    
    # Aggiorna la sezione Parametri (dove ora teniamo anche le credenziali)
    if 'Parametri' not in config:
        config.add_section('Parametri')
        
    config['Parametri']['codicefiscale'] = codice_fiscale
    config['Parametri']['pin'] = pin 
    config['Parametri']['password'] = password
    
    # Salva le modifiche nel file
    with open(config_path, 'w') as configfile:
        config.write(configfile)
        
    return True
