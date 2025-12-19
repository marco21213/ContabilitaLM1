import configparser
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any


def get_db_path(config_path: str = "config.ini") -> str:
    """
    Legge il percorso del database dalla sezione [Autenticazione] di config.ini.
    Resta il solo utilizzo di config.ini per la connessione al database.
    """
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    if "Autenticazione" not in config or "percorso_database" not in config["Autenticazione"]:
        # Fallback minimale: database nella cartella del progetto
        return str(Path("database.db").resolve())

    db_path = config.get("Autenticazione", "percorso_database", fallback="database.db")
    return db_path


def _open_connection(config_path: str = "config.ini") -> sqlite3.Connection:
    """Restituisce una connessione SQLite aperta usando il percorso del DB da config.ini."""
    db_path = get_db_path(config_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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



