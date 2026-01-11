"""
Modulo per la gestione dei backup incrementali del database con supporto Dropbox.
"""
import os
import shutil
import sqlite3
import configparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import opzionale per Dropbox
try:
    import dropbox
    from dropbox.exceptions import AuthError, ApiError, BadInputError
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False
    logger.warning("Dropbox SDK non installato. Installare con: pip install dropbox")


class BackupManager:
    """Gestisce i backup incrementali del database con supporto Dropbox."""
    
    def __init__(self, config_path: str = "config.ini"):
        """Inizializza il BackupManager leggendo la configurazione."""
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # Leggi configurazione backup
        self.db_path = self._get_db_path()
        self.backup_folder = self._get_backup_folder()
        self.keep_days = int(self.config.get('Backup', 'giorni_ritenzione', fallback='30'))
        
        # Configurazione Dropbox
        self.dropbox_enabled = self.config.getboolean('Backup', 'dropbox_enabled', fallback=False)
        self.dropbox_token = self.config.get('Backup', 'dropbox_token', fallback='')
        self.dropbox_folder = self.config.get('Backup', 'dropbox_folder', fallback='/ContabilitaLM1/backup')
        
        # Tipo di backup
        self.backup_on_close = self.config.getboolean('Backup', 'backup_on_close', fallback=False)
        self.backup_scheduled = self.config.getboolean('Backup', 'backup_scheduled', fallback=False)
        self.backup_schedule_time = self.config.get('Backup', 'backup_schedule_time', fallback='02:00')
        
        self.dbx = None
        if self.dropbox_enabled and DROPBOX_AVAILABLE and self.dropbox_token:
            try:
                self.dbx = dropbox.Dropbox(self.dropbox_token)
                # Test connessione
                self.dbx.users_get_current_account()
                logger.info("Connessione Dropbox stabilita")
            except Exception as e:
                logger.error(f"Errore connessione Dropbox: {e}")
                self.dbx = None
    
    def _get_db_path(self) -> str:
        """Ottiene il percorso del database da config.ini."""
        if "Autenticazione" in self.config and "percorso_database" in self.config["Autenticazione"]:
            return self.config.get("Autenticazione", "percorso_database")
        return ""
    
    def _get_backup_folder(self) -> str:
        """Ottiene la cartella di backup locale."""
        folder = self.config.get('Backup', 'cartella', fallback='')
        if not folder:
            # Fallback: cartella backup nella stessa directory del database
            if self.db_path:
                db_dir = os.path.dirname(self.db_path)
                folder = os.path.join(db_dir, 'backup')
        return folder
    
    def create_backup_filename(self) -> str:
        """Crea il nome del file di backup con timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        db_name = Path(self.db_path).stem if self.db_path else 'database'
        return f"{db_name}_{timestamp}.db"
    
    def create_backup(self, upload_to_dropbox: bool = True) -> Tuple[bool, str, Optional[str]]:
        """
        Crea un backup incrementale del database.
        
        Returns:
            Tuple[bool, str, Optional[str]]: (successo, percorso_file_locale, percorso_dropbox)
        """
        if not self.db_path or not os.path.exists(self.db_path):
            logger.error(f"Database non trovato: {self.db_path}")
            return False, "", None
        
        try:
            # Crea la cartella backup locale se non esiste
            if self.backup_folder:
                os.makedirs(self.backup_folder, exist_ok=True)
            
            # Nome file backup
            backup_filename = self.create_backup_filename()
            local_backup_path = os.path.join(self.backup_folder, backup_filename) if self.backup_folder else None
            
            # Crea backup locale
            if local_backup_path:
                shutil.copy2(self.db_path, local_backup_path)
                logger.info(f"Backup locale creato: {local_backup_path}")
            
            # Upload su Dropbox se abilitato
            dropbox_path = None
            if upload_to_dropbox and self.dropbox_enabled and self.dbx:
                try:
                    dropbox_path = self.upload_to_dropbox(local_backup_path or self.db_path, backup_filename)
                    logger.info(f"Backup caricato su Dropbox: {dropbox_path}")
                except Exception as e:
                    error_msg = str(e)
                    # Verifica se è un errore di permessi/scope
                    if 'files.content.write' in error_msg or 'scope' in error_msg.lower() or 'permitted' in error_msg.lower():
                        logger.error(f"Errore permessi Dropbox: L'app non ha lo scope 'files.content.write' abilitato. "
                                   f"Vai su https://www.dropbox.com/developers/apps e abilita lo scope nella sezione Permissions.")
                    else:
                        logger.error(f"Errore upload Dropbox: {e}")
                    # Non fallisce il backup se l'upload Dropbox fallisce
            
            return True, local_backup_path or "", dropbox_path
            
        except Exception as e:
            logger.error(f"Errore nella creazione del backup: {e}")
            return False, "", None
    
    def upload_to_dropbox(self, local_file_path: str, remote_filename: str) -> str:
        """
        Carica un file su Dropbox.
        
        Args:
            local_file_path: Percorso del file locale
            remote_filename: Nome del file su Dropbox
            
        Returns:
            Percorso completo su Dropbox
            
        Raises:
            Exception: Se Dropbox non è configurato o se ci sono errori di permessi
        """
        if not self.dbx:
            raise Exception("Dropbox non configurato")
        
        # Percorso completo su Dropbox
        dropbox_path = f"{self.dropbox_folder.rstrip('/')}/{remote_filename}"
        
        # Leggi il file e caricalo
        with open(local_file_path, 'rb') as f:
            file_data = f.read()
        
        # Upload con gestione errori specifici
        try:
            self.dbx.files_upload(
                file_data,
                dropbox_path,
                mode=dropbox.files.WriteMode.overwrite,
                mute=True
            )
        except BadInputError as e:
            error_msg = str(e)
            if 'files.content.write' in error_msg or 'scope' in error_msg.lower():
                raise Exception(
                    f"Errore permessi Dropbox: L'app non ha lo scope 'files.content.write' abilitato.\n\n"
                    f"Per risolvere:\n"
                    f"1. Vai su https://www.dropbox.com/developers/apps\n"
                    f"2. Seleziona la tua app\n"
                    f"3. Vai alla scheda 'Permissions'\n"
                    f"4. Abilita lo scope 'files.content.write'\n"
                    f"5. Salva le modifiche\n"
                    f"6. Genera un nuovo access token se necessario"
                ) from e
            raise
        except AuthError as e:
            raise Exception(f"Errore autenticazione Dropbox: Token non valido o scaduto. Genera un nuovo token.") from e
        except Exception as e:
            raise Exception(f"Errore upload Dropbox: {e}") from e
        
        return dropbox_path
    
    def cleanup_old_backups(self, days: Optional[int] = None) -> Tuple[int, int]:
        """
        Rimuove i backup più vecchi del numero di giorni specificato.
        
        Returns:
            Tuple[int, int]: (backup_locali_rimossi, backup_dropbox_rimossi)
        """
        if days is None:
            days = self.keep_days
        
        cutoff_date = datetime.now() - timedelta(days=days)
        local_removed = 0
        dropbox_removed = 0
        
        # Pulisci backup locali
        if self.backup_folder and os.path.exists(self.backup_folder):
            for filename in os.listdir(self.backup_folder):
                if filename.endswith('.db'):
                    file_path = os.path.join(self.backup_folder, filename)
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            local_removed += 1
                            logger.info(f"Rimosso backup locale vecchio: {filename}")
                    except Exception as e:
                        logger.error(f"Errore rimozione backup {filename}: {e}")
        
        # Pulisci backup Dropbox
        if self.dropbox_enabled and self.dbx:
            try:
                dropbox_path = self.dropbox_folder.rstrip('/')
                result = self.dbx.files_list_folder(dropbox_path)
                
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith('.db'):
                        # Estrai data dal nome file (formato: database_YYYY-MM-DD_HH-MM-SS.db)
                        try:
                            # Prova a estrarre la data dal nome
                            parts = entry.name.split('_')
                            if len(parts) >= 3:
                                date_str = f"{parts[-3]}_{parts[-2]}_{parts[-1].replace('.db', '')}"
                                file_date = datetime.strptime(date_str, '%Y-%m-%d_%H-%M-%S')
                                
                                if file_date < cutoff_date:
                                    file_path = f"{dropbox_path}/{entry.name}"
                                    self.dbx.files_delete_v2(file_path)
                                    dropbox_removed += 1
                                    logger.info(f"Rimosso backup Dropbox vecchio: {entry.name}")
                        except Exception as e:
                            logger.warning(f"Impossibile determinare data per {entry.name}: {e}")
                            
            except Exception as e:
                logger.error(f"Errore pulizia backup Dropbox: {e}")
        
        return local_removed, dropbox_removed
    
    def list_backups(self) -> Tuple[list, list]:
        """
        Lista tutti i backup disponibili (locali e Dropbox).
        
        Returns:
            Tuple[list, list]: (backup_locali, backup_dropbox)
        """
        local_backups = []
        dropbox_backups = []
        
        # Lista backup locali
        if self.backup_folder and os.path.exists(self.backup_folder):
            for filename in os.listdir(self.backup_folder):
                if filename.endswith('.db'):
                    file_path = os.path.join(self.backup_folder, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    file_size = os.path.getsize(file_path)
                    local_backups.append({
                        'name': filename,
                        'path': file_path,
                        'date': file_time,
                        'size': file_size
                    })
        
        # Lista backup Dropbox
        if self.dropbox_enabled and self.dbx:
            try:
                dropbox_path = self.dropbox_folder.rstrip('/')
                result = self.dbx.files_list_folder(dropbox_path)
                
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith('.db'):
                        dropbox_backups.append({
                            'name': entry.name,
                            'path': f"{dropbox_path}/{entry.name}",
                            'date': entry.client_modified,
                            'size': entry.size
                        })
            except Exception as e:
                logger.error(f"Errore lista backup Dropbox: {e}")
        
        # Ordina per data (più recenti prima)
        local_backups.sort(key=lambda x: x['date'], reverse=True)
        dropbox_backups.sort(key=lambda x: x['date'], reverse=True)
        
        return local_backups, dropbox_backups


def create_backup(config_path: str = "config.ini", upload_to_dropbox: bool = True) -> Tuple[bool, str]:
    """
    Funzione di convenienza per creare un backup.
    
    Returns:
        Tuple[bool, str]: (successo, messaggio)
    """
    try:
        manager = BackupManager(config_path)
        success, local_path, dropbox_path = manager.create_backup(upload_to_dropbox)
        
        if success:
            msg = f"Backup creato con successo!\nLocale: {local_path}"
            if dropbox_path:
                msg += f"\nDropbox: {dropbox_path}"
            return True, msg
        else:
            return False, "Errore nella creazione del backup"
    except Exception as e:
        logger.error(f"Errore backup: {e}")
        return False, f"Errore: {e}"
