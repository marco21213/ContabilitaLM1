"""
Scheduler per backup automatici giornalieri.
"""
import threading
import schedule
import time
import logging
import configparser
import os
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from scripts.backup_manager import BackupManager
except ImportError:
    logger.error("Impossibile importare BackupManager")
    BackupManager = None

# Import per configurazione backup dal database
try:
    from scripts.backup_config_db import (
        get_backup_scheduled,
        get_backup_schedule_time,
        get_backup_dropbox_enabled,
    )
except ImportError:
    logger.warning("Impossibile importare backup_config_db, uso config.ini come fallback")
    get_backup_scheduled = None


class BackupScheduler:
    """Gestisce lo scheduling dei backup automatici."""
    
    def __init__(self, config_path: str = "config.ini"):
        """Inizializza lo scheduler."""
        self.config_path = config_path
        self.running = False
        self.thread = None
        self.config = configparser.ConfigParser()
        if os.path.exists(config_path):
            self.config.read(config_path, encoding='utf-8')
    
    def start(self):
        """Avvia lo scheduler in un thread separato."""
        if self.running:
            logger.warning("Scheduler già in esecuzione")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Backup scheduler avviato")
    
    def stop(self):
        """Ferma lo scheduler."""
        self.running = False
        schedule.clear()
        logger.info("Backup scheduler fermato")
    
    def _run_scheduler(self):
        """Esegue lo scheduler in un loop."""
        while self.running:
            try:
                # Verifica se il backup schedulato è abilitato (dal database o config.ini)
                try:
                    if get_backup_scheduled:
                        backup_scheduled = get_backup_scheduled(self.config_path)
                        schedule_time = get_backup_schedule_time(self.config_path) or '02:00'
                    else:
                        raise ImportError("backup_config_db non disponibile")
                except Exception as e:
                    logger.debug(f"Errore nel caricamento configurazione dal database, uso config.ini: {e}")
                    # Fallback a config.ini
                    if os.path.exists(self.config_path):
                        self.config.read(self.config_path, encoding='utf-8')
                    backup_scheduled = self.config.getboolean('Backup', 'backup_scheduled', fallback=False)
                    schedule_time = self.config.get('Backup', 'backup_schedule_time', fallback='02:00')
                
                if backup_scheduled:
                    # Rimuovi job esistenti
                    schedule.clear()
                    
                    # Aggiungi nuovo job
                    schedule.every().day.at(schedule_time).do(self._execute_scheduled_backup)
                    logger.info(f"Backup schedulato alle {schedule_time}")
                else:
                    schedule.clear()
                
                # Esegui job in attesa
                schedule.run_pending()
                
            except Exception as e:
                logger.error(f"Errore nello scheduler: {e}")
            
            # Attendi 60 secondi prima di ricontrollare
            time.sleep(60)
    
    def _execute_scheduled_backup(self):
        """Esegue un backup schedulato."""
        try:
            logger.info("Esecuzione backup schedulato...")
            
            if not BackupManager:
                logger.error("BackupManager non disponibile")
                return
            
            manager = BackupManager(self.config_path)
            # Usa la configurazione già caricata nel BackupManager
            dropbox_enabled = manager.dropbox_enabled
            
            success, local_path, dropbox_path = manager.create_backup(upload_to_dropbox=dropbox_enabled)
            
            if success:
                logger.info(f"Backup schedulato completato: {local_path}")
                # Esegui pulizia backup vecchi
                manager.cleanup_old_backups()
            else:
                logger.error("Errore nel backup schedulato")
                
        except Exception as e:
            logger.error(f"Errore nell'esecuzione backup schedulato: {e}")


# Istanza globale dello scheduler
_scheduler_instance = None


def start_backup_scheduler(config_path: str = "config.ini"):
    """Avvia lo scheduler globale."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackupScheduler(config_path)
        _scheduler_instance.start()
    return _scheduler_instance


def stop_backup_scheduler():
    """Ferma lo scheduler globale."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None
