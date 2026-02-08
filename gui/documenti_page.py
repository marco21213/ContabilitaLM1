import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import configparser
import os
from PIL import Image, ImageTk
from datetime import datetime
from tkcalendar import DateEntry
import sys
sys.path.append("scripts")
from parametri_db import get_cartella_ricevute, get_import_rapido

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style

# Importa le finestre di modifica e nuovo
sys.path.append('.')
from documenti_page_modifica import ModificaDocumentoWindow
from documenti_page_nuovo import NuovoDocumentoWindow
from documenti_page_importa import ImportaDocumentoWindow
from documenti_page_importa_vendite import ImportaDocumentoVenditeWindow

class VistaScadenzeApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.db_path = self.get_db_path()

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.original_data = []
        
        # Filtro attivo per la tab corrente
        self.current_tab_filter = "acquisti"  # "acquisti", "vendite", "scaduto_clienti", "scaduto_fornitori"
        
        # Indica se stiamo visualizzando dati scaduti (per cambiare la struttura della tabella)
        self.mode_scaduti = False
        
        self.active_filters = {
            'data': '',
            'tipo': '',
            'numero': '',
            'soggetto': '',
            'totale': '',
            'scadenza': '',
            'pagamenti': '',
            'residuo': '',
            'tipo_pag': '',
            'stato': ''
        }
        
        # Impostazioni di ordinamento (carica da config.ini)
        self.sort_column = self.get_sort_preference('column', 'data')  # 'data', 'numero' o 'soggetto'
        self.sort_direction = self.get_sort_preference('direction', 'desc')  # 'asc' o 'desc'

        self.configure_style()
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        # Crea il sistema di tab
        self.create_tab_system()
        
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
        
        # Tab Acquisti
        self.tab_buttons['acquisti'] = tk.Button(
            tab_header_frame, 
            text="📥 ACQUISTI",
            command=lambda: self.switch_tab('acquisti'),
            **tab_style
        )
        self.tab_buttons['acquisti'].pack(side="left", padx=(0, 5))
        
        # Tab Vendite
        self.tab_buttons['vendite'] = tk.Button(
            tab_header_frame,
            text="📤 VENDITE",
            command=lambda: self.switch_tab('vendite'),
            **tab_style
        )
        self.tab_buttons['vendite'].pack(side="left", padx=(0, 5))
        
        # Tab Scaduto Clienti
        self.tab_buttons['scaduto_clienti'] = tk.Button(
            tab_header_frame,
            text="⚠️ SCADUTO CLIENTI",
            command=lambda: self.switch_tab('scaduto_clienti'),
            **tab_style
        )
        self.tab_buttons['scaduto_clienti'].pack(side="left", padx=(0, 5))
        
        # Tab Scaduto Fornitori
        self.tab_buttons['scaduto_fornitori'] = tk.Button(
            tab_header_frame,
            text="⚠️ SCADUTO FORNITORI",
            command=lambda: self.switch_tab('scaduto_fornitori'),
            **tab_style
        )
        self.tab_buttons['scaduto_fornitori'].pack(side="left")
        
        # Frame per contatore (a destra)
        right_frame = tk.Frame(tab_header_frame, bg=Style.BACKGROUND_COLOR)
        right_frame.pack(side="right", padx=(0, 10))
        
        # Etichetta contatore
        self.counter_label = tk.Label(
            right_frame,
            text="",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 10)
        )
        self.counter_label.pack(side="left")
        
        # Contenuto tab (tutto il resto)
        self.content_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        self.content_frame.pack(fill="both", expand=True)
        
        # Crea la barra dei pulsanti nel content frame
        self.create_button_bar()
        
        # Crea la tabella nel content frame
        self.create_table()
        
        # Attiva la tab predefinita
        self.switch_tab('acquisti')
    
    def switch_tab(self, tab_name):
        """Cambia la tab attiva"""
        self.current_tab_filter = tab_name
        
        # Determina se stiamo in modalità scaduti
        self.mode_scaduti = tab_name in ['scaduto_clienti', 'scaduto_fornitori']
        
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
        
        # Cambia la struttura della tabella se necessario
        if self.mode_scaduti:
            self.switch_to_scaduti_table()
            # Per scaduti, imposta ordinamento predefinito
            if self.sort_column not in ['ragione_sociale', 'saldo_scaduto', 'numero_scadenze']:
                self.sort_column = 'ragione_sociale'
                self.sort_direction = 'asc'
        else:
            self.switch_to_documenti_table()
            # Per documenti, imposta ordinamento predefinito
            if self.sort_column not in ['data', 'numero', 'soggetto']:
                self.sort_column = 'data'
                self.sort_direction = 'desc'
        
        # Aggiorna visibilità bottone dettaglio fatture sospese
        self._update_dettaglio_sospese_button()
        
        # Aggiorna visibilità bottoni import
        self.update_button_visibility()
        
        # Aggiorna etichetta ordinamento
        self.update_sort_label()
        
        # Resetta i filtri quando cambi tab
        self.clear_all_filters(silent=True)
        
        # Carica i dati appropriati
        if self.mode_scaduti:
            self.load_data_scaduti()
        else:
            self.load_data()
    
    def update_button_visibility(self):
        """Aggiorna la visibilità dei bottoni in base alla tab attiva"""
        if not hasattr(self, 'button_frames'):
            return
        
        tab = self.current_tab_filter
        
        # Definisci quali bottoni mostrare per ogni tab
        visibility_rules = {
            'acquisti': {
                'import_acquisti': True,   # Mostra Import Acquisti
                'import_vendite': False,    # Nascondi Import Vendite
                'import_rapido': False      # Nascondi Import Rapido
            },
            'vendite': {
                'import_acquisti': False,   # Nascondi Import Acquisti
                'import_vendite': True,     # Mostra Import Vendite
                'import_rapido': False      # Nascondi Import Rapido
            },
            'scaduto_clienti': {
                'import_acquisti': False,   # Nascondi Import Acquisti
                'import_vendite': False,    # Nascondi Import Vendite
                'import_rapido': False      # Nascondi Import Rapido
            },
            'scaduto_fornitori': {
                'import_acquisti': False,   # Nascondi Import Acquisti
                'import_vendite': False,    # Nascondi Import Vendite
                'import_rapido': False      # Nascondi Import Rapido
            }
        }
        
        # Applica le regole
        if tab in visibility_rules:
            rules = visibility_rules[tab]
            for button_key, visible in rules.items():
                if button_key in self.button_frames:
                    if visible:
                        self.button_frames[button_key].pack(side="left", padx=(0, 25))
                    else:
                        self.button_frames[button_key].pack_forget()

    def create_button_bar(self):
        button_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(Style.CONTENT_PADDING, 10))
        icon_size = (32, 32)
        button_size = 40

        def add_button(frame, icon_name, text, command, fallback_color, button_key=None):
            try:
                img = Image.open(f"assets/icon/{icon_name}.png")
                img = img.resize(icon_size, Image.Resampling.LANCZOS)
                icon = ImageTk.PhotoImage(img)
                btn = tk.Button(frame, image=icon, command=command,
                                bg=Style.BACKGROUND_COLOR, relief="flat",
                                cursor="hand2", width=button_size, height=button_size, borderwidth=0)
                btn.image = icon
                btn.pack()
                tk.Label(frame, text=text, bg=Style.BACKGROUND_COLOR,
                         fg="#1f396a", font=("Arial", 10, "bold")).pack(pady=(8, 0))
            except Exception as e:
                print(f"Errore caricamento icona {icon_name}: {e}")
                btn = tk.Button(frame, text=text, command=command, bg=fallback_color,
                                fg="white", font=("Arial", 11, "bold"), cursor="hand2", width=12, height=2)
                btn.pack()
            
            # Salva il riferimento al frame per poterlo nascondere/mostrare
            if button_key:
                if not hasattr(self, 'button_frames'):
                    self.button_frames = {}
                self.button_frames[button_key] = frame
            
            return frame

        # Pulsanti principali (sempre visibili)
        buttons_always = [
            ("nuovo", "Nuovo", self.nuovo_documento, "#4CAF50", None),
            ("modifica", "Modifica", self.modifica_documento, "#FF9800", None),
            ("cancella", "Cancella", self.cancella_documento, "#f44336", None),
        ]
        
        # Pulsanti condizionali (visibili solo in alcune tab)
        buttons_conditional = [
            ("import_acquisti", "Importa Acquisti", self.importa_acquisti, "#9C27B0", "import_acquisti"),
            ("import_vendite", "Importa Vendite", self.importa_vendite, "#9C27B0", "import_vendite"),
            ("import_rapido", "Import Rapido", self.importa_rapido, "#00BCD4", "import_rapido"),
        ]
        
        # Pulsante filtri (sempre visibile)
        buttons_filtri = [
            ("filtri", "Cancella filtri", self.clear_all_filters, "#607D8B", None),
        ]
        
        # Crea tutti i bottoni sempre visibili
        for icon, text, cmd, color, key in buttons_always:
            frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            frame.pack(side="left", padx=(0, 25))
            add_button(frame, icon, text, cmd, color, key)
        
        # Crea i bottoni condizionali (verranno mostrati/nascosti dinamicamente)
        for icon, text, cmd, color, key in buttons_conditional:
            frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            # Non fare pack subito, verrà gestito da update_button_visibility
            add_button(frame, icon, text, cmd, color, key)
        
        # Crea il pulsante filtri (sempre visibile)
        for icon, text, cmd, color, key in buttons_filtri:
            frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            frame.pack(side="left", padx=(0, 25))
            add_button(frame, icon, text, cmd, color, key)
        
        # Aggiorna la visibilità iniziale (mostra/nascondi i bottoni condizionali)
        self.update_button_visibility()
        
        # Bottone per dettaglio fatture sospese (solo per scaduto clienti)
        self.dettaglio_sospese_frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
        self.dettaglio_sospese_frame.pack(side="left", padx=(0, 25))
        self.dettaglio_sospese_btn = None
        self._update_dettaglio_sospese_button()
        
        # Aggiungi pulsante ordinamento a destra
        sort_frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
        sort_frame.pack(side="right", padx=(20, 0))
        
        self.sort_btn = tk.Button(
            sort_frame,
            text="Ordina",
            command=self.show_sort_menu,
            bg="#E0E0E0",
            fg="#333333",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            relief="flat",
            padx=15,
            pady=10
        )
        self.sort_btn.pack()
        
        # Etichetta che mostra l'ordinamento attivo
        self.sort_label = tk.Label(
            sort_frame,
            text="",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 9),
            anchor="center"
        )
        self.sort_label.pack(pady=(5, 0))
        
        # Aggiorna l'etichetta iniziale
        self.update_sort_label()

    def clear_all_filters(self, silent=False):
        """Cancella tutti i filtri"""
        for key in self.active_filters.keys():
            self.active_filters[key] = ""
        if self.mode_scaduti:
            self.apply_filters_scaduti()
        else:
            self.apply_filters()
        if not silent:
            messagebox.showinfo("Filtri", "Tutti i filtri sono stati rimossi.")

    def create_table(self):
        """Crea la tabella iniziale (per documenti)"""
        columns = ("DATA", "TIPO", "NUMERO", "SOGGETTO", "TOTALE", "SCADENZA",
                   "PAGAMENTI", "RESIDUO", "TIPO PAG.", "STATO")

        table_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            field_key = col.lower().replace(" ", "_").replace(".", "")
            self.tree.heading(col, text=f"{col} ⧗", command=lambda f=field_key, c=col: self.show_filter_menu(f, c))

        for name, w, a in [("DATA", 90, "center"), ("TIPO", 90, "center"), ("NUMERO", 100, "center"),
                           ("SOGGETTO", 180, "w"), ("TOTALE", 100, "e"), ("SCADENZA", 90, "center"),
                           ("PAGAMENTI", 110, "e"), ("RESIDUO", 100, "e"), ("TIPO PAG.", 100, "center"),
                           ("STATO", 90, "center")]:
            self.tree.column(name, width=w, anchor=a)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')
        
        # Salva il riferimento al frame della tabella
        self.table_frame = table_frame
    
    def switch_to_scaduti_table(self):
        """Cambia la tabella per mostrare dati scaduti"""
        # Rimuovi la tabella esistente
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Crea nuova tabella per scaduti
        columns = ("CODICE", "RAGIONE SOCIALE", "N° SCADUTE", "TOTALE SCADENZE", 
                   "TOTALE PAGATO", "SALDO SCADUTO")
        
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        # Configurazione intestazioni (senza filtri per scaduti)
        for col in columns:
            self.tree.heading(col, text=col)
        
        # Configurazione colonne
        self.tree.column("CODICE", width=100, anchor="center")
        self.tree.column("RAGIONE SOCIALE", width=250, anchor="w")
        self.tree.column("N° SCADUTE", width=100, anchor="center")
        self.tree.column("TOTALE SCADENZE", width=150, anchor="e")
        self.tree.column("TOTALE PAGATO", width=150, anchor="e")
        self.tree.column("SALDO SCADUTO", width=150, anchor="e")
        
        # Scrollbar
        scrollbar_y = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        # Layout con griglia
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        
        # Configura righe alternate
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')
    
    def switch_to_documenti_table(self):
        """Ripristina la tabella per documenti"""
        # Rimuovi la tabella esistente
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Ricrea la tabella documenti
        columns = ("DATA", "TIPO", "NUMERO", "SOGGETTO", "TOTALE", "SCADENZA",
                   "PAGAMENTI", "RESIDUO", "TIPO PAG.", "STATO")
        
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        for col in columns:
            field_key = col.lower().replace(" ", "_").replace(".", "")
            self.tree.heading(col, text=f"{col} ⧗", command=lambda f=field_key, c=col: self.show_filter_menu(f, c))

        for name, w, a in [("DATA", 90, "center"), ("TIPO", 90, "center"), ("NUMERO", 100, "center"),
                           ("SOGGETTO", 180, "w"), ("TOTALE", 100, "e"), ("SCADENZA", 90, "center"),
                           ("PAGAMENTI", 110, "e"), ("RESIDUO", 100, "e"), ("TIPO PAG.", 100, "center"),
                           ("STATO", 90, "center")]:
            self.tree.column(name, width=w, anchor=a)

        scrollbar_y = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')
    
    def show_sort_menu(self):
        """Mostra un menu per selezionare l'ordinamento"""
        menu = tk.Menu(self, tearoff=0)
        
        if self.mode_scaduti:
            # Menu per dati scaduti
            current_mark_asc = " ✓" if self.sort_column == "ragione_sociale" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "ragione_sociale" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"👤 Ragione Sociale ↑ Crescente{current_mark_asc}", 
                            command=lambda: self.change_sort("ragione_sociale", "asc"))
            menu.add_command(label=f"👤 Ragione Sociale ↓ Decrescente{current_mark_desc}", 
                            command=lambda: self.change_sort("ragione_sociale", "desc"))
            menu.add_separator()
            current_mark_asc = " ✓" if self.sort_column == "saldo_scaduto" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "saldo_scaduto" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"💰 Saldo ↑ Crescente{current_mark_asc}", 
                            command=lambda: self.change_sort("saldo_scaduto", "asc"))
            menu.add_command(label=f"💰 Saldo ↓ Decrescente{current_mark_desc}", 
                            command=lambda: self.change_sort("saldo_scaduto", "desc"))
            menu.add_separator()
            current_mark_asc = " ✓" if self.sort_column == "numero_scadenze" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "numero_scadenze" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"🔢 N° Scadenze ↑ Crescente{current_mark_asc}", 
                            command=lambda: self.change_sort("numero_scadenze", "asc"))
            menu.add_command(label=f"🔢 N° Scadenze ↓ Decrescente{current_mark_desc}", 
                            command=lambda: self.change_sort("numero_scadenze", "desc"))
        else:
            # Menu per documenti
            current_mark_asc = " ✓" if self.sort_column == "data" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "data" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"📅 Data ↑ Crescente (più vecchie){current_mark_asc}", 
                            command=lambda: self.change_sort("data", "asc"))
            menu.add_command(label=f"📅 Data ↓ Decrescente (più recenti){current_mark_desc}", 
                            command=lambda: self.change_sort("data", "desc"))
            menu.add_separator()
            current_mark_asc = " ✓" if self.sort_column == "numero" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "numero" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"🔢 Numero ↑ Crescente{current_mark_asc}", 
                            command=lambda: self.change_sort("numero", "asc"))
            menu.add_command(label=f"🔢 Numero ↓ Decrescente{current_mark_desc}", 
                            command=lambda: self.change_sort("numero", "desc"))
            menu.add_separator()
            current_mark_asc = " ✓" if self.sort_column == "soggetto" and self.sort_direction == "asc" else ""
            current_mark_desc = " ✓" if self.sort_column == "soggetto" and self.sort_direction == "desc" else ""
            menu.add_command(label=f"👤 Soggetto ↑ Crescente (A-Z){current_mark_asc}", 
                            command=lambda: self.change_sort("soggetto", "asc"))
            menu.add_command(label=f"👤 Soggetto ↓ Decrescente (Z-A){current_mark_desc}", 
                            command=lambda: self.change_sort("soggetto", "desc"))
        
        # Posiziona il menu sotto il pulsante
        x = self.sort_btn.winfo_rootx()
        y = self.sort_btn.winfo_rooty() + self.sort_btn.winfo_height()
        menu.post(x, y)
    
    def change_sort(self, column, direction):
        """Cambia l'ordinamento"""
        self.sort_column = column
        self.sort_direction = direction
        
        # Salva la preferenza
        self.save_sort_preference()
        
        # Aggiorna l'etichetta
        self.update_sort_label()
        
        # Ricarica i dati con il nuovo ordinamento
        if self.mode_scaduti:
            self.load_data_scaduti()
        else:
            self.load_data()
    
    def update_sort_label(self):
        """Aggiorna l'etichetta che mostra l'ordinamento attivo"""
        if not hasattr(self, 'sort_label'):
            return
        
        # Mappa nomi colonne a etichette
        column_labels = {
            'data': 'Data',
            'numero': 'Numero',
            'soggetto': 'Soggetto',
            'ragione_sociale': 'Ragione Sociale',
            'saldo_scaduto': 'Saldo',
            'numero_scadenze': 'N° Scadenze'
        }
        
        # Simbolo direzione
        direction_symbol = "↑" if self.sort_direction == "asc" else "↓"
        direction_text = "Crescente" if self.sort_direction == "asc" else "Decrescente"
        
        # Testo etichetta
        column_label = column_labels.get(self.sort_column, self.sort_column)
        self.sort_label.config(text=f"{column_label} {direction_symbol} ({direction_text})")

    def show_filter_menu(self, field_name, column_title):
        win = tk.Toplevel(self)
        win.title(f"Filtro - {column_title}")
        # Dimensioni maggiori per il campo soggetto (con listbox)
        if field_name == "soggetto":
            win.geometry("400x350")
        else:
            win.geometry("320x200")
            win.configure(bg=Style.WHITE)
            win.resizable(False, False)
            win.transient(self)
            win.grab_set()
        
        frame = tk.Frame(win, bg=Style.WHITE, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=f"Filtro per {column_title}:", bg=Style.WHITE,
                 fg="#000", font=("Arial", 10, "bold")).pack(pady=(0, 10))

        if field_name == "data":
            tk.Label(frame, text="Dal:", bg=Style.WHITE).pack()
            dal_entry = DateEntry(frame, date_pattern="dd/mm/yyyy", width=15)
            dal_entry.pack(pady=(0, 5))
            tk.Label(frame, text="Al:", bg=Style.WHITE).pack()
            al_entry = DateEntry(frame, date_pattern="dd/mm/yyyy", width=15)
            al_entry.pack(pady=(0, 10))

            def apply_date():
                dal, al = dal_entry.get(), al_entry.get()
                self.active_filters["data"] = f"{dal}|{al}"
                self.apply_filters()
                win.destroy()

            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_date, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        elif field_name in ("soggetto", "tipo_pag", "stato"):
            vals = sorted({r[field_name] for r in self.original_data if r[field_name]})
            
            # Per il campo soggetto, usa autocompletamento con ricerca
            if field_name == "soggetto":
                # Frame per ricerca e lista
                search_frame = tk.Frame(frame, bg=Style.WHITE)
                search_frame.pack(fill="x", pady=(0, 10))
                
                tk.Label(search_frame, text="Cerca:", bg=Style.WHITE, 
                        font=("Arial", 9)).pack(side="left", padx=(0, 5))
                
                search_entry = tk.Entry(search_frame, font=("Arial", 10), width=20)
                search_entry.pack(side="left", fill="x", expand=True)
                
                # Focus dopo che la finestra è stata renderizzata
                def set_focus():
                    search_entry.focus_set()
                win.after(100, set_focus)
                
                # Listbox con scrollbar per i risultati filtrati
                listbox_frame = tk.Frame(frame, bg=Style.WHITE)
                listbox_frame.pack(fill="both", expand=True, pady=(0, 10))
                
                scrollbar = tk.Scrollbar(listbox_frame)
                scrollbar.pack(side="right", fill="y")
                
                listbox = tk.Listbox(listbox_frame, font=("Arial", 10), 
                                    yscrollcommand=scrollbar.set, height=8)
                listbox.pack(side="left", fill="both", expand=True)
                scrollbar.config(command=listbox.yview)
                
                # Popola la listbox con tutti i valori
                all_vals = [""] + vals
                for val in all_vals:
                    listbox.insert(tk.END, val)
                
                # Variabile per il valore selezionato
                selected_value = tk.StringVar()
                
                def filter_listbox(*args):
                    """Filtra la listbox in base al testo digitato"""
                    search_text = search_entry.get().lower()
                    listbox.delete(0, tk.END)
                    
                    if not search_text:
                        # Mostra tutti i valori se non c'è ricerca
                        filtered = [""] + vals
                    else:
                        # Filtra i valori che contengono il testo cercato
                        filtered = []
                        for val in vals:
                            if search_text in val.lower():
                                filtered.append(val)
                        
                        # Se non ci sono risultati, mostra un messaggio
                        if not filtered:
                            listbox.insert(tk.END, "(Nessun risultato)")
                            listbox.itemconfig(0, {'fg': '#999'})
                            return
                    
                    for val in filtered:
                        listbox.insert(tk.END, val)
                    
                    # Se c'è un solo risultato dopo il filtro, evidenzialo automaticamente
                    if len(filtered) == 1 and filtered[0]:
                        listbox.selection_set(0)
                        listbox.see(0)
                    elif len(filtered) > 1:
                        # Seleziona il primo risultato se c'è più di un match
                        listbox.selection_set(0)
                        listbox.see(0)
                
                def on_listbox_select(event):
                    """Gestisce la selezione dalla listbox"""
                    selection = listbox.curselection()
                    if selection:
                        selected_value.set(listbox.get(selection[0]))
                        search_entry.delete(0, tk.END)
                        search_entry.insert(0, selected_value.get())
                
                def on_listbox_double_click(event):
                    """Applica il filtro con doppio click"""
                    on_listbox_select(event)
                    apply_combo()
                
                def on_search_key(event):
                    """Gestisce i tasti nella ricerca"""
                    if event.keysym == 'Down':
                        listbox.focus_set()
                        if listbox.size() > 0:
                            listbox.selection_set(0)
                            listbox.see(0)
                        return "break"
                    elif event.keysym == 'Return':
                        # Se c'è una selezione nella listbox, usala
                        selection = listbox.curselection()
                        if selection:
                            selected_value.set(listbox.get(selection[0]))
                        apply_combo()
                        return "break"
                
                def on_listbox_key(event):
                    """Gestisce i tasti nella listbox"""
                    if event.keysym == 'Return':
                        apply_combo()
                        return "break"
                    elif event.keysym == 'Escape':
                        win.destroy()
                        return "break"
                    elif event.keysym == 'Up' and listbox.curselection()[0] == 0:
                        # Quando si arriva in cima, torna al campo ricerca
                        search_entry.focus_set()
                        return "break"
                
                search_entry.bind('<KeyRelease>', filter_listbox)
                search_entry.bind('<KeyPress>', on_search_key)
                listbox.bind('<<ListboxSelect>>', on_listbox_select)
                listbox.bind('<Double-Button-1>', on_listbox_double_click)
                listbox.bind('<KeyPress>', on_listbox_key)
                
                # Bind Escape per chiudere
                win.bind('<Escape>', lambda e: win.destroy())
                search_entry.bind('<Escape>', lambda e: win.destroy())
                
                # Mostra suggerimento
                hint_label = tk.Label(frame, 
                        text="💡 Digita per cercare, ↓↑ per navigare, Invio per applicare, Esc per chiudere", 
                        bg=Style.WHITE, fg="#666", font=("Arial", 8, "italic"))
                hint_label.pack(pady=(0, 5))
                
                def apply_combo():
                    # Prendi il valore dalla listbox se c'è una selezione, altrimenti dal campo ricerca
                    selection = listbox.curselection()
                    if selection:
                        val = listbox.get(selection[0])
                        # Ignora se è il messaggio "Nessun risultato"
                        if val == "(Nessun risultato)":
                            return
                    else:
                        val = search_entry.get().strip()
                        # Verifica se il valore esiste nella lista
                        if val not in vals:
                            # Cerca il primo match parziale che inizia con il testo
                            val_lower = val.lower()
                            for v in vals:
                                if v.lower().startswith(val_lower):
                                    val = v
                                    break
                            else:
                                # Se non trova un match che inizia, cerca qualsiasi match
                                for v in vals:
                                    if val_lower in v.lower():
                                        val = v
                                        break
                                else:
                                    val = ""  # Nessun match trovato
                    
                    self.active_filters[field_name] = val.lower() if val else ""
                    self.apply_filters()
                    win.destroy()
            else:
                # Per tipo_pag e stato, mantieni la combobox normale
                combo = ttk.Combobox(frame, values=[""] + vals, state="readonly", width=25)
                combo.pack(pady=(0, 15))
                
                def apply_combo():
                    self.active_filters[field_name] = combo.get().lower()
                    self.apply_filters()
                    win.destroy()
                
                tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                          width=10, command=apply_combo, cursor="hand2").pack(side="left", padx=5)
                tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                          width=10, command=win.destroy, cursor="hand2").pack(side="left")
                
                combo.bind('<Return>', lambda e: apply_combo())
        else:
            entry = tk.Entry(frame, font=("Arial", 10), width=25)
            entry.insert(0, self.active_filters.get(field_name, ""))
            entry.pack(pady=(0, 15))
            entry.focus()
            
            def apply_text():
                self.active_filters[field_name] = entry.get().strip().lower()
                self.apply_filters()
                win.destroy()
            
            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_text, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
            
            entry.bind('<Return>', lambda e: apply_text())
            win.bind('<Escape>', lambda e: win.destroy())

    def apply_filters(self):
        """Applica i filtri ai dati e aggiorna la visualizzazione"""
        # Se siamo in modalità scaduti, non processare qui
        if self.mode_scaduti:
            return
        
        res = []
        for row in self.original_data:
            # Verifica che la riga abbia i campi dei documenti (non scaduti)
            if 'data' not in row or 'tipo' not in row:
                continue
            
            # Filtro per tab (basato sul tipo di documento e segno)
            tipo = row.get('tipo', '').lower()
            segno = row.get('segno')
            
            if self.current_tab_filter == 'acquisti':
                # Mostra documenti di acquisto (fatture passive, DDT in ingresso, note di credito fornitori, ecc.)
                # IMPORTANTE: Escludi esplicitamente le note di credito clienti
                
                # Prima verifica: se è una nota di credito cliente, escludila da acquisti
                # Case-insensitive: controlla sia maiuscole che minuscole
                is_nc_cliente = ('nc_cliente' in tipo or 'nota_credito_cliente' in tipo or 
                                'NC_CLIENTE' in row.get('tipo', '') or 'NOTA_CREDITO_CLIENTE' in row.get('tipo', ''))
                if is_nc_cliente:
                    continue
                
                # Usa segno se disponibile, altrimenti usa tipo_documento
                is_acquisto = False
                if segno is not None:
                    # Se segno = -1 (fatture passive) o segno = 1 per nc_fornitore (nota credito fornitore)
                    # Ma NON se è nc_cliente (già escluso sopra)
                    is_acquisto = (segno == -1) or (segno == 1 and ('nc_fornitore' in tipo or 'NC_FORNITORE' in row.get('tipo', '')))
                else:
                    # Fallback su tipo_documento
                    is_acquisto = any(x in tipo for x in ['passiv', 'acquist', 'costo', 'spesa', 'nc_fornitore', 'nota_credito_fornitore',
                                                          'NC_FORNITORE', 'NOTA_CREDITO_FORNITORE'])
                
                if not is_acquisto:
                    continue
            elif self.current_tab_filter == 'vendite':
                # Mostra documenti di vendita (fatture attive, DDT in uscita, note di credito clienti, ecc.)
                # IMPORTANTE: Include esplicitamente le note di credito clienti
                
                # Usa segno se disponibile, altrimenti usa tipo_documento
                is_vendita = False
                if segno is not None:
                    # Se segno = 1 (fatture attive) o segno = -1 per nc_cliente (nota credito cliente)
                    tipo_upper = row.get('tipo', '').upper()
                    is_vendita = (segno == 1) or (segno == -1 and ('nc_cliente' in tipo or 'nota_credito_cliente' in tipo or
                                                                   'NC_CLIENTE' in tipo_upper or 'NOTA_CREDITO_CLIENTE' in tipo_upper))
                else:
                    # Fallback su tipo_documento
                    tipo_upper = row.get('tipo', '').upper()
                    is_vendita = any(x in tipo for x in ['attiv', 'vendit', 'ricav', 'incass', 'nc_cliente', 'nota_credito_cliente']) or \
                                any(x in tipo_upper for x in ['ATTIV', 'VENDIT', 'RICAV', 'INCASS', 'NC_CLIENTE', 'NOTA_CREDITO_CLIENTE'])
                
                if not is_vendita:
                    continue
            # Se 'tutti', nessun filtro sulla tipologia
            
            # Filtri aggiuntivi dall'utente
            ok = True
            for k, v in self.active_filters.items():
                if not v:
                    continue
                if k == "data" and "|" in v:
                    dal, al = v.split("|")
                    try:
                        d = datetime.strptime(row["data"], "%d/%m/%Y")
                        if dal:
                            if d < datetime.strptime(dal, "%d/%m/%Y"): 
                                ok = False
                                break
                        if al:
                            if d > datetime.strptime(al, "%d/%m/%Y"): 
                                ok = False
                                break
                    except:
                        ok = False
                        break
                elif v not in row[k].lower():
                    ok = False
                    break
            if ok: 
                res.append(row)
        
        self.update_table_display(res)

    def configure_style(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview.Heading", background=Style.MENU_HEADER_BG,
                        foreground=Style.MENU_HEADER_FG, font=("Arial", 10, "bold"),
                        padding=(5, 8), relief="solid", borderwidth=1,
                        lightcolor="#E0E0E0", darkcolor="#E0E0E0")
        style.configure("Treeview", font=("Arial", 9), rowheight=26,
                        background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF",
                        borderwidth=1, relief="solid", lightcolor="#E8E8E8", darkcolor="#E8E8E8")
        style.map("Treeview", background=[('selected', '#4b6cb7')], foreground=[('selected', 'white')])

    def get_db_path(self):
        c = configparser.ConfigParser()
        c.read("config.ini", encoding="utf-8")
        return c.get("Autenticazione", "percorso_database", fallback="./database.db")

    def get_cartella_ricevute(self):
        try:
            cartella = get_cartella_ricevute()
            return cartella if cartella else "./ricevute"
        except Exception:
            return "./ricevute"
    
    def get_sort_preference(self, key, default):
        """Legge le preferenze di ordinamento dal config.ini"""
        try:
            c = configparser.ConfigParser()
            c.read("config.ini", encoding="utf-8")
            return c.get("Ordinamento", f"documenti_{key}", fallback=default)
        except:
            return default
    
    def save_sort_preference(self):
        """Salva le preferenze di ordinamento nel config.ini"""
        try:
            c = configparser.ConfigParser()
            c.read("config.ini", encoding="utf-8")
            
            # Crea la sezione se non esiste
            if not c.has_section("Ordinamento"):
                c.add_section("Ordinamento")
            
            c.set("Ordinamento", "documenti_column", self.sort_column)
            c.set("Ordinamento", "documenti_direction", self.sort_direction)
            
            with open("config.ini", "w", encoding="utf-8") as f:
                c.write(f)
        except Exception as e:
            print(f"Errore nel salvataggio preferenze ordinamento: {e}")

    def load_data(self):
        """Carica i dati dalla tabella documenti"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Determina l'ordinamento SQL in base alle preferenze
            if self.sort_column == "numero":
                order_by = f"d.numero_documento {self.sort_direction.upper()}"
            elif self.sort_column == "soggetto":
                order_by = f"s.ragione_sociale {self.sort_direction.upper()}"
            else:  # default: data
                order_by = f"d.data_documento {self.sort_direction.upper()}"
            
            # Verifica se la colonna segno esiste
            cur.execute("PRAGMA table_info(documenti)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_segno = 'segno' in colonne_nomi
            
            # Costruisci la query includendo segno se presente
            if has_segno:
                query = f"""
                    SELECT d.id, d.data_documento, d.tipo_documento, d.numero_documento,
                           s.ragione_sociale, SUM(sc.importo_scadenza),
                           substr(sc.data_scadenza,1,2)||'/'||substr(sc.data_scadenza,4,2)||'/'||substr(sc.data_scadenza,7,4),
                           (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                            FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id),
                           CASE 
                               WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') AND d.segno = -1 THEN
                                   -- Per note di credito cliente: residuo = ABS(importo) - applicato (mostrato come positivo)
                                   ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                      FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                               ELSE
                                   -- Per documenti normali: residuo = importo - pagato - storni
                                   SUM(sc.importo_scadenza)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                           END,
                           (SELECT tipo_pagamento FROM scadenze WHERE id_documento=d.id
                            GROUP BY tipo_pagamento ORDER BY COUNT(*) DESC LIMIT 1),
                           CASE 
                               WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') AND d.segno = -1 THEN
                                   -- Per note di credito cliente: saldato se ABS(importo) - applicato <= 0
                                   CASE WHEN ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                              FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) <= 0 
                                        THEN 'SALDATO'
                                        WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                        THEN 'SCADUTO' 
                                        ELSE 'SOSPESO' 
                                   END
                               ELSE
                                   -- Per documenti normali
                                   CASE WHEN SUM(sc.importo_scadenza)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)<=0 THEN 'SALDATO'
                                        WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                        THEN 'SCADUTO' ELSE 'SOSPESO' END
                           END,
                           d.segno
                    FROM documenti d
                    LEFT JOIN soggetti s ON s.id=d.soggetto_id
                    JOIN scadenze sc ON d.id=sc.id_documento
                    GROUP BY d.id ORDER BY {order_by}
                """
            else:
                query = f"""
                    SELECT d.id, d.data_documento, d.tipo_documento, d.numero_documento,
                           s.ragione_sociale, SUM(sc.importo_scadenza),
                           substr(sc.data_scadenza,1,2)||'/'||substr(sc.data_scadenza,4,2)||'/'||substr(sc.data_scadenza,7,4),
                           (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                            FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id),
                           CASE 
                               WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') THEN
                                   -- Per note di credito cliente: residuo = ABS(importo) - applicato (mostrato come positivo)
                                   ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                      FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                               ELSE
                                   -- Per documenti normali: residuo = importo - pagato - storni
                                   SUM(sc.importo_scadenza)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                           END,
                           (SELECT tipo_pagamento FROM scadenze WHERE id_documento=d.id
                            GROUP BY tipo_pagamento ORDER BY COUNT(*) DESC LIMIT 1),
                           CASE 
                               WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') THEN
                                   -- Per note di credito cliente: saldato se ABS(importo) - applicato <= 0
                                   CASE WHEN ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                              FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) <= 0 
                                        THEN 'SALDATO'
                                        WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                        THEN 'SCADUTO' 
                                        ELSE 'SOSPESO' 
                                   END
                               ELSE
                                   -- Per documenti normali
                                   CASE WHEN SUM(sc.importo_scadenza)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                     FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)<=0 THEN 'SALDATO'
                                        WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                        THEN 'SCADUTO' ELSE 'SOSPESO' END
                           END,
                           NULL as segno
                    FROM documenti d
                    LEFT JOIN soggetti s ON s.id=d.soggetto_id
                    JOIN scadenze sc ON d.id=sc.id_documento
                    GROUP BY d.id ORDER BY {order_by}
                """
            
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            
            self.original_data = []
            for r in rows:
                data_str = r[1]
                if data_str and '-' in data_str:
                    try: 
                        data_str = datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                    except: 
                        pass
                
                # Estrai segno se presente (ultimo campo, indice 11)
                segno = r[11] if len(r) > 11 else None
                # Converti segno a int se è stringa
                if segno is not None:
                    try:
                        segno = int(segno) if isinstance(segno, (int, str)) and str(segno).strip() else None
                    except:
                        segno = None
                
                self.original_data.append({
                    'id': r[0], 
                    'data': data_str or "", 
                    'tipo': str(r[2]) or "",
                    'numero': str(r[3]) or "", 
                    'soggetto': str(r[4]) or "",
                    'totale': f"€ {r[5]:,.2f}" if r[5] else "€ 0.00",
                    'scadenza': str(r[6]) or "", 
                    'pagamenti': f"€ {r[7]:,.2f}" if r[7] else "€ 0.00",
                    'residuo': f"€ {r[8]:,.2f}" if r[8] else "€ 0.00",
                    'tipo_pag': str(r[9]) or "N/A", 
                    'stato': str(r[10]) or "",
                    'segno': segno
                })
            self.apply_filters()
        except Exception as e:
            messagebox.showerror("Errore DB", str(e))
            print(f"Errore caricamento dati: {e}")
    
    def load_data_scaduti(self):
        """Carica i dati dalle viste scaduto_clienti e scaduto_fornitori"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Determina l'ordinamento SQL in base alle preferenze
            order_mapping = {
                'ragione_sociale': 'ragione_sociale',
                'saldo_scaduto': 'saldo_scaduto',
                'numero_scadenze': 'numero_scadenze_scadute'
            }
            order_column = order_mapping.get(self.sort_column, 'ragione_sociale')
            order_by = f"{order_column} {self.sort_direction.upper()}"
            
            # Carica i dati da entrambe le viste con UNION
            cursor.execute(f"""
                SELECT soggetto_id, codice_soggetto, ragione_sociale, 
                       numero_scadenze_scadute, totale_scadenze, 
                       totale_pagato, saldo_scaduto,
                       'cliente' as tipo_origine
                FROM scaduto_clienti
                
                UNION ALL
                
                SELECT soggetto_id, codice_soggetto, ragione_sociale, 
                       numero_scadenze_scadute, totale_scadenze, 
                       totale_pagato, saldo_scaduto,
                       'fornitore' as tipo_origine
                FROM scaduto_fornitori
                
                ORDER BY {order_by}
            """)
            rows = cursor.fetchall()
            conn.close()

            # Salva i dati originali
            self.original_data = []
            for row in rows:
                self.original_data.append({
                    'soggetto_id': row[0],
                    'codice_soggetto': str(row[1]) if row[1] else "",
                    'ragione_sociale': str(row[2]) if row[2] else "",
                    'numero_scadenze': row[3] if row[3] else 0,
                    'totale_scadenze': row[4] if row[4] else 0.0,
                    'totale_pagato': row[5] if row[5] else 0.0,
                    'saldo_scaduto': row[6] if row[6] else 0.0,
                    'tipo_origine': str(row[7]).lower() if row[7] else ""
                })

            # Applica i filtri
            self.apply_filters_scaduti()

        except Exception as e:
            messagebox.showerror("Errore DB", str(e))
            print(f"Errore nel caricamento dati scaduti: {e}")
    
    def apply_filters_scaduti(self):
        """Applica i filtri in base alla tab attiva per i dati scaduti"""
        filtered_data = []
        
        for row in self.original_data:
            tipo_origine = row.get('tipo_origine', '').lower()
            
            if self.current_tab_filter == 'scaduto_clienti':
                if tipo_origine != 'cliente':
                    continue
            elif self.current_tab_filter == 'scaduto_fornitori':
                if tipo_origine != 'fornitore':
                    continue
            
            filtered_data.append(row)
        
        self.update_table_display_scaduti(filtered_data)
    
    def update_table_display_scaduti(self, data):
        """Aggiorna la visualizzazione della tabella per dati scaduti"""
        # Pulisci tabella
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Inserisci righe con formattazione
        for i, row in enumerate(data):
            values = (
                row['codice_soggetto'].upper(),
                row['ragione_sociale'].upper(),
                row['numero_scadenze'],
                f"€ {row['totale_scadenze']:,.2f}",
                f"€ {row['totale_pagato']:,.2f}",
                f"€ {row['saldo_scaduto']:,.2f}"
            )
            
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            # Salva soggetto_id come tag per poterlo recuperare dopo
            tags = (tag, f"soggetto_{row['soggetto_id']}")
            self.tree.insert("", tk.END, values=values, tags=tags)
        
        # Aggiorna il contatore
        tab_label = {
            'scaduto_clienti': 'Clienti',
            'scaduto_fornitori': 'Fornitori'
        }
        
        # Calcola il totale del saldo scaduto
        totale_saldo = sum(row['saldo_scaduto'] for row in data)
        
        label = tab_label.get(self.current_tab_filter, 'Soggetti')
        self.counter_label.config(
            text=f"{len(data)} {label} | Totale: € {totale_saldo:,.2f}"
        )

    def update_table_display(self, data):
        """Aggiorna la visualizzazione della tabella con i dati filtrati"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        for n, r in enumerate(data):
            vals = [r['data'], r['tipo'], r['numero'], r['soggetto'], r['totale'],
                    r['scadenza'], r['pagamenti'], r['residuo'], r['tipo_pag'], r['stato']]
            self.tree.insert("", tk.END, values=vals,
                             tags=('evenrow' if n % 2 == 0 else 'oddrow', f"id_{r['id']}"))
        
        # Aggiorna il contatore (solo per documenti, non per scaduti)
        if not self.mode_scaduti:
            tab_label = {
                'acquisti': 'Documenti Acquisto',
                'vendite': 'Documenti Vendita'
            }
            label = tab_label.get(self.current_tab_filter, 'Documenti')
            self.counter_label.config(
                text=f"{len(data)} {label} visualizzati"
            )

    def nuovo_documento(self):
        """Apre la finestra per creare un nuovo documento"""
        NuovoDocumentoWindow(self, self.db_path).set_callback_success(self.load_data)

    def modifica_documento(self):
        """Apre la finestra per modificare il documento selezionato"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un documento da modificare.")
            return
        if len(sel) > 1:
            messagebox.showwarning("Attenzione", "Seleziona un solo documento.")
            return
        tags = self.tree.item(sel[0], "tags")
        doc_id = None
        for t in tags:
            if t.startswith("id_"): 
                doc_id = int(t[3:])
        if not doc_id:
            messagebox.showerror("Errore", "Impossibile identificare il documento.")
            return
        ModificaDocumentoWindow(self, doc_id, self.db_path).set_callback_success(self.load_data)

    def cancella_documento(self):
        """Elimina i documenti selezionati"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona almeno un documento da cancellare.")
            return
        msg = f"Sei sicuro di voler cancellare {len(sel)} documento/i?"
        if not messagebox.askyesno("Conferma", msg): 
            return
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            for i in sel:
                tags = self.tree.item(i, "tags")
                doc_id = None
                for t in tags:
                    if t.startswith("id_"): 
                        doc_id = int(t[3:])
                if not doc_id: 
                    continue
                
                # Gestisci il movimento del plafond se il documento è agganciato a una dichiarazione
                self._rimuovi_movimento_plafond_documento(c, doc_id)
                
                # Elimina prima le associazioni pagamenti collegate al documento
                c.execute("DELETE FROM associazioni_pagamenti WHERE id_documento=?", (doc_id,))
                # Elimina le scadenze
                c.execute("DELETE FROM scadenze WHERE id_documento=?", (doc_id,))
                # Elimina il documento
                c.execute("DELETE FROM documenti WHERE id=?", (doc_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Eliminati", "Documenti eliminati con successo.")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def _rimuovi_movimento_plafond_documento(self, cursor, documento_id):
        """Rimuove il movimento del plafond associato a un documento e ripristina il residuo"""
        try:
            # Verifica se il documento è agganciato a una dichiarazione
            cursor.execute("""
                SELECT id_dichiarazione_intento FROM documenti WHERE id = ?
            """, (documento_id,))
            risultato = cursor.fetchone()
            id_dichiarazione = risultato[0] if risultato and risultato[0] else None
            
            if id_dichiarazione:
                # Verifica se esiste un movimento per questo documento
                cursor.execute("""
                    SELECT id, importo_consumato FROM consumo_plafond
                    WHERE id_dichiarazione = ? AND id_documento = ?
                """, (id_dichiarazione, documento_id))
                movimento = cursor.fetchone()
                
                if movimento:
                    movimento_id, importo_movimento = movimento
                    # Elimina il movimento
                    # Il plafond_residuo viene calcolato automaticamente dalla vista
                    cursor.execute("DELETE FROM consumo_plafond WHERE id = ?", (movimento_id,))
        except Exception:
            # Ignora errori se le tabelle non esistono o altri problemi
            pass

    def importa_acquisti(self):
        """Apre la finestra per importare documenti di acquisto"""
        folder = self.get_cartella_ricevute()
        if not os.path.exists(folder):
            messagebox.showerror("Errore", f"Cartella non trovata:\n{folder}")
            return
        ImportaDocumentoWindow(self, self.db_path, folder).set_callback_success(self.load_data)

    def importa_vendite(self):
        """Apre la finestra per importare documenti di vendita"""
        try:
            folder = self.get_cartella_ricevute()
            
            if not os.path.exists(folder):
                messagebox.showerror("Errore", f"Cartella non trovata:\n{folder}")
                return
            
            ImportaDocumentoVenditeWindow(self, self.db_path, folder).set_callback_success(self.load_data)
                
        except Exception as e:
            print(f"Errore in importa_vendite: {e}")
            messagebox.showerror("Errore", f"Impossibile aprire la finestra di importazione vendite:\n{str(e)}")

    def importa_rapido(self):
        """Importa XML direttamente dalla cartella specificata nel database senza interazione utente"""
        try:
            # Leggi il percorso dal database
            folder = get_import_rapido()
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Errore", f"Cartella non trovata o non configurata:\n{folder}\n\nVerifica il percorso nel database (tabella parametri, campo importarapido)")
                return
            
            # Mostra finestra di progresso
            win = tk.Toplevel(self)
            win.title("Import Rapido")
            win.geometry("600x550")
            win.transient(self)
            win.resizable(False, False)
            win.configure(bg="#FFFFFF")
            
            main_frame = tk.Frame(win, bg="#FFFFFF", padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            tk.Label(main_frame, text="📁 Import Rapido", bg="#FFFFFF", 
                    fg="#1976D2", font=("Arial", 14, "bold")).pack(pady=(0, 10))
            
            tk.Label(main_frame, text=f"Cartella: {folder}", bg="#FFFFFF", 
                    fg="#666", font=("Arial", 9)).pack(pady=(0, 20))
            
            text_area = scrolledtext.ScrolledText(main_frame, width=70, height=15, 
                                                 font=("Consolas", 9), bg="#F5F5F5")
            text_area.pack(fill="both", expand=True, pady=(0, 10))
            text_area.config(state='disabled')
            
            def aggiungi_messaggio(msg, end='\n'):
                text_area.config(state='normal')
                text_area.insert(tk.END, msg + end)
                text_area.see(tk.END)
                text_area.config(state='disabled')
                win.update_idletasks()
            
            btn_chiudi = tk.Button(main_frame, text="Chiudi", command=win.destroy,
                                  bg="#607D8B", fg="white", font=("Arial", 10, "bold"),
                                  cursor="hand2", padx=20, pady=5)
            btn_chiudi.pack(pady=(10, 0))
            btn_chiudi.config(state='disabled')
            
            def esegui_importazione():
                try:
                    from documenti_page_importa_vendite import ImportaFattureVenditaXML
                    
                    importatore = ImportaFattureVenditaXML(
                        self.db_path,
                        folder,
                        "config.ini",
                        callback=aggiungi_messaggio
                    )
                    importatore.esegui_importazione()
                    
                    aggiungi_messaggio("\n✅ Importazione completata!")
                    
                    # Mostra riepilogo delle fatture importate
                    if importatore.fatture_importate:
                        aggiungi_messaggio("\n" + "="*60)
                        aggiungi_messaggio("RIEPILOGO FATTURE IMPORTATE")
                        aggiungi_messaggio("="*60)
                        aggiungi_messaggio(f"\nTotale fatture importate: {len(importatore.fatture_importate)}")
                        
                        totale_generale = sum(f['totale'] for f in importatore.fatture_importate)
                        aggiungi_messaggio(f"Totale importo: € {totale_generale:,.2f}\n")
                        
                        aggiungi_messaggio("-" * 60)
                        aggiungi_messaggio(f"{'Numero':<15} {'Data':<12} {'Cliente':<30} {'Totale':>12}")
                        aggiungi_messaggio("-" * 60)
                        
                        for fattura in importatore.fatture_importate:
                            cliente_trunc = fattura['cliente'][:28] + '..' if len(fattura['cliente']) > 30 else fattura['cliente']
                            aggiungi_messaggio(f"{fattura['numero']:<15} {fattura['data']:<12} {cliente_trunc:<30} € {fattura['totale']:>10,.2f}")
                        
                        aggiungi_messaggio("-" * 60)
                        aggiungi_messaggio(f"{'TOTALE':<57} € {totale_generale:>10,.2f}")
                        aggiungi_messaggio("="*60)
                        
                        # Bottone per aggiungere pagamento
                        aggiungi_messaggio("\n")
                        aggiungi_messaggio("💡 Puoi aggiungere un pagamento direttamente da qui!")
                        
                        # Crea frame per il bottone
                        btn_frame = tk.Frame(main_frame, bg="#FFFFFF")
                        btn_frame.pack(pady=(10, 0))
                        
                        def apri_pagamento():
                            try:
                                from pagamenti_page_new import NuovoPagamentoWindow
                                
                                # Determina il soggetto (se c'è un solo cliente, lo pre-seleziona)
                                soggetti_importati = list(set(f['soggetto_id'] for f in importatore.fatture_importate))
                                
                                pagamento_win = NuovoPagamentoWindow(
                                    win, 
                                    self.db_path,
                                    on_save_callback=lambda: self.after(0, self.load_data)
                                )
                                
                                # Se c'è un solo soggetto, lo pre-seleziona
                                if len(soggetti_importati) == 1:
                                    soggetto_id = soggetti_importati[0]
                                    
                                    # Recupera le scadenze delle fatture appena importate
                                    documento_ids = [f['documento_id'] for f in importatore.fatture_importate if f['soggetto_id'] == soggetto_id]
                                    scadenze_ids = []
                                    if documento_ids:
                                        conn = sqlite3.connect(self.db_path)
                                        cur = conn.cursor()
                                        cur.execute("""
                                            SELECT id FROM scadenze 
                                            WHERE id_documento IN ({})
                                        """.format(','.join('?' * len(documento_ids))), documento_ids)
                                        scadenze_ids = [r[0] for r in cur.fetchall()]
                                        conn.close()
                                    
                                    # Trova l'indice del soggetto nella lista e selezionalo
                                    def selezione_automatica():
                                        try:
                                            for idx, (sid, nome) in enumerate(pagamento_win.soggetti):
                                                if sid == soggetto_id:
                                                    pagamento_win.soggetto_cb.current(idx)
                                                    pagamento_win.on_soggetto_selected(None)
                                                    # Aspetta che le scadenze siano caricate e poi selezionale
                                                    pagamento_win.after(100, pre_seleziona_scadenze)
                                                    break
                                        except Exception as e:
                                            print(f"Errore selezione automatica: {e}")
                                    
                                    def pre_seleziona_scadenze():
                                        try:
                                            # Seleziona le scadenze delle fatture appena importate
                                            for sc in pagamento_win.scadenze:
                                                if sc['scadenza_id'] in scadenze_ids:
                                                    sc['selected'] = True
                                            pagamento_win.refresh_treeview()
                                        except Exception as e:
                                            print(f"Errore pre-selezione scadenze: {e}")
                                    
                                    # Aspetta che la finestra sia completamente renderizzata
                                    pagamento_win.after(50, selezione_automatica)
                                
                            except Exception as e:
                                messagebox.showerror("Errore", f"Errore nell'apertura della finestra pagamento:\n{str(e)}")
                        
                        btn_aggiungi_pag = tk.Button(
                            btn_frame,
                            text="💰 Aggiungi Pagamento",
                            command=apri_pagamento,
                            bg="#4CAF50",
                            fg="white",
                            font=("Arial", 11, "bold"),
                            cursor="hand2",
                            padx=20,
                            pady=10,
                            relief="flat"
                        )
                        btn_aggiungi_pag.pack()
                    
                    # Aggiorna i dati nella pagina principale
                    self.after(0, self.load_data)
                    
                except Exception as e:
                    aggiungi_messaggio(f"\n❌ ERRORE: {str(e)}")
                finally:
                    btn_chiudi.config(state='normal')
            
            # Avvia importazione in thread separato
            import threading
            thread = threading.Thread(target=esegui_importazione, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'importazione rapida:\n{str(e)}")
        except Exception as e:
            print(f"Errore in importa_rapido: {e}")
            messagebox.showerror("Errore", f"Errore durante l'importazione rapida:\n{str(e)}")
    
    def _update_dettaglio_sospese_button(self):
        """Aggiorna la visibilità del bottone dettaglio fatture sospese"""
        # Rimuovi il bottone esistente se presente
        if self.dettaglio_sospese_btn:
            self.dettaglio_sospese_btn.destroy()
            for widget in self.dettaglio_sospese_frame.winfo_children():
                widget.destroy()
            self.dettaglio_sospese_btn = None
        
        # Mostra il bottone solo nel tab scaduto clienti
        if self.current_tab_filter == 'scaduto_clienti':
            icon_size = (32, 32)
            button_size = 40
            try:
                img = Image.open("assets/icon/info.png")
                img = img.resize(icon_size, Image.Resampling.LANCZOS)
                icon = ImageTk.PhotoImage(img)
                btn = tk.Button(self.dettaglio_sospese_frame, image=icon, 
                                command=self.mostra_fatture_sospese,
                                bg=Style.BACKGROUND_COLOR, relief="flat",
                                cursor="hand2", width=button_size, height=button_size, borderwidth=0)
                btn.image = icon
                btn.pack()
                tk.Label(self.dettaglio_sospese_frame, text="Fatture Sospese", 
                        bg=Style.BACKGROUND_COLOR,
                        fg="#1f396a", font=("Arial", 10, "bold")).pack(pady=(8, 0))
                self.dettaglio_sospese_btn = btn
            except Exception as e:
                print(f"Errore caricamento icona info: {e}")
                btn = tk.Button(self.dettaglio_sospese_frame, text="Fatture Sospese", 
                               command=self.mostra_fatture_sospese, bg="#2196F3",
                               fg="white", font=("Arial", 11, "bold"), cursor="hand2", width=12, height=2)
                btn.pack()
                self.dettaglio_sospese_btn = btn
    
    def mostra_fatture_sospese(self):
        """Mostra il dettaglio delle fatture sospese per il cliente selezionato"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un cliente per visualizzare le fatture sospese.")
            return
        
        if len(sel) > 1:
            messagebox.showwarning("Attenzione", "Seleziona un solo cliente.")
            return
        
        # Recupera il soggetto_id dal tag
        tags = self.tree.item(sel[0], "tags")
        soggetto_id = None
        for tag in tags:
            if tag.startswith("soggetto_"):
                try:
                    # Il tag è formato come "soggetto_123"
                    soggetto_id = int(tag.split("_")[1])
                    break
                except (ValueError, IndexError) as e:
                    print(f"Errore nel parsing del tag: {tag}, errore: {e}")
                    continue
        
        if not soggetto_id:
            messagebox.showerror("Errore", f"Impossibile identificare il cliente. Tag trovati: {tags}")
            return
        
        # Recupera i dati del cliente
        cliente_data = None
        for row in self.original_data:
            if row.get('soggetto_id') == soggetto_id:
                cliente_data = row
                break
        
        if not cliente_data:
            messagebox.showerror("Errore", "Cliente non trovato.")
            return
        
        # Apri la finestra di dettaglio
        DettaglioFattureSospeseWindow(self, soggetto_id, cliente_data, self.db_path)


class DettaglioFattureSospeseWindow(tk.Toplevel):
    """Finestra per visualizzare il dettaglio delle fatture sospese per un cliente"""
    
    def __init__(self, parent, soggetto_id, cliente_data, db_path):
        super().__init__(parent)
        self.soggetto_id = soggetto_id
        self.cliente_data = cliente_data
        self.db_path = db_path
        
        self.title(f"Fatture Sospese - {cliente_data['ragione_sociale']}")
        self.geometry("1200x600")
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.transient(parent)
        
        # Frame principale
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Intestazione
        header_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text=f"Fatture Sospese - {cliente_data['ragione_sociale']}", 
                bg=Style.BACKGROUND_COLOR, fg="#1f396a", 
                font=("Arial", 16, "bold")).pack(side="left")
        
        tk.Label(header_frame, text=f"Codice: {cliente_data['codice_soggetto']}", 
                bg=Style.BACKGROUND_COLOR, fg="#666", 
                font=("Arial", 10)).pack(side="right")
        
        # Tabella
        table_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True)
        
        columns = ("DATA", "TIPO", "NUMERO", "SCADENZA", "IMPORTO", "PAGATO", "RESIDUO", "STATO")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("DATA", width=100, anchor="center")
        self.tree.column("TIPO", width=120, anchor="center")
        self.tree.column("NUMERO", width=120, anchor="center")
        self.tree.column("SCADENZA", width=100, anchor="center")
        self.tree.column("IMPORTO", width=120, anchor="e")
        self.tree.column("PAGATO", width=120, anchor="e")
        self.tree.column("RESIDUO", width=120, anchor="e")
        self.tree.column("STATO", width=100, anchor="center")
        
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')
        
        # Frame per totali
        totali_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        totali_frame.pack(fill="x", pady=(10, 0))
        
        self.totale_label = tk.Label(totali_frame, text="", bg=Style.BACKGROUND_COLOR, 
                                     fg="#1f396a", font=("Arial", 11, "bold"))
        self.totale_label.pack(side="right")
        
        # Bottone chiudi
        btn_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(btn_frame, text="Chiudi", command=self.destroy,
                 bg="#607D8B", fg="white", font=("Arial", 10, "bold"),
                 cursor="hand2", padx=20, pady=5).pack(side="right")
        
        # Carica i dati
        self.load_data()
    
    def load_data(self):
        """Carica le fatture sospese per il cliente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se la colonna segno esiste
            cursor.execute("PRAGMA table_info(documenti)")
            colonne_info = cursor.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_segno = 'segno' in colonne_nomi
            
            # Query per recuperare le fatture sospese (stato = 'SOSPESO')
            # Usiamo una CTE per poter filtrare correttamente per stato
            if has_segno:
                query = """
                    WITH documenti_calcolati AS (
                        SELECT d.id, d.data_documento, d.tipo_documento, d.numero_documento,
                               substr(sc.data_scadenza,1,2)||'/'||substr(sc.data_scadenza,4,2)||'/'||substr(sc.data_scadenza,7,4) as data_scadenza,
                               SUM(sc.importo_scadenza) as importo_totale,
                               (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) as pagato,
                               CASE 
                                   WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') AND d.segno = -1 THEN
                                       ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                          FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   ELSE
                                       SUM(sc.importo_scadenza)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                               END as residuo,
                               CASE 
                                   WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') AND d.segno = -1 THEN
                                       CASE WHEN ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                                  FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) <= 0 
                                            THEN 'SALDATO'
                                            WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                            THEN 'SCADUTO' 
                                            ELSE 'SOSPESO' 
                                       END
                                   ELSE
                                       CASE WHEN SUM(sc.importo_scadenza)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)<=0 THEN 'SALDATO'
                                            WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                            THEN 'SCADUTO' ELSE 'SOSPESO' END
                               END as stato
                        FROM documenti d
                        JOIN scadenze sc ON d.id = sc.id_documento
                        WHERE d.soggetto_id = ? AND d.segno = 1
                        GROUP BY d.id
                    )
                    SELECT id, data_documento, tipo_documento, numero_documento, data_scadenza, 
                           importo_totale, pagato, residuo, stato
                    FROM documenti_calcolati
                    WHERE stato = 'SOSPESO'
                    ORDER BY data_documento DESC
                """
            else:
                query = """
                    WITH documenti_calcolati AS (
                        SELECT d.id, d.data_documento, d.tipo_documento, d.numero_documento,
                               substr(sc.data_scadenza,1,2)||'/'||substr(sc.data_scadenza,4,2)||'/'||substr(sc.data_scadenza,7,4) as data_scadenza,
                               SUM(sc.importo_scadenza) as importo_totale,
                               (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) as pagato,
                               CASE 
                                   WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') THEN
                                       ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                          FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                   ELSE
                                       SUM(sc.importo_scadenza)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                               END as residuo,
                               CASE 
                                   WHEN (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%') THEN
                                       CASE WHEN ABS(SUM(sc.importo_scadenza)) - (SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                                                                  FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id) <= 0 
                                            THEN 'SALDATO'
                                            WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                            THEN 'SCADUTO' 
                                            ELSE 'SOSPESO' 
                                       END
                                   ELSE
                                       CASE WHEN SUM(sc.importo_scadenza)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)
                                       -(SELECT COALESCE(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END),0) 
                                         FROM associazioni_pagamenti ap WHERE ap.id_documento=d.id)<=0 THEN 'SALDATO'
                                            WHEN MAX(date(substr(sc.data_scadenza,7,4)||'-'||substr(sc.data_scadenza,4,2)||'-'||substr(sc.data_scadenza,1,2)))<date('now')
                                            THEN 'SCADUTO' ELSE 'SOSPESO' END
                               END as stato
                        FROM documenti d
                        JOIN scadenze sc ON d.id = sc.id_documento
                        WHERE d.soggetto_id = ?
                        GROUP BY d.id
                    )
                    SELECT id, data_documento, tipo_documento, numero_documento, data_scadenza, 
                           importo_totale, pagato, residuo, stato
                    FROM documenti_calcolati
                    WHERE stato = 'SOSPESO'
                    ORDER BY data_documento DESC
                """
            
            cursor.execute(query, (self.soggetto_id,))
            rows = cursor.fetchall()
            conn.close()
            
            # Debug: stampa il numero di righe trovate
            print(f"Fatture sospese trovate per soggetto_id {self.soggetto_id}: {len(rows)}")
            
            # Pulisci tabella
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            totale_residuo = 0.0
            totale_importo = 0.0
            totale_pagato = 0.0
            
            # Inserisci i dati
            for i, row in enumerate(rows):
                data_str = row[1]
                if data_str and '-' in data_str:
                    try:
                        data_str = datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                    except:
                        pass
                elif data_str and '/' in data_str:
                    # Già in formato DD/MM/YYYY
                    pass
                
                importo = float(row[5]) if row[5] else 0.0
                pagato = float(row[6]) if row[6] else 0.0
                residuo = float(row[7]) if row[7] else 0.0
                
                totale_importo += importo
                totale_pagato += pagato
                totale_residuo += residuo
                
                values = (
                    data_str or "",
                    str(row[2]) or "",
                    str(row[3]) or "",
                    str(row[4]) or "",
                    f"€ {importo:,.2f}",
                    f"€ {pagato:,.2f}",
                    f"€ {residuo:,.2f}",
                    str(row[8]) or ""
                )
                
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.tree.insert("", tk.END, values=values, tags=(tag,))
            
            # Aggiorna totali
            self.totale_label.config(
                text=f"Totale Importo: € {totale_importo:,.2f} | "
                     f"Totale Pagato: € {totale_pagato:,.2f} | "
                     f"Totale Residuo: € {totale_residuo:,.2f} | "
                     f"Numero Fatture: {len(rows)}"
            )
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei dati:\n{str(e)}")
            print(f"Errore caricamento fatture sospese: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Vista Scadenze Documenti")
    root.geometry("1300x700")
    app = VistaScadenzeApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()