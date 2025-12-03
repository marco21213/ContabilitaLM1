"""
Modulo per gestire i percorsi delle risorse in modo compatibile
sia per sviluppo che per eseguibili compilati (EXE).
"""

import os
import sys


def get_resource_path(relative_path):
    """
    Ottiene il percorso assoluto di una risorsa.
    
    Funziona sia in modalità sviluppo che quando compilato in EXE con PyInstaller.
    PyInstaller crea una cartella temporanea e memorizza il percorso in _MEIPASS.
    
    Args:
        relative_path: Percorso relativo della risorsa (es. "assets/icon/logo.png")
    
    Returns:
        Percorso assoluto della risorsa
    """
    try:
        # PyInstaller crea una cartella temporanea e memorizza il percorso in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Modalità sviluppo: usa il percorso corrente del progetto
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def get_icon_path(icon_name):
    """
    Ottiene il percorso completo di un'icona.
    
    Args:
        icon_name: Nome dell'icona (es. "logo.png" o "salva.png")
    
    Returns:
        Percorso completo dell'icona
    """
    return get_resource_path(os.path.join("assets", "icon", icon_name))


def get_config_path():
    """
    Ottiene il percorso del file di configurazione.
    
    Returns:
        Percorso del file config.ini
    """
    return get_resource_path("config.ini")


def resource_exists(relative_path):
    """
    Verifica se una risorsa esiste.
    
    Args:
        relative_path: Percorso relativo della risorsa
    
    Returns:
        True se la risorsa esiste, False altrimenti
    """
    path = get_resource_path(relative_path)
    return os.path.exists(path)

