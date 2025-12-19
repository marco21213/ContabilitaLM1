from datetime import datetime, timedelta
import os
from pathlib import Path

from parametri_db import carica_parametri, aggiorna_parametri


def get_config_path() -> str:
    """
    Trova il percorso di config.ini partendo dalla directory corrente dello script
    e risalendo fino alla root del progetto.
    """
    # Percorso dello script corrente
    script_dir = Path(__file__).parent.resolve()
    
    # Prova prima nella directory dello script
    config_path = script_dir.parent / "config.ini"
    if config_path.exists():
        return str(config_path)
    
    # Prova nella directory corrente di lavoro
    config_path = Path("config.ini").resolve()
    if config_path.exists():
        return str(config_path)
    
    # Fallback: usa config.ini nella directory corrente
    return "config.ini"


def ottieni_date_da_parametri() -> tuple[str | None, str | None]:
    """
    Calcola dal/al partendo dal campo 'aggiornamento' presente nella tabella parametri.
    - dal: 5 giorni prima di aggiornamento, formato ddmmyyyy
    - al: data odierna, formato ddmmyyyy
    """
    config_path = get_config_path()
    
    try:
        params = carica_parametri(config_path=config_path)
    except Exception as e:
        print(f"Errore nel leggere i parametri dal database: {e}")
        return None, None

    # sqlite3.Row supporta l'accesso come dizionario con [] o get()
    try:
        data_aggiornamento_str = params["aggiornamento"]
    except (KeyError, TypeError):
        try:
            data_aggiornamento_str = params.get("aggiornamento")
        except:
            data_aggiornamento_str = None
    
    if not data_aggiornamento_str:
        print("Errore: il campo 'aggiornamento' non è valorizzato nella tabella parametri.")
        return None, None

    try:
        data_aggiornamento = datetime.strptime(data_aggiornamento_str, "%d/%m/%Y")
    except ValueError:
        print("Errore: Formato data 'aggiornamento' non valido. Usare il formato dd/mm/yyyy.")
        return None, None

    cinque_giorni_prima = data_aggiornamento - timedelta(days=5)
    data_odierna = datetime.today()

    dal_value = cinque_giorni_prima.strftime("%d%m%Y")
    al_value = data_odierna.strftime("%d%m%Y")

    return dal_value, al_value


def aggiorna_parametri_download():
    """
    Aggiorna nel database i campi:
    - dal, al calcolati da 'aggiornamento'
    - tipo = 1
    - venoacq = 'A'
    """
    print("=" * 60)
    print("SPEED_DOWNLOAD: Avvio aggiornamento parametri nel database")
    print("=" * 60)
    
    config_path = get_config_path()
    print(f"Config.ini trovato: {config_path}")
    print(f"Directory corrente: {os.getcwd()}")
    
    dal_value, al_value = ottieni_date_da_parametri()
    print(f"Date calcolate: dal={dal_value}, al={al_value}")

    if not (dal_value and al_value):
        print("✗ ERRORE: Impossibile calcolare le date. Verificare i log.")
        return False

    try:
        print(f"Aggiornamento database con: dal={dal_value}, al={al_value}, tipo=1, venoacq=A")
        # Aggiorna SOLO nel database, non in config.ini
        aggiorna_parametri(
            dal=dal_value, 
            al=al_value, 
            tipo=1, 
            venoacq="A",
            config_path=config_path
        )
        print(f"✓ SUCCESSO: Parametri aggiornati nel database")
        print(f"  - dal: {dal_value}")
        print(f"  - al: {al_value}")
        print(f"  - tipo: 1")
        print(f"  - venoacq: A")
        return True
    except Exception as e:
        print(f"✗ ERRORE durante l'aggiornamento dei parametri nel database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    aggiorna_parametri_download()
