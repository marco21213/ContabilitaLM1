import configparser
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any


def get_db_path(config_path: str = "config.ini") -> str:
    """
    Legge il percorso del database dalla sezione [Autenticazione] di config.ini.
    Resta il solo utilizzo di config.ini per la connessione al database.
    Gestisce percorsi cross-platform e crea la directory se necessario.
    """
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    if "Autenticazione" not in config or "percorso_database" not in config["Autenticazione"]:
        # Fallback minimale: database nella cartella del progetto
        db_path = Path("database.db").resolve()
    else:
        db_path_str = config.get("Autenticazione", "percorso_database", fallback="database.db")
        db_path = Path(db_path_str).expanduser()
        
        # Se il percorso è relativo, risolvilo rispetto alla root del progetto
        if not db_path.is_absolute():
            project_root = Path(config_path).resolve().parent
            db_path = project_root / db_path
        else:
            db_path = db_path.resolve()
    
    # Crea la directory se non esiste
    db_dir = db_path.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
    
    return str(db_path)


def _open_connection(config_path: str = "config.ini") -> sqlite3.Connection:
    """Restituisce una connessione SQLite aperta usando il percorso del DB da config.ini.
    Crea automaticamente la directory e il database se non esistono.
    """
    db_path = get_db_path(config_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Impossibile aprire il database {db_path}: {e}")


def carica_parametri(config_path: str = "config.ini") -> sqlite3.Row:
    """
    Carica l'unica riga di parametri (id = 1) dalla tabella parametri.
    Restituisce un oggetto sqlite3.Row indicizzabile per nome colonna, es. row['codicefiscale'].
    """
    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM parametri WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                "Nessun record trovato nella tabella 'parametri' (atteso id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        return row
    finally:
        conn.close()


def aggiorna_parametri(
    *,
    dal: Optional[str] = None,
    al: Optional[str] = None,
    tipo: Optional[int] = None,
    venoacq: Optional[str] = None,
    aggiornamento: Optional[str] = None,
    pivadiretta: Optional[str] = None,
    config_path: str = "config.ini",
) -> None:
    """
    Aggiorna uno o più campi nella riga id=1 della tabella parametri.
    I parametri passati come None vengono ignorati.
    """
    campi: Dict[str, Any] = {}
    if dal is not None:
        campi["dal"] = dal
    if al is not None:
        campi["al"] = al
    if tipo is not None:
        campi["tipo"] = int(tipo)
    if venoacq is not None:
        campi["venoacq"] = venoacq
    if aggiornamento is not None:
        campi["aggiornamento"] = aggiornamento
    if pivadiretta is not None:
        campi["pivadiretta"] = pivadiretta

    if not campi:
        return

    placeholders = ", ".join(f"{k} = ?" for k in campi.keys())
    values = list(campi.values())

    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE parametri SET {placeholders} WHERE id = 1",
            values,
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                "Impossibile aggiornare la tabella 'parametri' (nessuna riga con id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        conn.commit()
    finally:
        conn.close()


def aggiorna_credenziali(
    *,
    codicefiscale: Optional[str] = None,
    pin: Optional[str] = None,
    password: Optional[str] = None,
    config_path: str = "config.ini",
) -> None:
    """
    Aggiorna CF/PIN/password nella riga id=1 della tabella parametri.
    I parametri None vengono ignorati.
    """
    campi: Dict[str, Any] = {}
    if codicefiscale is not None:
        campi["codicefiscale"] = codicefiscale
    if pin is not None:
        campi["pin"] = pin
    if password is not None:
        campi["password"] = password

    if not campi:
        return

    placeholders = ", ".join(f"{k} = ?" for k in campi.keys())
    values = list(campi.values())

    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE parametri SET {placeholders} WHERE id = 1",
            values,
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                "Impossibile aggiornare la tabella 'parametri' per le credenziali (nessuna riga con id = 1)."
            )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# FUNZIONI PER PARAMETRI CARTELLE
# ============================================================================

def get_cartella_emesse(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella fatture emesse (vendite)."""
    try:
        params = carica_parametri(config_path)
        # sqlite3.Row supporta l'indicizzazione diretta, restituisce None se il campo è NULL
        value = params["cartellaemesse"]
        return value if value else None
    except (KeyError, IndexError):
        # Campo non presente nella tabella
        return None
    except RuntimeError:
        # Nessun record trovato nella tabella
        return None
    except Exception as e:
        # Log dell'errore per debug
        import logging
        logging.getLogger(__name__).error(f"Errore in get_cartella_emesse: {e}")
        return None


def get_cartella_ricevute(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella fatture ricevute (acquisti)."""
    try:
        params = carica_parametri(config_path)
        value = params["cartellaricevute"]
        return value if value else None
    except (KeyError, IndexError):
        return None
    except RuntimeError:
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore in get_cartella_ricevute: {e}")
        return None


def get_cartella_stampa(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella stampa."""
    try:
        params = carica_parametri(config_path)
        value = params["cartellastampa"]
        return value if value else None
    except (KeyError, IndexError):
        return None
    except RuntimeError:
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore in get_cartella_stampa: {e}")
        return None


def get_import_acquisti(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella import acquisti."""
    try:
        params = carica_parametri(config_path)
        value = params["importacquisti"]
        return value if value else None
    except (KeyError, IndexError):
        return None
    except RuntimeError:
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore in get_import_acquisti: {e}")
        return None


def get_import_vendite(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella import vendite."""
    try:
        params = carica_parametri(config_path)
        value = params["importavendite"]
        return value if value else None
    except (KeyError, IndexError):
        return None
    except RuntimeError:
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore in get_import_vendite: {e}")
        return None


def get_import_rapido(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il percorso della cartella import rapido."""
    try:
        params = carica_parametri(config_path)
        value = params["importarapido"]
        return value if value else None
    except (KeyError, IndexError):
        return None
    except RuntimeError:
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Errore in get_import_rapido: {e}")
        return None


def aggiorna_parametri_cartelle(
    *,
    cartellaemesse: Optional[str] = None,
    cartellaricevute: Optional[str] = None,
    cartellastampa: Optional[str] = None,
    importacquisti: Optional[str] = None,
    importavendite: Optional[str] = None,
    importarapido: Optional[str] = None,
    config_path: str = "config.ini",
) -> None:
    """
    Aggiorna uno o più parametri cartelle nella riga id=1 della tabella parametri.
    I parametri passati come None vengono ignorati.
    """
    campi: Dict[str, Any] = {}
    if cartellaemesse is not None:
        campi["cartellaemesse"] = cartellaemesse
    if cartellaricevute is not None:
        campi["cartellaricevute"] = cartellaricevute
    if cartellastampa is not None:
        campi["cartellastampa"] = cartellastampa
    if importacquisti is not None:
        campi["importacquisti"] = importacquisti
    if importavendite is not None:
        campi["importavendite"] = importavendite
    if importarapido is not None:
        campi["importarapido"] = importarapido

    if not campi:
        return

    placeholders = ", ".join(f"{k} = ?" for k in campi.keys())
    values = list(campi.values())

    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE parametri SET {placeholders} WHERE id = 1",
            values,
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                "Impossibile aggiornare la tabella 'parametri' (nessuna riga con id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        conn.commit()
    finally:
        conn.close()


# Funzioni di convenienza per aggiornare singoli parametri
def set_cartella_emesse(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella fatture emesse."""
    aggiorna_parametri_cartelle(cartellaemesse=value, config_path=config_path)


def set_cartella_ricevute(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella fatture ricevute."""
    aggiorna_parametri_cartelle(cartellaricevute=value, config_path=config_path)


def set_cartella_stampa(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella stampa."""
    aggiorna_parametri_cartelle(cartellastampa=value, config_path=config_path)


def set_import_acquisti(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella import acquisti."""
    aggiorna_parametri_cartelle(importacquisti=value, config_path=config_path)


def set_import_vendite(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella import vendite."""
    aggiorna_parametri_cartelle(importavendite=value, config_path=config_path)


def set_import_rapido(value: str, config_path: str = "config.ini") -> None:
    """Imposta il percorso della cartella import rapido."""
    aggiorna_parametri_cartelle(importarapido=value, config_path=config_path)

