import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any
import configparser
import os
import sys
import logging

# Aggiungi il percorso alla root del progetto per importare scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.parametri_db import (
    carica_parametri,
    aggiorna_parametri,
    aggiorna_credenziali as aggiorna_credenziali_db,
    get_cartella_emesse,
    get_cartella_ricevute,
    get_cartella_stampa,
    get_import_acquisti,
    get_import_vendite,
    get_import_rapido,
    set_cartella_emesse,
    set_cartella_ricevute,
    set_cartella_stampa,
    set_import_acquisti,
    set_import_vendite,
    set_import_rapido,
)

logger = logging.getLogger(__name__)

class ConfigWindow:
    """Finestra di configurazione dell'applicazione"""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Configurazione")
        self.window.geometry("800x650")
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centra la finestra
        self.center_window()
        
        # Determina il percorso assoluto del file config.ini
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.config_file = os.path.join(project_root, "config.ini")
        
        self.config = configparser.ConfigParser()
        self.create_widgets()
        self.load_settings()
        
    def center_window(self) -> None:
        """Centra la finestra rispetto alla finestra principale"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self) -> None:
        """Crea i widget della finestra di configurazione"""
        # Frame principale
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Titolo
        ttk.Label(
            main_frame, 
            text="Configurazione Parametri", 
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))
        
        # Notebook per le diverse sezioni
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # Scheda Parametri (file config.ini)
        params_frame = ttk.Frame(notebook, padding="10")
        notebook.add(params_frame, text="Parametri")
        self.create_parameters_tab(params_frame)

        # Scheda Parametri AdE (tabella parametri nel database)
        ade_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ade_frame, text="Parametri AdE")
        self.create_ade_tab(ade_frame)
        
        # Scheda Backup
        backup_frame = ttk.Frame(notebook, padding="10")
        notebook.add(backup_frame, text="Backup")
        self.create_backup_tab(backup_frame)
        
        # Scheda Email
        email_frame = ttk.Frame(notebook, padding="10")
        notebook.add(email_frame, text="Email")
        self.create_email_tab(email_frame)
        
        # Pulsanti di azione
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(20, 0))
        
        ttk.Button(
            button_frame, 
            text="Salva", 
            command=self.save_settings
        ).pack(side='right', padx=5)
        
        ttk.Button(
            button_frame, 
            text="Annulla", 
            command=self.window.destroy
        ).pack(side='right', padx=5)
        
        ttk.Button(
            button_frame, 
            text="Ripristina Default", 
            command=self.restore_defaults
        ).pack(side='left')
    
    def create_parameters_tab(self, parent: ttk.Frame) -> None:
        """Crea la scheda per i parametri principali"""
        # Database
        ttk.Label(parent, text="Percorso Database:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky='w', pady=(0, 5)
        )
        ttk.Label(parent, text="File database SQLite:").grid(row=1, column=0, sticky='w', pady=2)
        
        db_frame = ttk.Frame(parent)
        db_frame.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        
        self.db_entry = ttk.Entry(db_frame, width=40)
        self.db_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            db_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_file(self.db_entry, "Seleziona file database", [("Database files", "*.db *.sqlite")])
        ).pack(side='right', padx=(5, 0))
        
        # Separatore
        ttk.Separator(parent, orient='horizontal').grid(
            row=2, column=0, columnspan=2, sticky='ew', pady=15
        )
        
        # Cartella Fatture Vendita
        ttk.Label(parent, text="Cartelle Fatture:", font=("Arial", 10, "bold")).grid(
            row=3, column=0, sticky='w', pady=(0, 5)
        )
        ttk.Label(parent, text="Fatture Vendita:").grid(row=4, column=0, sticky='w', pady=2)
        
        vendita_frame = ttk.Frame(parent)
        vendita_frame.grid(row=4, column=1, padx=5, pady=2, sticky='ew')
        
        self.vendita_entry = ttk.Entry(vendita_frame, width=40)
        self.vendita_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            vendita_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.vendita_entry, "Seleziona cartella fatture vendita")
        ).pack(side='right', padx=(5, 0))
        
        # Cartella Fatture Acquisto
        ttk.Label(parent, text="Fatture Acquisto:").grid(row=5, column=0, sticky='w', pady=2)
        
        acquisto_frame = ttk.Frame(parent)
        acquisto_frame.grid(row=5, column=1, padx=5, pady=2, sticky='ew')
        
        self.acquisto_entry = ttk.Entry(acquisto_frame, width=40)
        self.acquisto_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            acquisto_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.acquisto_entry, "Seleziona cartella fatture acquisto")
        ).pack(side='right', padx=(5, 0))
        
        # Cartella Fatture Stampa
        ttk.Label(parent, text="Fatture Stampa:").grid(row=6, column=0, sticky='w', pady=2)
        
        stampa_frame = ttk.Frame(parent)
        stampa_frame.grid(row=6, column=1, padx=5, pady=2, sticky='ew')
        
        self.stampa_entry = ttk.Entry(stampa_frame, width=40)
        self.stampa_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            stampa_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.stampa_entry, "Seleziona cartella fatture stampa")
        ).pack(side='right', padx=(5, 0))
        
        # Separatore
        ttk.Separator(parent, orient='horizontal').grid(
            row=7, column=0, columnspan=2, sticky='ew', pady=15
        )
        
        # Cartelle Import
        ttk.Label(parent, text="Cartelle Import:", font=("Arial", 10, "bold")).grid(
            row=8, column=0, sticky='w', pady=(0, 5)
        )
        
        # Import Acquisti
        ttk.Label(parent, text="Import Acquisti:").grid(row=9, column=0, sticky='w', pady=2)
        
        import_acquisti_frame = ttk.Frame(parent)
        import_acquisti_frame.grid(row=9, column=1, padx=5, pady=2, sticky='ew')
        
        self.import_acquisti_entry = ttk.Entry(import_acquisti_frame, width=40)
        self.import_acquisti_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            import_acquisti_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.import_acquisti_entry, "Seleziona cartella import acquisti")
        ).pack(side='right', padx=(5, 0))
        
        # Import Vendite
        ttk.Label(parent, text="Import Vendite:").grid(row=10, column=0, sticky='w', pady=2)
        
        import_vendite_frame = ttk.Frame(parent)
        import_vendite_frame.grid(row=10, column=1, padx=5, pady=2, sticky='ew')
        
        self.import_vendite_entry = ttk.Entry(import_vendite_frame, width=40)
        self.import_vendite_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            import_vendite_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.import_vendite_entry, "Seleziona cartella import vendite")
        ).pack(side='right', padx=(5, 0))
        
        # Import Rapido
        ttk.Label(parent, text="Import Rapido:").grid(row=11, column=0, sticky='w', pady=2)
        
        import_rapido_frame = ttk.Frame(parent)
        import_rapido_frame.grid(row=11, column=1, padx=5, pady=2, sticky='ew')
        
        self.import_rapido_entry = ttk.Entry(import_rapido_frame, width=40)
        self.import_rapido_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            import_rapido_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.import_rapido_entry, "Seleziona cartella import rapido")
        ).pack(side='right', padx=(5, 0))
        
        parent.columnconfigure(1, weight=1)

    def create_ade_tab(self, parent: ttk.Frame) -> None:
        """Crea la scheda per i parametri salvati nella tabella 'parametri' del database (AdE)."""
        row = 0

        ttk.Label(parent, text="Credenziali AdE", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(parent, text="Codice fiscale:").grid(row=row, column=0, sticky="w", pady=2)
        self.cf_entry = ttk.Entry(parent, width=30)
        self.cf_entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        row += 1

        ttk.Label(parent, text="PIN:").grid(row=row, column=0, sticky="w", pady=2)
        self.pin_entry = ttk.Entry(parent, width=30)
        self.pin_entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        row += 1

        ttk.Label(parent, text="Password:").grid(row=row, column=0, sticky="w", pady=2)
        self.pwd_entry = ttk.Entry(parent, width=30, show="*")
        self.pwd_entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        row += 1

        ttk.Separator(parent, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Label(parent, text="Parametri ricerca/download", font=("Arial", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        row += 1

        ttk.Label(parent, text="P.IVA delega diretta:").grid(row=row, column=0, sticky="w", pady=2)
        self.piva_entry = ttk.Entry(parent, width=30)
        self.piva_entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        row += 1

        ttk.Label(parent, text="Dal (ddmmyyyy):").grid(row=row, column=0, sticky="w", pady=2)
        self.dal_entry = ttk.Entry(parent, width=15)
        self.dal_entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
        row += 1

        ttk.Label(parent, text="Al (ddmmyyyy):").grid(row=row, column=0, sticky="w", pady=2)
        self.al_entry = ttk.Entry(parent, width=15)
        self.al_entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
        row += 1

        ttk.Label(parent, text="Tipo data (0/1/2):").grid(row=row, column=0, sticky="w", pady=2)
        self.tipo_entry = ttk.Entry(parent, width=5)
        self.tipo_entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
        row += 1

        ttk.Label(parent, text="Vendite/Acquisti (V/A):").grid(row=row, column=0, sticky="w", pady=2)
        self.venoacq_entry = ttk.Entry(parent, width=5)
        self.venoacq_entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
        row += 1

        ttk.Label(parent, text="Ultimo aggiornamento (dd/mm/yyyy):").grid(
            row=row, column=0, sticky="w", pady=2
        )
        self.agg_entry = ttk.Entry(parent, width=15)
        self.agg_entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
        row += 1

        parent.columnconfigure(1, weight=1)
    
    def create_backup_tab(self, parent: ttk.Frame) -> None:
        """Crea la scheda per le impostazioni di backup"""
        # Frame scrollabile per contenere tutte le opzioni
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        row = 0
        
        # === BACKUP LOCALE ===
        ttk.Label(scrollable_frame, text="Backup Locale", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(10, 5)
        )
        row += 1
        
        # Cartella backup locale
        ttk.Label(scrollable_frame, text="Cartella backup locale:").grid(row=row, column=0, sticky='w', pady=5)
        backup_frame = ttk.Frame(scrollable_frame)
        backup_frame.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
        self.backup_folder = ttk.Entry(backup_frame, width=40)
        self.backup_folder.pack(side='left', fill='x', expand=True)
        ttk.Button(
            backup_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.backup_folder, "Seleziona cartella backup")
        ).pack(side='right', padx=(5, 0))
        row += 1
        
        # Mantieni backup per
        ttk.Label(scrollable_frame, text="Mantieni backup per (giorni):").grid(row=row, column=0, sticky='w', pady=5)
        self.keep_backup_days = ttk.Spinbox(scrollable_frame, from_=1, to=365, width=5)
        self.keep_backup_days.grid(row=row, column=1, padx=5, pady=5, sticky='w')
        row += 1
        
        # Separatore
        ttk.Separator(scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=15
        )
        row += 1
        
        # === DROPBOX ===
        ttk.Label(scrollable_frame, text="Backup Cloud (Dropbox)", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(10, 5)
        )
        row += 1
        
        # Abilita Dropbox
        self.dropbox_enabled = tk.BooleanVar()
        ttk.Checkbutton(
            scrollable_frame, 
            text="Abilita backup su Dropbox", 
            variable=self.dropbox_enabled,
            command=self.toggle_dropbox_fields
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
        row += 1
        
        # Dropbox Access Token
        ttk.Label(scrollable_frame, text="Dropbox Access Token:").grid(row=row, column=0, sticky='w', pady=5)
        dropbox_token_frame = ttk.Frame(scrollable_frame)
        dropbox_token_frame.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
        self.dropbox_token = ttk.Entry(dropbox_token_frame, width=40, show='*')
        self.dropbox_token.pack(side='left', fill='x', expand=True)
        ttk.Button(
            dropbox_token_frame,
            text="Info",
            command=self.show_dropbox_info
        ).pack(side='right', padx=(5, 0))
        row += 1
        
        # Dropbox Folder
        ttk.Label(scrollable_frame, text="Cartella Dropbox:").grid(row=row, column=0, sticky='w', pady=5)
        self.dropbox_folder = ttk.Entry(scrollable_frame, width=40)
        self.dropbox_folder.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
        row += 1
        
        # Separatore
        ttk.Separator(scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=15
        )
        row += 1
        
        # === MODALITÀ BACKUP ===
        ttk.Label(scrollable_frame, text="Modalità Backup", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(10, 5)
        )
        row += 1
        
        # Backup alla chiusura
        self.backup_on_close = tk.BooleanVar()
        ttk.Checkbutton(
            scrollable_frame, 
            text="Backup automatico alla chiusura dell'applicazione", 
            variable=self.backup_on_close
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
        row += 1
        
        # Backup schedulato
        self.backup_scheduled = tk.BooleanVar()
        schedule_frame = ttk.Frame(scrollable_frame)
        schedule_frame.grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
        ttk.Checkbutton(
            schedule_frame, 
            text="Backup schedulato giornaliero alle:", 
            variable=self.backup_scheduled
        ).pack(side='left')
        self.backup_schedule_time = ttk.Entry(schedule_frame, width=8)
        self.backup_schedule_time.insert(0, "02:00")
        self.backup_schedule_time.pack(side='left', padx=5)
        ttk.Label(schedule_frame, text="(formato HH:MM)").pack(side='left', padx=5)
        row += 1
        
        # Separatore
        ttk.Separator(scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=15
        )
        row += 1
        
        # === AZIONI ===
        # Esegui backup ora
        ttk.Button(
            scrollable_frame, 
            text="🔄 Esegui Backup Ora", 
            command=self.execute_backup
        ).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1
        
        # Lista backup
        ttk.Button(
            scrollable_frame,
            text="📋 Visualizza Backup",
            command=self.show_backup_list
        ).grid(row=row, column=0, columnspan=2, pady=5)
        
        scrollable_frame.columnconfigure(1, weight=1)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        parent.columnconfigure(0, weight=1)
    
    def create_email_tab(self, parent: ttk.Frame) -> None:
        """Crea la scheda per le impostazioni email"""
        row = 0
        
        ttk.Label(parent, text="Configurazione Email", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 15)
        )
        row += 1
        
        # SMTP Server
        ttk.Label(parent, text="SMTP Server:").grid(row=row, column=0, sticky="w", pady=5)
        self.smtp_server_entry = ttk.Entry(parent, width=40)
        self.smtp_server_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # SMTP Porta
        ttk.Label(parent, text="SMTP Porta:").grid(row=row, column=0, sticky="w", pady=5)
        self.smtp_port_entry = ttk.Entry(parent, width=40)
        self.smtp_port_entry.insert(0, "587")  # Default per TLS
        self.smtp_port_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Email Mittente
        ttk.Label(parent, text="Email Mittente:").grid(row=row, column=0, sticky="w", pady=5)
        self.email_mittente_entry = ttk.Entry(parent, width=40)
        self.email_mittente_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Password Email
        ttk.Label(parent, text="Password Email:").grid(row=row, column=0, sticky="w", pady=5)
        self.email_password_entry = ttk.Entry(parent, width=40, show="*")
        self.email_password_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Email Destinatario Default
        ttk.Label(parent, text="Email Destinatario Default:").grid(row=row, column=0, sticky="w", pady=5)
        self.email_destinatario_entry = ttk.Entry(parent, width=40)
        self.email_destinatario_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Note informative
        info_text = (
            "Nota: Per Gmail, usa 'smtp.gmail.com' porta 587 con TLS.\n"
            "Potrebbe essere necessario generare una 'Password per app' nelle impostazioni Google."
        )
        ttk.Label(parent, text=info_text, font=("Arial", 9), foreground="gray", 
                 wraplength=400, justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(15, 5)
        )
        
        parent.columnconfigure(1, weight=1)
    
    def load_settings(self) -> None:
        """Carica le impostazioni dal file config.ini"""
        try:
            # Leggi il file di configurazione
            self.config.read(self.config_file)
            
            # Sezione Autenticazione
            self.db_entry.insert(0, self.config.get('Autenticazione', 'percorso_database', fallback=''))
            
            # Parametri cartelle dal database
            try:
                cartella_emesse = get_cartella_emesse()
                if cartella_emesse:
                    self.vendita_entry.insert(0, cartella_emesse)
            except Exception as e:
                logger.debug(f"Errore nel caricamento cartella_emesse: {e}")
            
            try:
                cartella_ricevute = get_cartella_ricevute()
                if cartella_ricevute:
                    self.acquisto_entry.insert(0, cartella_ricevute)
            except Exception as e:
                logger.debug(f"Errore nel caricamento cartella_ricevute: {e}")
            
            try:
                cartella_stampa = get_cartella_stampa()
                if cartella_stampa:
                    self.stampa_entry.insert(0, cartella_stampa)
            except Exception as e:
                logger.debug(f"Errore nel caricamento cartella_stampa: {e}")
            
            # Parametri import dal database
            try:
                import_acquisti = get_import_acquisti()
                if import_acquisti:
                    self.import_acquisti_entry.insert(0, import_acquisti)
            except Exception as e:
                logger.debug(f"Errore nel caricamento import_acquisti: {e}")
            
            try:
                import_vendite = get_import_vendite()
                if import_vendite:
                    self.import_vendite_entry.insert(0, import_vendite)
            except Exception as e:
                logger.debug(f"Errore nel caricamento import_vendite: {e}")
            
            try:
                import_rapido = get_import_rapido()
                if import_rapido:
                    self.import_rapido_entry.insert(0, import_rapido)
            except Exception as e:
                logger.debug(f"Errore nel caricamento import_rapido: {e}")

            # Parametri AdE dal database
            try:
                params = carica_parametri()
                # Credenziali
                try:
                    self.cf_entry.insert(0, params["codicefiscale"])
                except Exception:
                    pass
                try:
                    self.pin_entry.insert(0, params["pin"])
                except Exception:
                    pass
                try:
                    self.pwd_entry.insert(0, params["password"])
                except Exception:
                    pass
                # Parametri di ricerca
                try:
                    self.piva_entry.insert(0, params["pivadiretta"])
                except Exception:
                    pass
                try:
                    self.dal_entry.insert(0, params["dal"])
                except Exception:
                    pass
                try:
                    self.al_entry.insert(0, params["al"])
                except Exception:
                    pass
                try:
                    self.tipo_entry.insert(0, str(params["tipo"]))
                except Exception:
                    pass
                try:
                    self.venoacq_entry.insert(0, params["venoacq"])
                except Exception:
                    pass
                try:
                    self.agg_entry.insert(0, params["aggiornamento"])
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Errore nel caricamento dei parametri AdE dal database: {e}")
            
            # Backup (se esiste la sezione)
            self.backup_folder.insert(0, self.config.get('Backup', 'cartella', fallback=''))
            self.keep_backup_days.set(self.config.get('Backup', 'giorni_ritenzione', fallback='30'))
            
            # Dropbox
            if hasattr(self, 'dropbox_enabled'):
                self.dropbox_enabled.set(self.config.getboolean('Backup', 'dropbox_enabled', fallback=False))
                self.dropbox_token.insert(0, self.config.get('Backup', 'dropbox_token', fallback=''))
                self.dropbox_folder.insert(0, self.config.get('Backup', 'dropbox_folder', fallback='/ContabilitaLM1/backup'))
            
            # Modalità backup
            if hasattr(self, 'backup_on_close'):
                self.backup_on_close.set(self.config.getboolean('Backup', 'backup_on_close', fallback=False))
                self.backup_scheduled.set(self.config.getboolean('Backup', 'backup_scheduled', fallback=False))
                schedule_time = self.config.get('Backup', 'backup_schedule_time', fallback='02:00')
                if hasattr(self, 'backup_schedule_time'):
                    self.backup_schedule_time.delete(0, tk.END)
                    self.backup_schedule_time.insert(0, schedule_time)
            
            # Aggiorna stato campi Dropbox
            if hasattr(self, 'dropbox_enabled'):
                self.toggle_dropbox_fields()
            
            # Email
            if hasattr(self, 'smtp_server_entry'):
                self.smtp_server_entry.insert(0, self.config.get('Email', 'smtp_server', fallback=''))
                port = self.config.get('Email', 'smtp_port', fallback='587')
                if port:
                    self.smtp_port_entry.delete(0, tk.END)
                    self.smtp_port_entry.insert(0, port)
                self.email_mittente_entry.insert(0, self.config.get('Email', 'email_mittente', fallback=''))
                self.email_password_entry.insert(0, self.config.get('Email', 'email_password', fallback=''))
                self.email_destinatario_entry.insert(0, self.config.get('Email', 'email_destinatario', fallback=''))
            
        except Exception as e:
            logger.error(f"Errore nel caricamento delle impostazioni: {e}")
            messagebox.showerror("Errore", f"Errore nel caricamento configurazione: {e}")
    
    def save_settings(self) -> None:
        """Salva le impostazioni nel file config.ini e nel database"""
        try:
            # Aggiorna i valori nella configurazione (file config.ini)
            if not self.config.has_section('Autenticazione'):
                self.config.add_section('Autenticazione')
            if not self.config.has_section('Backup'):
                self.config.add_section('Backup')
            if not self.config.has_section('Email'):
                self.config.add_section('Email')
            
            # Autenticazione
            self.config.set('Autenticazione', 'percorso_database', self.db_entry.get())
            
            # Parametri cartelle nel database
            try:
                set_cartella_emesse(self.vendita_entry.get())
                set_cartella_ricevute(self.acquisto_entry.get())
                set_cartella_stampa(self.stampa_entry.get())
            except Exception as e:
                logger.error(f"Errore nel salvataggio dei parametri cartelle nel database: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio parametri cartelle nel database: {e}")
                return
            
            # Parametri import nel database
            try:
                set_import_acquisti(self.import_acquisti_entry.get())
                set_import_vendite(self.import_vendite_entry.get())
                set_import_rapido(self.import_rapido_entry.get())
            except Exception as e:
                logger.error(f"Errore nel salvataggio dei parametri import nel database: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio parametri import nel database: {e}")
                return
            
            # Backup
            self.config.set('Backup', 'cartella', self.backup_folder.get())
            self.config.set('Backup', 'giorni_ritenzione', self.keep_backup_days.get())
            
            # Dropbox
            if hasattr(self, 'dropbox_enabled'):
                self.config.set('Backup', 'dropbox_enabled', str(self.dropbox_enabled.get()))
                self.config.set('Backup', 'dropbox_token', self.dropbox_token.get())
                self.config.set('Backup', 'dropbox_folder', self.dropbox_folder.get())
            
            # Modalità backup
            if hasattr(self, 'backup_on_close'):
                self.config.set('Backup', 'backup_on_close', str(self.backup_on_close.get()))
                self.config.set('Backup', 'backup_scheduled', str(self.backup_scheduled.get()))
                self.config.set('Backup', 'backup_schedule_time', self.backup_schedule_time.get())
            
            # Email
            if not self.config.has_section('Email'):
                self.config.add_section('Email')
            self.config.set('Email', 'smtp_server', self.smtp_server_entry.get().strip())
            self.config.set('Email', 'smtp_port', self.smtp_port_entry.get().strip())
            self.config.set('Email', 'email_mittente', self.email_mittente_entry.get().strip())
            self.config.set('Email', 'email_password', self.email_password_entry.get().strip())
            self.config.set('Email', 'email_destinatario', self.email_destinatario_entry.get().strip())
            
            # Salva sul file
            try:
                # Assicurati che la directory esista
                config_dir = os.path.dirname(self.config_file)
                if config_dir and not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)
                
                with open(self.config_file, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
                logger.info(f"Configurazione salvata in: {self.config_file}")
                messagebox.showinfo("Successo", "Configurazione salvata con successo!")
            except PermissionError as e:
                logger.error(f"Errore permessi nel salvataggio config: {e}")
                messagebox.showerror("Errore", f"Impossibile salvare la configurazione: permessi negati.\n{self.config_file}")
                return
            except Exception as e:
                logger.error(f"Errore nel salvataggio config: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio della configurazione: {e}")
                return

            # Aggiorna parametri AdE nel database
            try:
                # Credenziali
                aggiorna_credenziali_db(
                    codicefiscale=self.cf_entry.get().strip(),
                    pin=self.pin_entry.get().strip(),
                    password=self.pwd_entry.get().strip(),
                )

                # Parametri scarico
                tipo_raw = self.tipo_entry.get().strip()
                tipo_val = int(tipo_raw) if tipo_raw else None

                aggiorna_parametri(
                    dal=self.dal_entry.get().strip() or None,
                    al=self.al_entry.get().strip() or None,
                    tipo=tipo_val,
                    venoacq=self.venoacq_entry.get().strip() or None,
                    aggiornamento=self.agg_entry.get().strip() or None,
                    pivadiretta=self.piva_entry.get().strip() or None,
                )
            except Exception as e:
                logger.error(f"Errore nel salvataggio dei parametri AdE nel database: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio parametri AdE nel database: {e}")
                return

            messagebox.showinfo("Successo", "Parametri salvati correttamente!")
            self.window.destroy()
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio delle impostazioni: {e}")
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")
    
    def restore_defaults(self) -> None:
        """Ripristina le impostazioni predefinite"""
        if messagebox.askyesno("Conferma", "Ripristinare le impostazioni predefinite?\n\nTutti i valori correnti verranno persi."):
            try:
                # Pulizia campi
                for entry in [self.db_entry, self.vendita_entry, self.acquisto_entry, 
                             self.stampa_entry, self.import_acquisti_entry, 
                             self.import_vendite_entry, self.import_rapido_entry, 
                             self.backup_folder]:
                    entry.delete(0, tk.END)
                
                # Valori predefiniti
                default_db = "database/contabilita.db"
                default_vendita = "fatture/emesse"
                default_acquisto = "fatture/ricevute"
                default_stampa = "fatture/stampa"
                default_import_acquisti = "fatture/ricevute"
                default_import_vendite = "fatture/emesse"
                default_import_rapido = "fatture/emesse"
                default_backup = "backup"
                
                self.db_entry.insert(0, default_db)
                self.vendita_entry.insert(0, default_vendita)
                self.acquisto_entry.insert(0, default_acquisto)
                self.stampa_entry.insert(0, default_stampa)
                self.import_acquisti_entry.insert(0, default_import_acquisti)
                self.import_vendite_entry.insert(0, default_import_vendite)
                self.import_rapido_entry.insert(0, default_import_rapido)
                self.backup_folder.insert(0, default_backup)
                self.keep_backup_days.set("30")
                
                # Reset opzioni Dropbox
                if hasattr(self, 'dropbox_enabled'):
                    self.dropbox_enabled.set(False)
                    self.dropbox_token.delete(0, tk.END)
                    self.dropbox_folder.delete(0, tk.END)
                    self.dropbox_folder.insert(0, '/ContabilitaLM1/backup')
                    self.toggle_dropbox_fields()
                
                # Reset modalità backup
                if hasattr(self, 'backup_on_close'):
                    self.backup_on_close.set(False)
                    self.backup_scheduled.set(False)
                    self.backup_schedule_time.delete(0, tk.END)
                    self.backup_schedule_time.insert(0, '02:00')
                
                messagebox.showinfo("Successo", "Impostazioni predefinite ripristinate!")
                
            except Exception as e:
                logger.error(f"Errore nel ripristino delle impostazioni: {e}")
                messagebox.showerror("Errore", f"Errore nel ripristino: {e}")
    
    def browse_file(self, entry_widget: ttk.Entry, title: str, filetypes: list) -> None:
        """Apre la dialog per selezionare un file"""
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)
    
    def browse_folder(self, entry_widget: ttk.Entry, title: str) -> None:
        """Apre la dialog per selezionare una cartella"""
        folder = filedialog.askdirectory(title=title)
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)
    
    def execute_backup(self) -> None:
        """Esegue un backup manuale"""
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.backup_manager import BackupManager
            
            # Salva le impostazioni prima di eseguire il backup
            self.save_settings()
            
            # Crea il manager
            manager = BackupManager(self.config_file)
            
            # Mostra progresso
            progress_window = tk.Toplevel(self.window)
            progress_window.title("Backup in corso...")
            progress_window.geometry("400x100")
            progress_label = tk.Label(progress_window, text="Creazione backup in corso...", font=("Arial", 10))
            progress_label.pack(pady=20)
            progress_window.update()
            
            # Esegui backup
            upload_to_dropbox = hasattr(self, 'dropbox_enabled') and self.dropbox_enabled.get()
            success, local_path, dropbox_path = manager.create_backup(upload_to_dropbox=upload_to_dropbox)
            
            progress_window.destroy()
            
            if success:
                msg = "Backup eseguito con successo!\n\n"
                if local_path:
                    msg += f"Locale: {local_path}\n"
                if dropbox_path:
                    msg += f"Dropbox: {dropbox_path}\n"
                else:
                    # Controlla se Dropbox era abilitato ma non è riuscito
                    if upload_to_dropbox:
                        msg += "\n⚠️ Backup Dropbox non eseguito - verifica configurazione e permessi"
                messagebox.showinfo("Backup Completato", msg)
            else:
                messagebox.showerror("Errore", "Errore durante la creazione del backup")
                
        except Exception as e:
            logger.error(f"Errore nell'esecuzione del backup: {e}")
            messagebox.showerror("Errore", f"Errore durante il backup: {e}")
    
    def toggle_dropbox_fields(self) -> None:
        """Abilita/disabilita i campi Dropbox in base al checkbox"""
        enabled = self.dropbox_enabled.get() if hasattr(self, 'dropbox_enabled') else False
        if hasattr(self, 'dropbox_token'):
            self.dropbox_token.config(state='normal' if enabled else 'disabled')
        if hasattr(self, 'dropbox_folder'):
            self.dropbox_folder.config(state='normal' if enabled else 'disabled')
    
    def show_dropbox_info(self) -> None:
        """Mostra informazioni su come ottenere il token Dropbox"""
        info_text = """Come configurare Dropbox per i backup:

1. Vai su https://www.dropbox.com/developers/apps
2. Clicca su "Create app"
3. Configura l'app:
   - App name: scegli un nome (es. "ContabilitaLM1 Backup")
   - Type of access: "Full Dropbox"
   - App folder: lascia vuoto o scegli una cartella
4. IMPORTANTE - Vai alla scheda "Permissions":
   - Abilita "files.content.write" (obbligatorio per upload)
   - Abilita "files.content.read" (opzionale, per download)
   - Salva le modifiche
5. Vai alla scheda "Settings" → "Generate access token"
6. Copia il token generato e incollalo qui

⚠️ IMPORTANTE: Se ricevi errori di permessi, verifica che lo scope 
'files.content.write' sia abilitato nella scheda Permissions dell'app.

NOTA: Il token è sensibile, tienilo al sicuro!"""
        messagebox.showinfo("Informazioni Dropbox Token", info_text)
    
    def show_backup_list(self) -> None:
        """Mostra la lista dei backup disponibili"""
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.backup_manager import BackupManager
            
            manager = BackupManager(self.config_file)
            local_backups, dropbox_backups = manager.list_backups()
            
            # Crea finestra per visualizzare i backup
            list_window = tk.Toplevel(self.window)
            list_window.title("Lista Backup")
            list_window.geometry("700x500")
            
            # Notebook per separare backup locali e Dropbox
            notebook = ttk.Notebook(list_window)
            notebook.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Tab backup locali
            local_frame = ttk.Frame(notebook)
            notebook.add(local_frame, text=f"Backup Locali ({len(local_backups)})")
            
            local_tree = ttk.Treeview(local_frame, columns=('Data', 'Dimensione'), show='tree headings', height=15)
            local_tree.heading('#0', text='Nome File')
            local_tree.heading('Data', text='Data')
            local_tree.heading('Dimensione', text='Dimensione')
            local_tree.column('#0', width=300)
            local_tree.column('Data', width=150)
            local_tree.column('Dimensione', width=100)
            
            for backup in local_backups:
                size_mb = backup['size'] / (1024 * 1024)
                local_tree.insert('', 'end', text=backup['name'], 
                                values=(backup['date'].strftime('%Y-%m-%d %H:%M:%S'), 
                                       f"{size_mb:.2f} MB"))
            
            local_scrollbar = ttk.Scrollbar(local_frame, orient='vertical', command=local_tree.yview)
            local_tree.configure(yscrollcommand=local_scrollbar.set)
            local_tree.pack(side='left', fill='both', expand=True)
            local_scrollbar.pack(side='right', fill='y')
            
            # Tab backup Dropbox
            dropbox_frame = ttk.Frame(notebook)
            notebook.add(dropbox_frame, text=f"Backup Dropbox ({len(dropbox_backups)})")
            
            dropbox_tree = ttk.Treeview(dropbox_frame, columns=('Data', 'Dimensione'), show='tree headings', height=15)
            dropbox_tree.heading('#0', text='Nome File')
            dropbox_tree.heading('Data', text='Data')
            dropbox_tree.heading('Dimensione', text='Dimensione')
            dropbox_tree.column('#0', width=300)
            dropbox_tree.column('Data', width=150)
            dropbox_tree.column('Dimensione', width=100)
            
            for backup in dropbox_backups:
                size_mb = backup['size'] / (1024 * 1024)
                from datetime import datetime as dt
                date_str = backup['date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(backup['date'], dt) else str(backup['date'])
                dropbox_tree.insert('', 'end', text=backup['name'], 
                                  values=(date_str, f"{size_mb:.2f} MB"))
            
            dropbox_scrollbar = ttk.Scrollbar(dropbox_frame, orient='vertical', command=dropbox_tree.yview)
            dropbox_tree.configure(yscrollcommand=dropbox_scrollbar.set)
            dropbox_tree.pack(side='left', fill='both', expand=True)
            dropbox_scrollbar.pack(side='right', fill='y')
            
        except Exception as e:
            logger.error(f"Errore visualizzazione backup: {e}")
            messagebox.showerror("Errore", f"Errore nel caricamento dei backup: {e}")