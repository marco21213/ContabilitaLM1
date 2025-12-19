from scripts.parametri_db import aggiorna_credenziali as aggiorna_credenziali_db


def aggiorna_credenziali(codice_fiscale, pin, password):
    """
    Aggiorna codice fiscale, PIN e password nella tabella parametri (id = 1).
    """
    aggiorna_credenziali_db(
        codicefiscale=codice_fiscale,
        pin=pin,
        password=password,
    )
    return True
