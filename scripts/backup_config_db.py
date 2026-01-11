"""
Gestione configurazione backup nel database.
"""
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

from scripts.parametri_db import _open_connection


def carica_backup_config(config_path: str = "config.ini") -> sqlite3.Row:
    """
    Carica la configurazione backup (id = 1) dalla tabella backup_config.
    Restituisce un oggetto sqlite3.Row indicizzabile per nome colonna.
    """
    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM backup_config WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                "Nessun record trovato nella tabella 'backup_config' (atteso id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        return row
    finally:
        conn.close()


def get_backup_config_dict(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Carica la configurazione backup e restituisce un dizionario con valori convertiti.
    Converte gli INTEGER (0/1) in booleani Python.
    """
    row = carica_backup_config(config_path)
    return {
        'id': row['id'],
        'cartella': row['cartella'],
        'giorni_ritenzione': row['giorni_ritenzione'],
        'automatico': bool(row['automatico']),
        'dropbox_enabled': bool(row['dropbox_enabled']),
        'dropbox_token': row['dropbox_token'] if row['dropbox_token'] else '',
        'dropbox_folder': row['dropbox_folder'] if row['dropbox_folder'] else '',
        'backup_on_close': bool(row['backup_on_close']),
        'backup_scheduled': bool(row['backup_scheduled']),
        'backup_schedule_time': row['backup_schedule_time'] if row['backup_schedule_time'] else '02:00'
    }


def aggiorna_backup_config(
    *,
    cartella: Optional[str] = None,
    giorni_ritenzione: Optional[int] = None,
    automatico: Optional[bool] = None,
    dropbox_enabled: Optional[bool] = None,
    dropbox_token: Optional[str] = None,
    dropbox_folder: Optional[str] = None,
    backup_on_close: Optional[bool] = None,
    backup_scheduled: Optional[bool] = None,
    backup_schedule_time: Optional[str] = None,
    config_path: str = "config.ini",
) -> None:
    """
    Aggiorna uno o più campi nella riga id=1 della tabella backup_config.
    I booleani vengono convertiti in INTEGER (0/1).
    I parametri passati come None vengono ignorati.
    """
    campi: Dict[str, Any] = {}
    
    if cartella is not None:
        campi["cartella"] = cartella
    if giorni_ritenzione is not None:
        campi["giorni_ritenzione"] = int(giorni_ritenzione)
    if automatico is not None:
        campi["automatico"] = 1 if automatico else 0
    if dropbox_enabled is not None:
        campi["dropbox_enabled"] = 1 if dropbox_enabled else 0
    if dropbox_token is not None:
        campi["dropbox_token"] = dropbox_token
    if dropbox_folder is not None:
        campi["dropbox_folder"] = dropbox_folder
    if backup_on_close is not None:
        campi["backup_on_close"] = 1 if backup_on_close else 0
    if backup_scheduled is not None:
        campi["backup_scheduled"] = 1 if backup_scheduled else 0
    if backup_schedule_time is not None:
        campi["backup_schedule_time"] = backup_schedule_time

    if not campi:
        return

    placeholders = ", ".join(f"{k} = ?" for k in campi.keys())
    values = list(campi.values())

    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE backup_config SET {placeholders} WHERE id = 1",
            values,
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                "Impossibile aggiornare la tabella 'backup_config' (nessuna riga con id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        conn.commit()
    finally:
        conn.close()


# Funzioni helper per accedere ai singoli campi
def get_backup_cartella(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce la cartella di backup."""
    try:
        row = carica_backup_config(config_path)
        return row["cartella"] if row["cartella"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None


def get_backup_giorni_ritenzione(config_path: str = "config.ini") -> Optional[int]:
    """Restituisce i giorni di ritenzione."""
    try:
        row = carica_backup_config(config_path)
        return int(row["giorni_ritenzione"]) if row["giorni_ritenzione"] else None
    except (KeyError, RuntimeError, ValueError):
        return None
    except Exception:
        return None


def get_backup_automatico(config_path: str = "config.ini") -> bool:
    """Restituisce se il backup automatico è abilitato."""
    try:
        row = carica_backup_config(config_path)
        return bool(row["automatico"])
    except (KeyError, RuntimeError):
        return False
    except Exception:
        return False


def get_backup_dropbox_enabled(config_path: str = "config.ini") -> bool:
    """Restituisce se Dropbox è abilitato."""
    try:
        row = carica_backup_config(config_path)
        return bool(row["dropbox_enabled"])
    except (KeyError, RuntimeError):
        return False
    except Exception:
        return False


def get_backup_dropbox_token(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il token Dropbox."""
    try:
        row = carica_backup_config(config_path)
        return row["dropbox_token"] if row["dropbox_token"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None


def get_backup_dropbox_folder(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce la cartella Dropbox."""
    try:
        row = carica_backup_config(config_path)
        return row["dropbox_folder"] if row["dropbox_folder"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None


def get_backup_on_close(config_path: str = "config.ini") -> bool:
    """Restituisce se il backup alla chiusura è abilitato."""
    try:
        row = carica_backup_config(config_path)
        return bool(row["backup_on_close"])
    except (KeyError, RuntimeError):
        return False
    except Exception:
        return False


def get_backup_scheduled(config_path: str = "config.ini") -> bool:
    """Restituisce se il backup schedulato è abilitato."""
    try:
        row = carica_backup_config(config_path)
        return bool(row["backup_scheduled"])
    except (KeyError, RuntimeError):
        return False
    except Exception:
        return False


def get_backup_schedule_time(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce l'orario del backup schedulato."""
    try:
        row = carica_backup_config(config_path)
        return row["backup_schedule_time"] if row["backup_schedule_time"] else '02:00'
    except (KeyError, RuntimeError):
        return '02:00'
    except Exception:
        return '02:00'
