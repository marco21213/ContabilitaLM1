import configparser
from datetime import datetime, timedelta

# Funzione per ottenere le date nel formato richiesto
def ottieni_date_da_config(file_config):
    config = configparser.ConfigParser()
    config.read(file_config)

    # Leggi la data di aggiornamento dalla sezione [Parametri]
    if 'Parametri' in config and 'aggiornamento' in config['Parametri']:
        data_aggiornamento_str = config['Parametri']['aggiornamento']
        try:
            # Converte la stringa in oggetto datetime
            data_aggiornamento = datetime.strptime(data_aggiornamento_str, '%d/%m/%Y')
        except ValueError:
            print("Errore: Formato data 'aggiornamento' non valido. Usare il formato dd/mm/yyyy.")
            return None, None

        # Calcola 'dal' come 5 giorni prima di 'aggiornamento'
        cinque_giorni_prima = data_aggiornamento - timedelta(days=5)

        # Data odierna per 'al'
        data_odierna = datetime.today()

        # Formatta le date nel formato richiesto: ddmmyyyy
        dal_value = cinque_giorni_prima.strftime('%d%m%Y')
        al_value = data_odierna.strftime('%d%m%Y')

        return dal_value, al_value
    else:
        print("Errore: La sezione [Parametri] o il parametro 'aggiornamento' non esistono nel file config.ini.")
        return None, None

# Funzione per aggiornare i parametri 'dal', 'al', 'tipo' e 'venoacq'
def aggiorna_config(file_config):
    config = configparser.ConfigParser()

    # Leggi il file config.ini
    config.read(file_config)

    # Ottieni le date da assegnare
    dal_value, al_value = ottieni_date_da_config(file_config)

    if dal_value and al_value:
        # Modifica i valori sotto la sezione [Parametri]
        if 'Parametri' in config:
            config['Parametri']['dal'] = dal_value
            config['Parametri']['al'] = al_value
            config['Parametri']['tipo'] = '1'
            config['Parametri']['venoacq'] = 'A'
        else:
            print("La sezione [Parametri] non è stata trovata.")

        # Scrivi le modifiche al file
        with open(file_config, 'w') as configfile:
            config.write(configfile)
        print(f"Modificati i parametri in {file_config}: dal={dal_value}, al={al_value}, tipo=1, venoacq=A")
    else:
        print("Impossibile aggiornare i parametri. Verificare i log.")

# Esegui la funzione
aggiorna_config('config.ini')
