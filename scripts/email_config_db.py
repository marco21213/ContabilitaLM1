"""
Gestione configurazione email nel database con crittografia della password.
Utilizza cryptography.fernet per crittografare/decrittografare la password.
"""
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import os
import base64

from scripts.parametri_db import _open_connection


def _get_fernet_key_path(config_path: str = "config.ini") -> Path:
    """
    Restituisce il percorso del file contenente la chiave Fernet.
    La chiave viene salvata nella stessa directory del database.
    """
    from scripts.parametri_db import get_db_path
    db_path = Path(get_db_path(config_path))
    # Salva la chiave nella stessa directory del database con nome .email_key
    key_path = db_path.parent / ".email_key"
    return key_path


def _get_or_create_fernet_key(config_path: str = "config.ini") -> bytes:
    """
    Carica la chiave Fernet dal file, o la crea se non esiste.
    Restituisce la chiave come bytes.
    """
    key_path = _get_fernet_key_path(config_path)
    
    if key_path.exists():
        # Carica la chiave esistente
        with open(key_path, 'rb') as f:
            key = f.read()
    else:
        # Genera una nuova chiave e salvala
        key = Fernet.generate_key()
        # Salva con permessi ristretti (solo proprietario può leggere/scrivere)
        with open(key_path, 'wb') as f:
            os.chmod(key_path, 0o600)  # Solo proprietario può leggere/scrivere
            f.write(key)
    
    return key


def _get_fernet(config_path: str = "config.ini") -> Fernet:
    """Restituisce un'istanza Fernet configurata con la chiave."""
    key = _get_or_create_fernet_key(config_path)
    return Fernet(key)


def carica_email_config(config_path: str = "config.ini") -> sqlite3.Row:
    """
    Carica la configurazione email (id = 1) dalla tabella email_config.
    Decrittografa automaticamente la password.
    Restituisce un oggetto sqlite3.Row indicizzabile per nome colonna.
    """
    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM email_config WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                "Nessun record trovato nella tabella 'email_config' (atteso id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        return row
    finally:
        conn.close()


def decripta_password(password_cifrata: str, config_path: str = "config.ini") -> str:
    """
    Decrittografa la password usando Fernet.
    """
    try:
        fernet = _get_fernet(config_path)
        password_bytes = fernet.decrypt(password_cifrata.encode('utf-8'))
        return password_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Errore nella decrittografia della password: {e}")


def cripta_password(password_chiara: str, config_path: str = "config.ini") -> str:
    """
    Crittografa la password usando Fernet.
    Restituisce la password crittografata come stringa.
    """
    try:
        fernet = _get_fernet(config_path)
        password_cifrata = fernet.encrypt(password_chiara.encode('utf-8'))
        return password_cifrata.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Errore nella crittografia della password: {e}")


def get_email_config_decrypted(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Carica la configurazione email e restituisce un dizionario con la password decrittografata.
    Utile per l'uso diretto nelle funzioni di invio email.
    """
    row = carica_email_config(config_path)
    return {
        'id': row['id'],
        'smtp_server': row['smtp_server'],
        'smtp_port': row['smtp_port'],
        'email_mittente': row['email_mittente'],
        'email_password': decripta_password(row['email_password'], config_path),
        'email_destinatario': row['email_destinatario']
    }


def aggiorna_email_config(
    *,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    email_mittente: Optional[str] = None,
    email_password: Optional[str] = None,
    email_destinatario: Optional[str] = None,
    config_path: str = "config.ini",
) -> None:
    """
    Aggiorna uno o più campi nella riga id=1 della tabella email_config.
    La password viene automaticamente crittografata prima del salvataggio.
    I parametri passati come None vengono ignorati.
    """
    campi: Dict[str, Any] = {}
    
    if smtp_server is not None:
        campi["smtp_server"] = smtp_server
    if smtp_port is not None:
        campi["smtp_port"] = int(smtp_port)
    if email_mittente is not None:
        campi["email_mittente"] = email_mittente
    if email_password is not None:
        # Crittografa la password prima di salvarla
        campi["email_password"] = cripta_password(email_password, config_path)
    if email_destinatario is not None:
        campi["email_destinatario"] = email_destinatario

    if not campi:
        return

    placeholders = ", ".join(f"{k} = ?" for k in campi.keys())
    values = list(campi.values())

    conn = _open_connection(config_path)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE email_config SET {placeholders} WHERE id = 1",
            values,
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                "Impossibile aggiornare la tabella 'email_config' (nessuna riga con id = 1). "
                "Assicurati di aver creato e popolato la tabella."
            )
        conn.commit()
    finally:
        conn.close()


def get_smtp_server(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce il server SMTP."""
    try:
        row = carica_email_config(config_path)
        return row["smtp_server"] if row["smtp_server"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None


def get_smtp_port(config_path: str = "config.ini") -> Optional[int]:
    """Restituisce la porta SMTP."""
    try:
        row = carica_email_config(config_path)
        return int(row["smtp_port"]) if row["smtp_port"] else None
    except (KeyError, RuntimeError, ValueError):
        return None
    except Exception:
        return None


def get_email_mittente(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce l'email mittente."""
    try:
        row = carica_email_config(config_path)
        return row["email_mittente"] if row["email_mittente"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None


def get_email_password_decrypted(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce la password email decrittografata."""
    try:
        row = carica_email_config(config_path)
        if row["email_password"]:
            return decripta_password(row["email_password"], config_path)
        return None
    except (KeyError, RuntimeError, ValueError):
        return None
    except Exception:
        return None


def get_email_destinatario(config_path: str = "config.ini") -> Optional[str]:
    """Restituisce l'email destinatario di default."""
    try:
        row = carica_email_config(config_path)
        return row["email_destinatario"] if row["email_destinatario"] else None
    except (KeyError, RuntimeError):
        return None
    except Exception:
        return None
