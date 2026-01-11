import sys
import os
import sqlite3
import configparser
import hashlib
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), 'gui'))

from gui.main_window import MainWindow

class GitUpdatesNotifier:
    """Notifica la disponibilità di aggiornamenti da GitHub"""
    
    def __init__(self, repo_path=None):
        self.repo_path = repo_path or os.path.dirname(os.path.abspath(__file__))
    
    def check_updates_available(self):
        """Controlla se ci sono aggiornamenti disponibili"""
        try:
            # Fetch dal repository remoto (senza modificare i file)
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10
            )
            
            # Controlla se ci sono commit non scaricati
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..origin/main"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                commits_behind = int(result.stdout.strip())
                return commits_behind > 0, commits_behind
            
            return False, 0
            
        except Exception as e:
            print(f"[WARNING] Errore nella verifica degli aggiornamenti: {e}")
            return False, 0

def show_login_window():
    """Mostra una finestra di benvenuto semplificata"""
    
    # Controlla se ci sono aggiornamenti disponibili
    notifier = GitUpdatesNotifier()
    updates_available, count = notifier.check_updates_available()
    
    root = tk.Tk()
    root.title("Contabilità 3b")
    root.geometry("300x250" if updates_available else "300x200")
    root.resizable(False, False)
    
    # Centra la finestra
    root.eval('tk::PlaceWindow . center')
    
    # Frame principale
    main_frame = tk.Frame(root)
    main_frame.pack(expand=True, fill='both', padx=20, pady=20)
    
    # Titolo
    title_label = tk.Label(main_frame, text="Benvenuto", font=("Arial", 16, "bold"))
    title_label.pack(pady=(20, 30))
    
    # Messaggio di aggiornamenti disponibili
    if updates_available:
        update_label = tk.Label(
            main_frame,
            text=f"⚠️ Sono disponibili {count} aggiornamento/i",
            font=("Arial", 10, "bold"),
            fg="#ff9800"
        )
        update_label.pack(pady=(0, 10))
        
        info_label = tk.Label(
            main_frame,
            text="Esegui: git pull origin main",
            font=("Arial", 9),
            fg="#666"
        )
        info_label.pack(pady=(0, 15))
    
    # Messaggio di benvenuto
    welcome_label = tk.Label(main_frame, text="Accesso diretto al sistema", 
                           font=("Arial", 10), fg="green")
    welcome_label.pack(pady=(0, 30))
    
    def start_app():
        root.destroy()
        start_main_application()
    
    def exit_application():
        if messagebox.askyesno("Conferma", "Sei sicuro di voler uscire?"):
            root.destroy()
    
    # Frame per i pulsanti
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill='x', pady=(20, 0))
    
    # Pulsante di accesso
    access_btn = tk.Button(button_frame, text="Accedi", command=start_app, 
                         bg="#007acc", fg="white", font=("Arial", 10, "bold"),
                         width=12, height=1)
    access_btn.pack(side='left', padx=(0, 10))
    
    # Pulsante Esci
    exit_btn = tk.Button(button_frame, text="Esci", command=exit_application,
                        bg="#dc3545", fg="white", font=("Arial", 10),
                        width=8, height=1)
    exit_btn.pack(side='right')
    
    # Info versione
    version_label = tk.Label(main_frame, text="Contabilità 3B v1.0", 
                            font=("Arial", 8), fg="gray")
    version_label.pack(side='bottom', pady=(20, 0))
    
    # Avvia automaticamente dopo breve attesa
    root.after(1000, start_app)
    
    root.mainloop()

def start_main_application():
    """Avvia l'applicazione principale"""
    # Avvia lo scheduler per backup giornalieri
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        from scripts.backup_scheduler import start_backup_scheduler
        start_backup_scheduler(config_path)
    except Exception as e:
        print(f"Errore avvio scheduler backup: {e}")
    
    root = tk.Tk()
    app = MainWindow(root)
    
    # Configura backup alla chiusura
    def on_closing():
        try:
            import configparser
            config = configparser.ConfigParser()
            config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
                backup_on_close = config.getboolean('Backup', 'backup_on_close', fallback=False)
                
                if backup_on_close:
                    from scripts.backup_manager import BackupManager
                    manager = BackupManager(config_path)
                    dropbox_enabled = config.getboolean('Backup', 'dropbox_enabled', fallback=False)
                    success, local_path, dropbox_path = manager.create_backup(upload_to_dropbox=dropbox_enabled)
                    if success:
                        msg = f"Backup alla chiusura completato: {local_path}"
                        if dropbox_enabled and not dropbox_path:
                            msg += "\n⚠️ Backup Dropbox non eseguito - verifica configurazione e permessi"
                        print(msg)
                    else:
                        print("Errore nel backup alla chiusura")
        except Exception as e:
            print(f"Errore backup alla chiusura: {e}")
        
        # Ferma lo scheduler
        try:
            from scripts.backup_scheduler import stop_backup_scheduler
            stop_backup_scheduler()
        except Exception as e:
            print(f"Errore stop scheduler: {e}")
        
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    show_login_window()