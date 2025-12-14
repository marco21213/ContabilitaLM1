import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import configparser
import os
from PIL import Image, ImageTk
import re

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style


class SoggettoDialog(tk.Toplevel):
    def __init__(self, parent, db_path, soggetto_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.soggetto_data = soggetto_data
        
        self.title("Nuovo Soggetto" if soggetto_data is None else "Modifica Soggetto")
        self.geometry("600x500")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        self.center_window()
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        if soggetto_data:
            self.populate_fields()
            
        if hasattr(self, 'entries') and 'codice_soggetto' in self.entries:
            self.entries['codice_soggetto'].focus()
    
    def center_window(self):
        """Centra la finestra rispetto al parent"""
        self.update_idletasks()
        width = 600
        height = 500
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        
        x = max(0, x)
        y = max(0, y)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Crea i widget del form"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        
        fields = [
            ("Codice Soggetto*", "codice_soggetto"),
            ("Ragione Sociale*", "ragione_sociale"),
            ("Tipo Soggetto*", "tipo_soggetto"),
            ("Codice Fiscale", "codice_fiscale"),
            ("Partita IVA", "partita_iva"),
            ("Città", "citta"),
            ("CAP", "cap"),
            ("Provincia", "provincia"),
            ("Email", "email"),
            ("Codice Univoco", "codice_univoco")
        ]
        
        self.entries = {}
        row = 0
        
        for label_text, field_name in fields:
            field_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
            field_frame.grid(row=row, column=0, sticky="ew", pady=5)
            field_frame.grid_columnconfigure(1, weight=1)
            
            label = tk.Label(field_frame, text=label_text, 
                           bg=Style.BACKGROUND_COLOR,
                           fg="#000000",
                           font=("Arial", 10),
                           width=15, anchor="w")
            label.grid(row=0, column=0, sticky="w", padx=(0, 10))
            
            if field_name == "tipo_soggetto":
                entry = ttk.Combobox(field_frame, 
                                   values=["CLIENTE", "FORNITORE", "ENTRAMBI"],
                                   state="readonly",
                                   font=("Arial", 10))
                entry.set("Cliente")
            elif field_name == "cap":
                entry = tk.Entry(field_frame, font=("Arial", 10))
                vcmd = (self.register(self.validate_cap), '%P')
                entry.configure(validate="key", validatecommand=vcmd)
            else:
                entry = tk.Entry(field_frame, font=("Arial", 10))
            
            entry.grid(row=0, column=1, sticky="ew", padx=(0, 0))
            self.entries[field_name] = entry
            row += 1
        
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=row, column=0, pady=20, sticky="e")
        
        btn_annulla = tk.Button(button_frame, text="Annulla", 
                               command=self.destroy,
                               bg="#f44336", fg="white",
                               font=("Arial", 10),
                               width=10, cursor="hand2")
        btn_annulla.pack(side="right", padx=(10, 0))
        
        btn_salva = tk.Button(button_frame, text="Salva", 
                             command=self.salva_soggetto,
                             bg="#4CAF50", fg="white",
                             font=("Arial", 10, "bold"),
                             width=10, cursor="hand2")
        btn_salva.pack(side="right")
        
        self.bind('<Return>', lambda event: self.salva_soggetto())
        self.bind('<Escape>', lambda event: self.destroy())
    
    def validate_cap(self, value):
        """Valida che il CAP contenga solo numeri e sia lungo al massimo 5 caratteri"""
        if value == "":
            return True
        return value.isdigit() and len(value) <= 5
    
    def populate_fields(self):
        """Popola i campi con i dati esistenti per la modifica"""
        try:
            for field_name, entry in self.entries.items():
                value = self.soggetto_data.get(field_name, "")
                if isinstance(entry, ttk.Combobox):
                    entry.set(value if value else "CLIENTE")
                else:
                    entry.delete(0, tk.END)
                    entry.insert(0, str(value) if value else "")
        except Exception as e:
            print(f"Errore nel popolare i campi: {e}")
    
    def validate_fields(self):
        """Valida i campi obbligatori"""
        codice = self.entries['codice_soggetto'].get().strip()
        if not codice:
            messagebox.showerror("Errore", "Il campo Codice Soggetto è obbligatorio")
            self.entries['codice_soggetto'].focus()
            return False
        
        ragione = self.entries['ragione_sociale'].get().strip()
        if not ragione:
            messagebox.showerror("Errore", "Il campo Ragione Sociale è obbligatorio")
            self.entries['ragione_sociale'].focus()
            return False
        
        email = self.entries['email'].get().strip()
        if email and not self.validate_email(email):
            messagebox.showerror("Errore", "Formato email non valido")
            self.entries['email'].focus()
            return False
        
        cap = self.entries['cap'].get().strip()
        if cap and (not cap.isdigit() or len(cap) != 5):
            messagebox.showerror("Errore", "Il CAP deve essere composto da 5 cifre")
            self.entries['cap'].focus()
            return False
        
        return True
    
    def validate_email(self, email):
        """Valida il formato dell'email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def salva_soggetto(self):
        """Salva il soggetto nel database"""
        if not self.validate_fields():
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data = {
                'codice_soggetto': self.entries['codice_soggetto'].get().strip(),
                'ragione_sociale': self.entries['ragione_sociale'].get().strip(),
                'tipo_soggetto': self.entries['tipo_soggetto'].get().strip() or 'Cliente',
                'codice_fiscale': self.entries['codice_fiscale'].get().strip(),
                'partita_iva': self.entries['partita_iva'].get().strip(),
                'citta': self.entries['citta'].get().strip(),
                'cap': self.entries['cap'].get().strip(),
                'provincia': self.entries['provincia'].get().strip(),
                'email': self.entries['email'].get().strip(),
                'codice_univoco': self.entries['codice_univoco'].get().strip()
            }
            
            if self.soggetto_data is None:
                cursor.execute("SELECT COUNT(*) FROM soggetti WHERE codice_soggetto = ?", 
                             (data['codice_soggetto'],))
                if cursor.fetchone()[0] > 0:
                    messagebox.showerror("Errore", "Codice soggetto già esistente")
                    self.entries['codice_soggetto'].focus()
                    conn.close()
                    return
                
                cursor.execute("""
                    INSERT INTO soggetti 
                    (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale, 
                     partita_iva, citta, cap, provincia, email, codice_univoco)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(data.values()))
                
                message = "Soggetto creato correttamente"
            else:
                if data['codice_soggetto'] != self.soggetto_data['codice_soggetto']:
                    messagebox.showerror("Errore", "Non è possibile modificare il codice soggetto")
                    conn.close()
                    return
                
                cursor.execute("""
                    UPDATE soggetti SET
                    ragione_sociale=?, tipo_soggetto=?, codice_fiscale=?,
                    partita_iva=?, citta=?, cap=?, provincia=?, email=?, codice_univoco=?
                    WHERE codice_soggetto=?
                """, (data['ragione_sociale'], data['tipo_soggetto'], data['codice_fiscale'],
                      data['partita_iva'], data['citta'], data['cap'], data['provincia'],
                      data['email'], data['codice_univoco'], data['codice_soggetto']))
                
                message = "Soggetto aggiornato correttamente"
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", message)
            self.destroy()
            
            if hasattr(self.parent, 'load_data'):
                self.parent.load_data()
            
        except sqlite3.Error as e:
            messagebox.showerror("Errore Database", f"Errore del database: {str(e)}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il soggetto: {str(e)}")


class SoggettiApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.db_path = self.get_db_path()
        self.original_data = []
        self.item_to_codice = {}
        
        # Filtro attivo per la tab corrente
        self.current_tab_filter = "tutti"  # "clienti", "fornitori", "tutti"
        
        self.active_filters = {
            'ragione_sociale': '',
            'tipo_soggetto': '',
            'codice_fiscale': '',
            'partita_iva': '',
            'citta': '',
            'tipo_fattura': '',
            'tipo_pagamento': '',
            'email': '',
            'codice_univoco': ''
        }

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.configure_style()
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        # Crea il sistema di tab
        self.create_tab_system()
        
        # Carica dati
        self.load_data()

    def create_tab_system(self):
        """Crea il sistema di navigazione a tab"""
        # Frame principale per le tab
        tab_header_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, height=50)
        tab_header_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(Style.CONTENT_PADDING, 0))
        tab_header_frame.pack_propagate(False)
        
        # Stile per i pulsanti tab
        tab_style = {
            'font': ("Arial", 11, "bold"),
            'cursor': 'hand2',
            'relief': 'flat',
            'borderwidth': 0,
            'padx': 30,
            'pady': 10
        }
        
        # Tab buttons
        self.tab_buttons = {}
        
        # Tab Clienti
        self.tab_buttons['clienti'] = tk.Button(
            tab_header_frame, 
            text="👥 CLIENTI",
            command=lambda: self.switch_tab('clienti'),
            **tab_style
        )
        self.tab_buttons['clienti'].pack(side="left", padx=(0, 5))
        
        # Tab Fornitori
        self.tab_buttons['fornitori'] = tk.Button(
            tab_header_frame,
            text="🏭 FORNITORI",
            command=lambda: self.switch_tab('fornitori'),
            **tab_style
        )
        self.tab_buttons['fornitori'].pack(side="left", padx=(0, 5))
        
        # Tab Tutti
        self.tab_buttons['tutti'] = tk.Button(
            tab_header_frame,
            text="📋 TUTTI",
            command=lambda: self.switch_tab('tutti'),
            **tab_style
        )
        self.tab_buttons['tutti'].pack(side="left")
        
        # Etichetta contatore (a destra)
        self.counter_label = tk.Label(
            tab_header_frame,
            text="",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 10)
        )
        self.counter_label.pack(side="right", padx=(0, 10))
        
        # Contenuto tab (tutto il resto)
        self.content_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        self.content_frame.pack(fill="both", expand=True)
        
        # Crea la barra dei pulsanti nel content frame
        self.create_button_bar()
        
        # Crea la tabella nel content frame
        self.create_table()
        
        # Attiva la tab predefinita
        self.switch_tab('clienti')

    def switch_tab(self, tab_name):
        """Cambia la tab attiva"""
        self.current_tab_filter = tab_name
        
        # Aggiorna lo stile dei pulsanti
        for name, button in self.tab_buttons.items():
            if name == tab_name:
                # Tab attiva
                button.configure(
                    bg=Style.MENU_HEADER_BG,
                    fg="white"
                )
            else:
                # Tab inattiva
                button.configure(
                    bg="#E0E0E0",
                    fg="#666666"
                )
        
        # Resetta i filtri quando cambi tab
        self.clear_all_filters()
        
        # Applica i filtri della tab
        self.apply_filters()

    def create_button_bar(self):
        """Crea la barra dei pulsanti con le icone ridimensionate e descrizioni"""
        button_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(Style.CONTENT_PADDING, 10))
        
        icon_size = (32, 32)
        button_size = 40
        
        # Pulsante Nuovo
        try:
            new_frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            new_frame.pack(side="left", padx=(0, 25))
            
            new_image = Image.open("assets/icon/nuovo.png")
            new_image = new_image.resize(icon_size, Image.Resampling.LANCZOS)
            new_icon = ImageTk.PhotoImage(new_image)
            
            self.new_btn = tk.Button(new_frame, image=new_icon, 
                                    command=self.nuovo_soggetto,
                                    bg=Style.BACKGROUND_COLOR,
                                    relief="flat",
                                    cursor="hand2",
                                    width=button_size, height=button_size,
                                    borderwidth=0)
            self.new_btn.image = new_icon
            self.new_btn.pack()
            
            new_label = tk.Label(new_frame, text="Nuovo", 
                                bg=Style.BACKGROUND_COLOR,
                                fg="#000000",
                                font=("Arial", 10, "bold"))
            new_label.pack(pady=(8, 0))
            
        except Exception as e:
            print(f"Errore nel caricamento dell'icona nuovo: {e}")
            self.new_btn = tk.Button(button_frame, text="Nuovo", 
                                    command=self.nuovo_soggetto,
                                    bg="#4CAF50",
                                    fg="white",
                                    font=("Arial", 11, "bold"),
                                    cursor="hand2",
                                    width=12, height=2)
            self.new_btn.pack(side="left", padx=(0, 10))
        
        # Pulsante Modifica
        try:
            edit_frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            edit_frame.pack(side="left", padx=(0, 25))
            
            edit_image = Image.open("assets/icon/modifica.png")
            edit_image = edit_image.resize(icon_size, Image.Resampling.LANCZOS)
            edit_icon = ImageTk.PhotoImage(edit_image)
            
            self.edit_btn = tk.Button(edit_frame, image=edit_icon, 
                                     command=self.modifica_soggetto,
                                     bg=Style.BACKGROUND_COLOR,
                                     relief="flat",
                                     cursor="hand2",
                                     width=button_size, height=button_size,
                                     borderwidth=0)
            self.edit_btn.image = edit_icon
            self.edit_btn.pack()
            
            edit_label = tk.Label(edit_frame, text="Modifica", 
                                 bg=Style.BACKGROUND_COLOR,
                                 fg="#000000",
                                 font=("Arial", 10, "bold"))
            edit_label.pack(pady=(8, 0))
            
        except Exception as e:
            print(f"Errore nel caricamento dell'icona modifica: {e}")
            self.edit_btn = tk.Button(button_frame, text="Modifica", 
                                     command=self.modifica_soggetto,
                                     bg="#FF9800",
                                     fg="white",
                                     font=("Arial", 11, "bold"),
                                     cursor="hand2",
                                     width=12, height=2)
            self.edit_btn.pack(side="left", padx=(0, 10))
        
        # Pulsante Cancella
        try:
            delete_frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            delete_frame.pack(side="left")
            
            delete_image = Image.open("assets/icon/cancella.png")
            delete_image = delete_image.resize(icon_size, Image.Resampling.LANCZOS)
            delete_icon = ImageTk.PhotoImage(delete_image)
            
            self.delete_btn = tk.Button(delete_frame, image=delete_icon, 
                                       command=self.cancella_soggetto,
                                       bg=Style.BACKGROUND_COLOR,
                                       relief="flat",
                                       cursor="hand2",
                                       width=button_size, height=button_size,
                                       borderwidth=0)
            self.delete_btn.image = delete_icon
            self.delete_btn.pack()
            
            delete_label = tk.Label(delete_frame, text="Cancella", 
                                   bg=Style.BACKGROUND_COLOR,
                                   fg="#000000",
                                   font=("Arial", 10, "bold"))
            delete_label.pack(pady=(8, 0))
            
        except Exception as e:
            print(f"Errore nel caricamento dell'icona cancella: {e}")
            self.delete_btn = tk.Button(button_frame, text="Cancella", 
                                       command=self.cancella_soggetto,
                                       bg="#f44336",
                                       fg="white",
                                       font=("Arial", 11, "bold"),
                                       cursor="hand2",
                                       width=12, height=2)
            self.delete_btn.pack(side="left")

    def create_table(self):
        """Crea la tabella con le colonne richieste e filtri integrati nelle intestazioni"""
        columns = ("RAGIONE SOCIALE", "TIPO", "COD. FISCALE", "PARTITA IVA", "CITTÀ", "T.FATT", "PAGAMENTO", "EMAIL", "CODICE UNIVOCO")
        
        table_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("RAGIONE SOCIALE", text="RAGIONE SOCIALE ⧗", command=lambda: self.show_filter_menu("ragione_sociale", "RAGIONE SOCIALE"))
        self.tree.heading("TIPO", text="TIPO ⧗", command=lambda: self.show_filter_menu("tipo_soggetto", "TIPO"))
        self.tree.heading("COD. FISCALE", text="COD. FISCALE ⧗", command=lambda: self.show_filter_menu("codice_fiscale", "COD. FISCALE"))
        self.tree.heading("PARTITA IVA", text="PARTITA IVA ⧗", command=lambda: self.show_filter_menu("partita_iva", "PARTITA IVA"))
        self.tree.heading("CITTÀ", text="CITTÀ ⧗", command=lambda: self.show_filter_menu("citta", "CITTÀ"))
        self.tree.heading("T.FATT", text="T.FATT ⧗", command=lambda: self.show_filter_menu("tipo_fattura", "T.FATT"))
        self.tree.heading("PAGAMENTO", text="PAGAMENTO ⧗", command=lambda: self.show_filter_menu("tipo_pagamento", "PAGAMENTO"))
        self.tree.heading("EMAIL", text="EMAIL ⧗", command=lambda: self.show_filter_menu("email", "EMAIL"))
        self.tree.heading("CODICE UNIVOCO", text="CODICE UNIVOCO ⧗", command=lambda: self.show_filter_menu("codice_univoco", "CODICE UNIVOCO"))
        
        self.tree.column("RAGIONE SOCIALE", width=250, anchor="w", minwidth=200, stretch=True)
        self.tree.column("TIPO", width=100, anchor="center", minwidth=80, stretch=False)
        self.tree.column("COD. FISCALE", width=130, anchor="center", minwidth=120, stretch=False)
        self.tree.column("PARTITA IVA", width=130, anchor="center", minwidth=120, stretch=False)
        self.tree.column("CITTÀ", width=120, anchor="w", minwidth=100, stretch=False)
        self.tree.column("T.FATT", width=80, anchor="center", minwidth=70, stretch=False)
        self.tree.column("PAGAMENTO", width=120, anchor="center", minwidth=100, stretch=False)
        self.tree.column("EMAIL", width=180, anchor="w", minwidth=150, stretch=True)
        self.tree.column("CODICE UNIVOCO", width=130, anchor="center", minwidth=120, stretch=False)
        
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind('<Double-1>', lambda event: self.modifica_soggetto())
        
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')

    def show_filter_menu(self, field_name, column_title):
        """Mostra un menu di filtro per la colonna selezionata"""
        filter_window = tk.Toplevel(self)
        filter_window.title(f"Filtro - {column_title}")
        filter_window.geometry("300x150")
        filter_window.resizable(False, False)
        filter_window.configure(bg=Style.WHITE)
        
        filter_window.transient(self)
        filter_window.grab_set()
        
        main_frame = tk.Frame(filter_window, bg=Style.WHITE, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        label = tk.Label(main_frame, text=f"Filtro per {column_title}:", 
                        bg=Style.WHITE, fg="#000000", font=("Arial", 10, "bold"))
        label.pack(pady=(0, 10))
        
        if field_name == "tipo_soggetto":
            filter_entry = ttk.Combobox(main_frame, 
                                      values=["", "CLIENTE", "FORNITORE", "ENTRAMBI"],
                                      font=("Arial", 10),
                                      width=25)
            filter_entry.set(self.active_filters[field_name].upper())
        elif field_name == "tipo_fattura":
            filter_entry = ttk.Combobox(main_frame, 
                                      values=["", "TD01", "TD24"],
                                      font=("Arial", 10),
                                      width=25)
            filter_entry.set(self.active_filters[field_name].upper())
        else:
            filter_entry = tk.Entry(main_frame, font=("Arial", 10), width=25)
            current_filter = self.active_filters[field_name]
            if field_name != "email":
                current_filter = current_filter.upper()
            filter_entry.insert(0, current_filter)
        
        filter_entry.pack(pady=(0, 15))
        filter_entry.focus()
        
        button_frame = tk.Frame(main_frame, bg=Style.WHITE)
        button_frame.pack(fill="x")
        
        def apply_filter():
            filter_value = filter_entry.get().strip()
            if field_name != "email":
                self.active_filters[field_name] = filter_value.lower()
            else:
                self.active_filters[field_name] = filter_value.lower()
            self.apply_filters()
            filter_window.destroy()
        
        def clear_filter():
            self.active_filters[field_name] = ""
            self.apply_filters()
            filter_window.destroy()
        
        btn_apply = tk.Button(button_frame, text="Applica", command=apply_filter,
                             bg="#4CAF50", fg="white", font=("Arial", 10),
                             width=10, cursor="hand2")
        btn_apply.pack(side="left", padx=(0, 10))
        
        btn_clear = tk.Button(button_frame, text="Cancella", command=clear_filter,
                             bg="#f44336", fg="white", font=("Arial", 10),
                             width=10, cursor="hand2")
        btn_clear.pack(side="left")
        
        filter_entry.bind('<Return>', lambda e: apply_filter())
        filter_window.bind('<Escape>', lambda e: filter_window.destroy())

    def configure_style(self):
        """Configura lo stile per la tabella usando gli stili definiti"""
        style = ttk.Style()
        style.theme_use('default')
        
        style.configure("Treeview.Heading", 
                       background=Style.MENU_HEADER_BG,
                       foreground=Style.MENU_HEADER_FG,
                       font=("Arial", 10, "bold"),
                       padding=(5, 8),
                       relief="solid",
                       borderwidth=1,
                       lightcolor="#E0E0E0",
                       darkcolor="#E0E0E0")
        
        style.configure("Treeview",
                       font=("Arial", 9),
                       rowheight=26,
                       background="#FFFFFF",
                       foreground="#000000",
                       fieldbackground="#FFFFFF",
                       borderwidth=1,
                       relief="solid",
                       lightcolor="#E8E8E8",
                       darkcolor="#E8E8E8")
        
        style.map("Treeview", 
                 background=[('selected', '#4b6cb7')],
                 foreground=[('selected', 'white')])

    def get_db_path(self):
        """Ottiene il percorso del database dal file di configurazione"""
        try:
            config = configparser.ConfigParser()
            config.read("config.ini", encoding="utf-8")
            return config.get("Autenticazione", "percorso_database", fallback="./database.db")
        except Exception as e:
            print(f"Errore nella lettura del config: {e}")
            return "./database.db"

    def load_data(self):
        """Carica i dati dalla tabella soggetti"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se le colonne tipo_fattura e tipo_pagamento esistono
            cursor.execute("PRAGMA table_info(soggetti)")
            colonne = [col[1] for col in cursor.fetchall()]
            has_tipo_fattura = 'tipo_fattura' in colonne
            has_tipo_pagamento = 'tipo_pagamento' in colonne
            
            # Costruisci la query con LEFT JOIN per tipo_pagamento
            if has_tipo_fattura and has_tipo_pagamento:
                cursor.execute("""
                    SELECT s.ragione_sociale, s.tipo_soggetto, s.codice_fiscale, 
                           s.partita_iva, s.citta, s.tipo_fattura, 
                           COALESCE(tp.tipo, '') AS tipo_pagamento,
                           s.email, s.codice_univoco, s.codice_soggetto
                    FROM soggetti s
                    LEFT JOIN tipo_pagamento tp ON s.tipo_pagamento = tp.id
                    ORDER BY s.ragione_sociale
                """)
            elif has_tipo_fattura:
                cursor.execute("""
                    SELECT ragione_sociale, tipo_soggetto, codice_fiscale, 
                           partita_iva, citta, tipo_fattura, 
                           '' AS tipo_pagamento,
                           email, codice_univoco, codice_soggetto
                    FROM soggetti
                    ORDER BY ragione_sociale
                """)
            elif has_tipo_pagamento:
                cursor.execute("""
                    SELECT s.ragione_sociale, s.tipo_soggetto, s.codice_fiscale, 
                           s.partita_iva, s.citta, '' AS tipo_fattura,
                           COALESCE(tp.tipo, '') AS tipo_pagamento,
                           s.email, s.codice_univoco, s.codice_soggetto
                    FROM soggetti s
                    LEFT JOIN tipo_pagamento tp ON s.tipo_pagamento = tp.id
                    ORDER BY s.ragione_sociale
                """)
            else:
                cursor.execute("""
                    SELECT ragione_sociale, tipo_soggetto, codice_fiscale, 
                           partita_iva, citta, '' AS tipo_fattura, '' AS tipo_pagamento,
                           email, codice_univoco, codice_soggetto
                    FROM soggetti
                    ORDER BY ragione_sociale
                """)
            
            rows = cursor.fetchall()
            conn.close()

            self.original_data = []
            for row in rows:
                data_row = {
                    'ragione_sociale': str(row[0]) if row[0] is not None else "",
                    'tipo_soggetto': str(row[1]) if row[1] is not None else "",
                    'codice_fiscale': str(row[2]) if row[2] is not None else "",
                    'partita_iva': str(row[3]) if row[3] is not None else "",
                    'citta': str(row[4]) if row[4] is not None else "",
                    'tipo_fattura': str(row[5]) if row[5] is not None else "",
                    'tipo_pagamento': str(row[6]) if row[6] is not None else "",
                    'email': str(row[7]) if row[7] is not None else "",
                    'codice_univoco': str(row[8]) if row[8] is not None else "",
                    'codice_soggetto': str(row[9]) if row[9] is not None else ""
                }
                self.original_data.append(data_row)

            self.apply_filters()

        except sqlite3.Error as e:
            messagebox.showerror("Errore Database", f"Errore nel caricamento dati: {str(e)}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore generico: {str(e)}")
            print(f"Errore durante il caricamento dei dati: {e}")

    def apply_filters(self, event=None):
        """Applica i filtri ai dati e aggiorna la visualizzazione"""
        filtered_data = []
        
        for row_data in self.original_data:
            # Filtro per tab
            tipo = row_data.get('tipo_soggetto', '').lower()
            
            if self.current_tab_filter == 'clienti':
                if tipo not in ['cliente', 'entrambi']:
                    continue
            elif self.current_tab_filter == 'fornitori':
                if tipo not in ['fornitore', 'entrambi']:
                    continue
            # Se 'tutti', nessun filtro sulla tipologia
            
            # Filtri aggiuntivi dall'utente
            match = True
            for field_name, filter_value in self.active_filters.items():
                if filter_value:
                    cell_value = str(row_data.get(field_name, "")).lower()
                    if filter_value not in cell_value:
                        match = False
                        break
            
            if match:
                filtered_data.append(row_data)
        
        self.update_table_display(filtered_data)

    def update_table_display(self, data):
        """Aggiorna la visualizzazione della tabella con i dati filtrati"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_to_codice.clear()

        for i, row_data in enumerate(data):
            values = [
                row_data['ragione_sociale'].upper(),
                row_data['tipo_soggetto'].upper(),
                row_data['codice_fiscale'].upper(),
                row_data['partita_iva'].upper(),
                row_data['citta'].upper(),
                row_data['tipo_fattura'].upper(),
                row_data['tipo_pagamento'].upper(),
                row_data['email'],
                row_data['codice_univoco'].upper()
            ]
            
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            item_id = self.tree.insert("", tk.END, values=values, tags=(tag,))
            self.item_to_codice[item_id] = row_data['codice_soggetto']
        
        # Aggiorna il contatore
        tab_label = {
            'clienti': 'Clienti',
            'fornitori': 'Fornitori',
            'tutti': 'Soggetti'
        }
        self.counter_label.config(
            text=f"{len(data)} {tab_label[self.current_tab_filter]} visualizzati"
        )

    def clear_all_filters(self):
        """Cancella tutti i filtri e ricarica tutti i dati"""
        for key in self.active_filters:
            self.active_filters[key] = ""
        self.apply_filters()

    def nuovo_soggetto(self):
        """Apre una finestra per inserire un nuovo soggetto"""
        try:
            dialog = SoggettoDialog(self.parent, self.db_path)
            dialog.center_window()
            dialog.wait_window()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la finestra: {str(e)}")
            print(f"Errore nell'apertura dialog nuovo soggetto: {e}")

    def modifica_soggetto(self):
        """Apre una finestra per modificare il soggetto selezionato"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un soggetto da modificare")
            return
        
        try:
            item = selected[0]
            codice_soggetto = self.item_to_codice.get(item)
            
            if not codice_soggetto:
                messagebox.showerror("Errore", "Impossibile ottenere il codice soggetto")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT codice_soggetto, ragione_sociale, tipo_soggetto, 
                       codice_fiscale, partita_iva, citta, cap, 
                       provincia, email, codice_univoco
                FROM soggetti 
                WHERE codice_soggetto = ?
            """, (codice_soggetto,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = ['codice_soggetto', 'ragione_sociale', 'tipo_soggetto', 
                          'codice_fiscale', 'partita_iva', 'citta', 'cap', 
                          'provincia', 'email', 'codice_univoco']
                soggetto_data = dict(zip(columns, row))
                
                dialog = SoggettoDialog(self.parent, self.db_path, soggetto_data)
                dialog.center_window()
                dialog.wait_window()
            else:
                messagebox.showerror("Errore", "Soggetto non trovato nel database")
                
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare i dati: {str(e)}")
            print(f"Errore nella modifica soggetto: {e}")

    def cancella_soggetto(self):
        """Elimina il soggetto selezionato"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un soggetto da eliminare")
            return
        
        try:
            item = selected[0]
            values = self.tree.item(item)['values']
            codice_soggetto = self.item_to_codice.get(item)
            ragione_sociale = values[0]
            
            if not codice_soggetto:
                messagebox.showerror("Errore", "Impossibile ottenere il codice soggetto")
                return
            
            if messagebox.askyesno("Conferma eliminazione", 
                                  f"Sei sicuro di voler eliminare il soggetto:\n{ragione_sociale}?"):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM soggetti WHERE codice_soggetto = ?", (codice_soggetto,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    messagebox.showinfo("Successo", "Soggetto eliminato correttamente")
                    self.load_data()
                else:
                    messagebox.showwarning("Attenzione", "Soggetto non trovato")
                
                conn.close()
                
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile eliminare il soggetto: {str(e)}")
            print(f"Errore nell'eliminazione: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Soggetti")
    root.geometry("1200x700")
    
    app = SoggettiApp(root)
    app.pack(fill="both", expand=True)
    
    root.mainloop()