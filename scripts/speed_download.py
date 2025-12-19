from datetime import datetime, timedelta

from parametri_db import carica_parametri, aggiorna_parametri


def ottieni_date_da_parametri() -> tuple[str | None, str | None]:
    """
    Calcola dal/al partendo dal campo 'aggiornamento' presente nella tabella parametri.
    - dal: 5 giorni prima di aggiornamento, formato ddmmyyyy
    - al: data odierna, formato ddmmyyyy
    """
    try:
        params = carica_parametri()
    except Exception as e:
        print(f"Errore nel leggere i parametri dal database: {e}")
        return None, None

    data_aggiornamento_str = params.get("aggiornamento")
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
    dal_value, al_value = ottieni_date_da_parametri()

    if not (dal_value and al_value):
        print("Impossibile aggiornare i parametri nel database. Verificare i log.")
        return

    try:
        aggiorna_parametri(dal=dal_value, al=al_value, tipo=1, venoacq="A")
        print(f"Modificati i parametri nel database: dal={dal_value}, al={al_value}, tipo=1, venoacq=A")
    except Exception as e:
        print(f"Errore durante l'aggiornamento dei parametri nel database: {e}")


if __name__ == "__main__":
    aggiorna_parametri_download()
