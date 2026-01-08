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
        # Cartella backup
        ttk.Label(parent, text="Cartella backup:").grid(row=0, column=0, sticky='w', pady=5)
        
        backup_frame = ttk.Frame(parent)
        backup_frame.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.backup_folder = ttk.Entry(backup_frame, width=30)
        self.backup_folder.pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            backup_frame, 
            text="Sfoglia...", 
            command=lambda: self.browse_folder(self.backup_folder, "Seleziona cartella backup")
        ).pack(side='right', padx=(5, 0))
        
        # Mantieni backup per
        ttk.Label(parent, text="Mantieni backup per (giorni):").grid(row=1, column=0, sticky='w', pady=5)
        self.keep_backup_days = ttk.Spinbox(
            parent, 
            from_=1, 
            to=365, 
            width=5
        )
        self.keep_backup_days.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Backup automatico
        self.auto_backup = tk.BooleanVar()
        ttk.Checkbutton(
            parent, 
            text="Backup automatico giornaliero", 
            variable=self.auto_backup
        ).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        # Esegui backup ora
        ttk.Button(
            parent, 
            text="Esegui Backup Ora", 
            command=self.execute_backup
        ).grid(row=3, column=0, columnspan=2, pady=10)
        
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
            self.backup_folder.insert(0, self.config.get('Backup', 'cartella', fallback='C:/backup/contabilita'))
            self.keep_backup_days.set(self.config.get('Backup', 'giorni_ritenzione', fallback='30'))
            self.auto_backup.set(self.config.getboolean('Backup', 'automatico', fallback=True))
            
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
            self.config.set('Backup', 'automatico', str(self.auto_backup.get()))
            
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
                self.auto_backup.set(True)
                
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
        # Qui implementeresti la logica di backup reale
        db_path = self.db_entry.get()
        backup_path = self.backup_folder.get()
        
        if not db_path or not backup_path:
            messagebox.showerror("Errore", "Specificare il percorso del database e della cartella di backup!")
            return
            
        try:
            # Simulazione backup (sostituire con logica reale)
            import shutil
            import datetime
            
            if not os.path.exists(backup_path):
                os.makedirs(backup_path)
            
            backup_file = os.path.join(
                backup_path, 
                f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            
            # Copia il file database (simulazione)
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_file)
                messagebox.showinfo("Backup", f"Backup eseguito correttamente!\nFile: {backup_file}")
            else:
                messagebox.showerror("Errore", f"File database non trovato: {db_path}")
                
        except Exception as e:
            logger.error(f"Errore nell'esecuzione del backup: {e}")
            messagebox.showerror("Errore", f"Errore durante il backup: {e}")