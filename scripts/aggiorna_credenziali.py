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
    
    # Aggiorna la sezione Credenziali
    if 'Credenziali' not in config:
        config.add_section('Credenziali')
        
    config['Credenziali']['codicefiscale'] = codice_fiscale
    config['Credenziali']['pin'] = pin 
    config['Credenziali']['password'] = password
    
    # Salva le modifiche nel file
    with open(config_path, 'w') as configfile:
        config.write(configfile)
        
    return True
