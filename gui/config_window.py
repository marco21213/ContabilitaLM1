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
from scripts.email_config_db import (
    carica_email_config,
    aggiorna_email_config,
    get_email_config_decrypted,
    get_smtp_server,
    get_smtp_port,
    get_email_mittente,
    get_email_password_decrypted,
    get_email_destinatario,
)
from scripts.backup_config_db import (
    carica_backup_config,
    aggiorna_backup_config,
    get_backup_config_dict,
    get_backup_cartella,
    get_backup_giorni_ritenzione,
    get_backup_automatico,
    get_backup_locale_enabled,
    get_backup_dropbox_enabled,
    get_backup_dropbox_token,
    get_backup_dropbox_folder,
    get_backup_on_close,
    get_backup_scheduled,
    get_backup_schedule_time,
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
        
        # Abilita backup locale
        self.backup_locale_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            scrollable_frame,
            text="Abilita backup locale",
            variable=self.backup_locale_enabled
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5, padx=5)
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
        
        # Frame per i bottoni
        token_buttons_frame = ttk.Frame(dropbox_token_frame)
        token_buttons_frame.pack(side='right', padx=(5, 0))
        
        ttk.Button(
            token_buttons_frame,
            text="📖 Guida",
            command=self.show_dropbox_info
        ).pack(side='left', padx=2)
        
        ttk.Button(
            token_buttons_frame,
            text="✓ Test",
            command=self.test_dropbox_token
        ).pack(side='left', padx=2)
        
        row += 1
        
        # Dropbox Folder
        ttk.Label(scrollable_frame, text="Cartella Dropbox:").grid(row=row, column=0, sticky='w', pady=5)
        dropbox_folder_frame = ttk.Frame(scrollable_frame)
        dropbox_folder_frame.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
        self.dropbox_folder = ttk.Entry(dropbox_folder_frame, width=40)
        self.dropbox_folder.pack(side='left', fill='x', expand=True)
        ttk.Button(
            dropbox_folder_frame,
            text="ℹ️ Info Condivisione",
            command=self.show_dropbox_sharing_info
        ).pack(side='right', padx=(5, 0))
        row += 1
        
        # Nota sulla pulizia automatica
        cleanup_note = ttk.Label(
            scrollable_frame,
            text="ℹ️ I backup Dropbox vengono eliminati automaticamente dopo il numero di giorni impostato sopra",
            font=("Arial", 8),
            foreground="gray",
            wraplength=400,
            justify="left"
        )
        cleanup_note.grid(row=row, column=0, columnspan=2, sticky='w', pady=(0, 5), padx=5)
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
            
            # Backup - carica dal database
            try:
                backup_cartella = get_backup_cartella()
                if backup_cartella:
                    self.backup_folder.insert(0, backup_cartella)
                
                giorni_ritenzione = get_backup_giorni_ritenzione()
                if giorni_ritenzione:
                    self.keep_backup_days.set(str(giorni_ritenzione))
                else:
                    self.keep_backup_days.set('30')
                
                # Backup locale enabled
                if hasattr(self, 'backup_locale_enabled'):
                    self.backup_locale_enabled.set(get_backup_locale_enabled())
                
                # Dropbox
                if hasattr(self, 'dropbox_enabled'):
                    self.dropbox_enabled.set(get_backup_dropbox_enabled())
                    dropbox_token = get_backup_dropbox_token()
                    if dropbox_token:
                        self.dropbox_token.insert(0, dropbox_token)
                    dropbox_folder = get_backup_dropbox_folder()
                    if dropbox_folder:
                        self.dropbox_folder.insert(0, dropbox_folder)
                    else:
                        self.dropbox_folder.insert(0, '/ContabilitaLM1/backup')
                
                # Modalità backup
                if hasattr(self, 'backup_on_close'):
                    self.backup_on_close.set(get_backup_on_close())
                    self.backup_scheduled.set(get_backup_scheduled())
                    schedule_time = get_backup_schedule_time()
                    if hasattr(self, 'backup_schedule_time'):
                        self.backup_schedule_time.delete(0, tk.END)
                        self.backup_schedule_time.insert(0, schedule_time)
                
                # Aggiorna stato campi Dropbox
                if hasattr(self, 'dropbox_enabled'):
                    self.toggle_dropbox_fields()
            except Exception as e:
                logger.debug(f"Errore nel caricamento configurazione backup dal database: {e}")
                # Se non esiste la tabella o il record, usa valori di default
                if not self.backup_folder.get():
                    self.backup_folder.insert(0, '')
                if self.keep_backup_days.get() == '':
                    self.keep_backup_days.set('30')
            
            # Email - carica dal database
            if hasattr(self, 'smtp_server_entry'):
                try:
                    smtp_server = get_smtp_server()
                    if smtp_server:
                        self.smtp_server_entry.insert(0, smtp_server)
                    
                    smtp_port = get_smtp_port()
                    if smtp_port:
                        self.smtp_port_entry.delete(0, tk.END)
                        self.smtp_port_entry.insert(0, str(smtp_port))
                    else:
                        # Default se non presente
                        self.smtp_port_entry.delete(0, tk.END)
                        self.smtp_port_entry.insert(0, "587")
                    
                    email_mittente = get_email_mittente()
                    if email_mittente:
                        self.email_mittente_entry.insert(0, email_mittente)
                    
                    email_password = get_email_password_decrypted()
                    if email_password:
                        self.email_password_entry.insert(0, email_password)
                    
                    email_destinatario = get_email_destinatario()
                    if email_destinatario:
                        self.email_destinatario_entry.insert(0, email_destinatario)
                except Exception as e:
                    logger.debug(f"Errore nel caricamento configurazione email dal database: {e}")
                    # Se non esiste la tabella o il record, lascia i campi vuoti
            
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
            
            # Backup - salva nel database
            try:
                giorni_ritenzione_val = int(self.keep_backup_days.get()) if self.keep_backup_days.get().strip() else 30
                
                aggiorna_backup_config(
                    cartella=self.backup_folder.get().strip() or None,
                    giorni_ritenzione=giorni_ritenzione_val,
                    automatico=True,  # Sempre True se configurato
                    backup_locale_enabled=self.backup_locale_enabled.get() if hasattr(self, 'backup_locale_enabled') else None,
                    dropbox_enabled=self.dropbox_enabled.get() if hasattr(self, 'dropbox_enabled') else None,
                    dropbox_token=self.dropbox_token.get().strip() if hasattr(self, 'dropbox_token') else None,
                    dropbox_folder=self.dropbox_folder.get().strip() if hasattr(self, 'dropbox_folder') else None,
                    backup_on_close=self.backup_on_close.get() if hasattr(self, 'backup_on_close') else None,
                    backup_scheduled=self.backup_scheduled.get() if hasattr(self, 'backup_scheduled') else None,
                    backup_schedule_time=self.backup_schedule_time.get().strip() if hasattr(self, 'backup_schedule_time') else None,
                )
            except Exception as e:
                logger.error(f"Errore nel salvataggio della configurazione backup nel database: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio configurazione backup nel database: {e}")
                return
            
            # Email - salva nel database
            try:
                aggiorna_email_config(
                    smtp_server=self.smtp_server_entry.get().strip() or None,
                    smtp_port=int(self.smtp_port_entry.get().strip()) if self.smtp_port_entry.get().strip() else None,
                    email_mittente=self.email_mittente_entry.get().strip() or None,
                    email_password=self.email_password_entry.get().strip() or None,
                    email_destinatario=self.email_destinatario_entry.get().strip() or None,
                )
            except Exception as e:
                logger.error(f"Errore nel salvataggio della configurazione email nel database: {e}")
                messagebox.showerror("Errore", f"Errore nel salvataggio configurazione email nel database: {e}")
                return
            
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
        progress_window = None
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.backup_manager import BackupManager
            
            # Salva le impostazioni prima di eseguire il backup
            self.save_settings()
            
            # Crea il manager
            manager = BackupManager(self.config_file)
            
            # Mostra progresso (solo se la finestra principale è ancora valida)
            try:
                # Verifica che self.window sia ancora valida
                if hasattr(self, 'window') and self.window.winfo_exists():
                    progress_window = tk.Toplevel(self.window)
                    progress_window.title("Backup in corso...")
                    progress_window.geometry("400x100")
                    progress_window.transient(self.window)
                    progress_label = tk.Label(progress_window, text="Creazione backup in corso...", font=("Arial", 10))
                    progress_label.pack(pady=20)
                    progress_window.update()
                else:
                    progress_window = None
                    logger.warning("Finestra principale non più valida, backup senza finestra di progresso")
            except (tk.TclError, AttributeError) as e:
                logger.warning(f"Impossibile creare finestra di progresso: {e}")
                progress_window = None
            
            # Esegui backup
            upload_to_dropbox = hasattr(self, 'dropbox_enabled') and self.dropbox_enabled.get()
            success, local_path, dropbox_path = manager.create_backup(upload_to_dropbox=upload_to_dropbox)
            
            # La pulizia automatica Dropbox viene eseguita automaticamente durante create_backup
            # se upload_to_dropbox è True. Eseguiamo anche la pulizia locale.
            if success:
                try:
                    local_removed, dropbox_removed = manager.cleanup_old_backups()
                    if local_removed > 0 or dropbox_removed > 0:
                        logger.info(f"Pulizia backup: {local_removed} locali, {dropbox_removed} Dropbox rimossi")
                except Exception as cleanup_error:
                    logger.warning(f"Errore durante pulizia backup: {cleanup_error}")
            
            # Mostra messaggio di risultato (solo se la finestra è ancora valida)
            try:
                if hasattr(self, 'window') and self.window.winfo_exists():
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
                        messagebox.showinfo("Backup Completato", msg, parent=self.window)
                    else:
                        messagebox.showerror("Errore", "Errore durante la creazione del backup", parent=self.window)
                else:
                    # Finestra chiusa, logga solo il risultato
                    if success:
                        logger.info(f"Backup completato: {local_path}")
                    else:
                        logger.error("Errore durante la creazione del backup")
            except (tk.TclError, AttributeError) as e:
                logger.warning(f"Impossibile mostrare messaggio risultato: {e}")
                
        except Exception as e:
            logger.error(f"Errore nell'esecuzione del backup: {e}")
            error_msg = str(e)
            # Messaggio più chiaro per errori Dropbox comuni (solo se la finestra è ancora valida)
            try:
                if hasattr(self, 'window') and self.window.winfo_exists():
                    if "expired_access_token" in error_msg or "Token non valido" in error_msg:
                        messagebox.showerror(
                            "Errore Backup Dropbox", 
                            f"Token Dropbox scaduto o non valido.\n\n"
                            f"Per risolvere:\n"
                            f"1. Vai su https://www.dropbox.com/developers/apps\n"
                            f"2. Seleziona la tua app\n"
                            f"3. Genera un nuovo access token\n"
                            f"4. Inseriscilo nella configurazione backup",
                            parent=self.window
                        )
                    else:
                        messagebox.showerror("Errore", f"Errore durante il backup: {e}", parent=self.window)
                else:
                    # Finestra chiusa, logga solo l'errore
                    logger.error(f"Errore backup (finestra chiusa): {error_msg}")
            except (tk.TclError, AttributeError):
                # Anche il tentativo di mostrare il messaggio è fallito, logga solo
                logger.error(f"Errore backup: {error_msg}")
        finally:
            # Chiudi sempre la finestra di progresso se esiste e è ancora valida
            if progress_window is not None:
                try:
                    if progress_window.winfo_exists():
                        progress_window.destroy()
                except tk.TclError:
                    # La finestra è già stata distrutta o non è più valida
                    pass
    
    def toggle_dropbox_fields(self) -> None:
        """Abilita/disabilita i campi Dropbox in base al checkbox"""
        enabled = self.dropbox_enabled.get() if hasattr(self, 'dropbox_enabled') else False
        if hasattr(self, 'dropbox_token'):
            self.dropbox_token.config(state='normal' if enabled else 'disabled')
        if hasattr(self, 'dropbox_folder'):
            self.dropbox_folder.config(state='normal' if enabled else 'disabled')
    
    def show_dropbox_info(self) -> None:
        """Mostra informazioni dettagliate su come ottenere il token Dropbox"""
        # Crea una finestra personalizzata con scrollbar
        info_window = tk.Toplevel(self.window)
        info_window.title("Guida Completa: Configurazione Dropbox")
        info_window.geometry("700x600")
        info_window.transient(self.window)
        info_window.grab_set()
        
        # Frame principale
        main_frame = ttk.Frame(info_window, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="🔧 GUIDA COMPLETA: Configurazione Dropbox per Backup",
            font=("Arial", 14, "bold"),
            justify="center"
        )
        title_label.pack(pady=(0, 10))
        
        # Frame con scrollbar per il testo
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Text widget con scrollbar
        text_widget = tk.Text(
            text_frame,
            wrap='word',
            font=("Courier", 10),
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            bg='#f5f5f5',
            relief='flat'
        )
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Inserisci il testo
        info_text = """🔧 GUIDA COMPLETA: Configurazione Dropbox per Backup

═══════════════════════════════════════════════════════

📋 PASSO 1: Accedi a Dropbox Developers
─────────────────────────────────────────
1. Apri il browser e vai su:
   https://www.dropbox.com/developers/apps

2. Accedi con il tuo account Dropbox (se non sei già loggato)

═══════════════════════════════════════════════════════

📋 PASSO 2: Crea una Nuova App
─────────────────────────────────────────
1. Clicca sul pulsante "Create app" (in alto a destra)

2. Compila il form di creazione:
   
   ✓ Choose an API:
     → Seleziona "Scoped access" (raccomandato)
     → Oppure "Full Dropbox" (più permessi)
   
   ✓ Choose the type of access you need:
     → Seleziona "Full Dropbox"
     → (Non scegliere "App folder" a meno che non serva)
   
   ✓ Name your app:
     → Inserisci un nome (es. "ContabilitaLM1 Backup")
     → Questo nome sarà visibile solo a te
   
3. Clicca su "Create app"

═══════════════════════════════════════════════════════

📋 PASSO 3: Configura i Permessi (IMPORTANTE!)
─────────────────────────────────────────
1. Nella pagina dell'app appena creata, vai alla scheda:
   "Permissions" (o "Permessi" in italiano)

2. Nella sezione "Files and folders", abilita:
   
   ✓ files.content.write  → OBBLIGATORIO per upload
   ✓ files.content.read    → Opzionale (per download)
   ✓ files.metadata.read   → Opzionale (per liste file)
   
3. IMPORTANTE: Clicca su "Submit" o "Salva" per salvare
   le modifiche ai permessi

⚠️ ATTENZIONE: Se non salvi i permessi, il token non funzionerà!

═══════════════════════════════════════════════════════

📋 PASSO 4: Genera l'Access Token
─────────────────────────────────────────
1. Vai alla scheda "Settings" (o "Impostazioni")

2. Scorri fino alla sezione "OAuth 2"

3. Trova la sezione "Generated access token" e clicca su:
   "Generate" o "Genera"

4. ⚠️ IMPORTANTE: Copia SUBITO il token generato!
   → Il token viene mostrato UNA SOLA VOLTA
   → Se lo perdi, dovrai generarne uno nuovo
   → Il token è molto lungo (circa 200 caratteri)

5. Incolla il token nel campo "Dropbox Access Token" 
   qui nella configurazione

═══════════════════════════════════════════════════════

📋 PASSO 5: Configura la Cartella Dropbox
─────────────────────────────────────────
1. Nel campo "Cartella Dropbox" inserisci il percorso:
   → Esempio: /ContabilitaLM1/backup
   → La cartella verrà creata automaticamente se non esiste
   → Usa sempre "/" come separatore (anche su Windows)

2. Clicca su "Salva" per salvare la configurazione

═══════════════════════════════════════════════════════

✅ VERIFICA: Test del Token
─────────────────────────────────────────
Dopo aver inserito il token, puoi testarlo cliccando su:
"🔄 Esegui Backup Ora" nella sezione Backup

Se il token è valido, vedrai:
✓ "Backup eseguito con successo!"
✓ "Dropbox: /ContabilitaLM1/backup/database_..."

═══════════════════════════════════════════════════════

❌ PROBLEMI COMUNI
─────────────────────────────────────────

🔴 Errore "expired_access_token":
   → Il token è scaduto o non valido
   → Genera un nuovo token e sostituiscilo

🔴 Errore "files.content.write" o "scope":
   → I permessi non sono stati salvati correttamente
   → Torna alla scheda "Permissions" e salva di nuovo
   → Genera un NUOVO token dopo aver salvato i permessi

🔴 Errore "bad_request" o "invalid_token":
   → Il token è stato copiato in modo incompleto
   → Genera un nuovo token e copialo per intero

═══════════════════════════════════════════════════════

🔒 SICUREZZA
─────────────────────────────────────────
• Il token dà accesso completo al tuo Dropbox
• Non condividere mai il token con altri
• Se sospetti che il token sia compromesso, revocalo
  dalla pagina dell'app e generane uno nuovo

═══════════════════════════════════════════════════════"""
        
        text_widget.insert('1.0', info_text)
        text_widget.config(state='disabled')  # Solo lettura
        
        # Bottone chiudi
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Chiudi",
            command=info_window.destroy
        ).pack()
        
        # Centra la finestra
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (info_window.winfo_width() // 2)
        y = (info_window.winfo_screenheight() // 2) - (info_window.winfo_height() // 2)
        info_window.geometry(f"+{x}+{y}")
    
    def test_dropbox_token(self) -> None:
        """Testa il token Dropbox inserito"""
        token = self.dropbox_token.get().strip()
        
        if not token:
            messagebox.showwarning(
                "Token Mancante",
                "Inserisci prima un token Dropbox nel campo sopra.",
                parent=self.window
            )
            return
        
        # Mostra finestra di progresso
        progress_window = None
        try:
            if hasattr(self, 'window') and self.window.winfo_exists():
                progress_window = tk.Toplevel(self.window)
                progress_window.title("Test Connessione Dropbox")
                progress_window.geometry("400x120")
                progress_window.transient(self.window)
                progress_label = tk.Label(
                    progress_window, 
                    text="Test connessione Dropbox in corso...", 
                    font=("Arial", 10)
                )
                progress_label.pack(pady=20)
                progress_window.update()
        except (tk.TclError, AttributeError):
            progress_window = None
        
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Prova a importare dropbox
            try:
                import dropbox
                from dropbox.exceptions import AuthError, ApiError
            except ImportError:
                if progress_window and progress_window.winfo_exists():
                    progress_window.destroy()
                messagebox.showerror(
                    "Errore",
                    "Libreria Dropbox non installata.\n\n"
                    "Installa con: pip install dropbox",
                    parent=self.window
                )
                return
            
            # Test connessione
            dbx = dropbox.Dropbox(token)
            account = dbx.users_get_current_account()
            
            # Test permessi (prova a listare una cartella)
            try:
                # Prova a listare la root per verificare i permessi
                dbx.files_list_folder('')
                permissions_ok = True
            except ApiError as e:
                error_msg = str(e)
                if 'files.content.write' in error_msg or 'scope' in error_msg.lower():
                    permissions_ok = False
                else:
                    permissions_ok = True  # Altri errori non sono critici per il test
            
            # Chiudi finestra progresso
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
            
            # Mostra risultato
            if permissions_ok:
                success_msg = (
                    f"✅ Token valido!\n\n"
                    f"Account: {account.name.display_name}\n"
                    f"Email: {account.email}\n\n"
                    f"Il token è configurato correttamente e può essere usato per i backup."
                )
                messagebox.showinfo("Test Riuscito", success_msg, parent=self.window)
            else:
                warning_msg = (
                    f"⚠️ Token valido ma permessi insufficienti!\n\n"
                    f"Account: {account.name.display_name}\n"
                    f"Email: {account.email}\n\n"
                    f"PROBLEMA: Lo scope 'files.content.write' non è abilitato.\n\n"
                    f"Per risolvere:\n"
                    f"1. Vai su https://www.dropbox.com/developers/apps\n"
                    f"2. Seleziona la tua app\n"
                    f"3. Vai alla scheda 'Permissions'\n"
                    f"4. Abilita 'files.content.write'\n"
                    f"5. Salva le modifiche\n"
                    f"6. Genera un NUOVO token"
                )
                messagebox.showwarning("Permessi Insufficienti", warning_msg, parent=self.window)
                
        except AuthError as e:
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
            
            error_msg = str(e)
            if 'expired_access_token' in error_msg:
                error_text = (
                    f"❌ Token scaduto o non valido!\n\n"
                    f"Genera un nuovo token su:\n"
                    f"https://www.dropbox.com/developers/apps\n\n"
                    f"Vedi la guida completa cliccando su '📖 Guida'."
                )
            else:
                error_text = (
                    f"❌ Errore autenticazione!\n\n"
                    f"Errore: {error_msg}\n\n"
                    f"Il token potrebbe essere:\n"
                    f"• Copiato in modo incompleto\n"
                    f"• Non valido\n"
                    f"• Revocato\n\n"
                    f"Genera un nuovo token dalla pagina dell'app."
                )
            messagebox.showerror("Test Fallito", error_text, parent=self.window)
            
        except Exception as e:
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()
            
            error_text = (
                f"❌ Errore durante il test!\n\n"
                f"Errore: {str(e)}\n\n"
                f"Verifica:\n"
                f"• Connessione internet attiva\n"
                f"• Token copiato correttamente\n"
                f"• Libreria dropbox installata"
            )
            messagebox.showerror("Errore", error_text, parent=self.window)
    
    def show_dropbox_sharing_info(self) -> None:
        """Mostra informazioni su come condividere la cartella Dropbox"""
        info_text = """📁 Come Condividere la Cartella Backup su Dropbox

═══════════════════════════════════════════════════════

📋 METODO 1: Condivisione dalla Web App Dropbox
─────────────────────────────────────────
1. Accedi a https://www.dropbox.com nel browser
2. Naviga fino alla cartella configurata qui sopra
   (es. /ContabilitaLM1/backup)
3. Clicca con il tasto destro sulla cartella
4. Seleziona "Condividi" o "Share"
5. Inserisci l'email dell'utente con cui vuoi condividere
6. Scegli i permessi:
   - "Editor" → può vedere e scaricare i backup
   - "Viewer" → può solo vedere i backup (raccomandato)
7. Clicca su "Condividi" o "Share"

═══════════════════════════════════════════════════════

📋 METODO 2: Condivisione dal Client Desktop
─────────────────────────────────────────
1. Apri il client Dropbox sul tuo computer
2. Naviga fino alla cartella backup
3. Clicca con il tasto destro sulla cartella
4. Seleziona "Condividi cartella" o "Share folder"
5. Segui le stesse istruzioni del Metodo 1

═══════════════════════════════════════════════════════

📋 METODO 3: Link di Condivisione
─────────────────────────────────────────
1. Accedi a https://www.dropbox.com
2. Naviga alla cartella backup
3. Clicca con il tasto destro → "Crea link" o "Create link"
4. Copia il link generato
5. Condividi il link con gli utenti
6. ⚠️ IMPORTANTE: Puoi limitare i permessi del link:
   - Solo visualizzazione (raccomandato)
   - Con password
   - Con scadenza

═══════════════════════════════════════════════════════

🔒 SICUREZZA
─────────────────────────────────────────
• I backup contengono dati sensibili del database
• Condividi SOLO con utenti fidati
• Usa permessi "Viewer" (solo lettura) quando possibile
• Non condividere il token di accesso dell'app, solo la cartella
• Puoi revocare l'accesso in qualsiasi momento

═══════════════════════════════════════════════════════

ℹ️ NOTE IMPORTANTI
─────────────────────────────────────────
• La condivisione NON influisce sul backup automatico
• Solo la cartella specificata viene condivisa, non tutto Dropbox
• Gli utenti condivisi vedranno solo i file nella cartella backup
• I backup vengono eliminati automaticamente dopo i giorni configurati
• Puoi condividere con più utenti contemporaneamente

═══════════════════════════════════════════════════════"""
        
        # Crea una finestra personalizzata con scrollbar (come per la guida token)
        info_window = tk.Toplevel(self.window)
        info_window.title("Informazioni Condivisione Dropbox")
        info_window.geometry("700x600")
        info_window.transient(self.window)
        info_window.grab_set()
        
        # Frame principale
        main_frame = ttk.Frame(info_window, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="📁 Come Condividere la Cartella Backup",
            font=("Arial", 14, "bold"),
            justify="center"
        )
        title_label.pack(pady=(0, 10))
        
        # Frame con scrollbar per il testo
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Text widget con scrollbar
        text_widget = tk.Text(
            text_frame,
            wrap='word',
            font=("Courier", 10),
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            bg='#f5f5f5',
            relief='flat'
        )
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Inserisci il testo
        text_widget.insert('1.0', info_text)
        text_widget.config(state='disabled')  # Solo lettura
        
        # Bottone chiudi
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Chiudi",
            command=info_window.destroy
        ).pack()
        
        # Centra la finestra
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (info_window.winfo_width() // 2)
        y = (info_window.winfo_screenheight() // 2) - (info_window.winfo_height() // 2)
        info_window.geometry(f"+{x}+{y}")
    
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