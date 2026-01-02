import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import configparser
import os
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageTk

# per PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Importa gli stili
import sys
import os
# Aggiungi il percorso per gli stili (relativo alla root del progetto)
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
style_path = os.path.join(project_root, 'assets', 'style')
if style_path not in sys.path:
    sys.path.insert(0, style_path)
from styles import Style

# Importa finestre
sys.path.append('.')
# Aggiungi anche la directory gui al path per import relativi
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from pagamenti_page_new import NuovoPagamentoWindow
from pagamenti_page_riba import RibaTab


class PagamentiUnificatiApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.db_path = self.get_db_path()

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.original_data = []
        self.filtered_data_pagamenti = []  # Dati filtrati per pagamenti (per cancellazione)
        
        # Filtro attivo per la tab corrente
        self.current_tab_filter = "pagamenti"  # "pagamenti", "riba"
        
        # Filtri per pagamenti
        self.active_filters_pagamenti = {
            'data': '',
            'tipo_pag': '',
            'soggetto': '',
            'importo': '',
            'documento': ''
        }
        
        # Componente RiBa tab (verrà creato quando necessario)
        self.riba_tab = None
        
        # Impostazioni di ordinamento
        self.sort_column = 'data'
        self.sort_direction = 'desc'

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
        
        # Tab Pagamenti
        self.tab_buttons['pagamenti'] = tk.Button(
            tab_header_frame, 
            text="💳 PAGAMENTI",
            command=lambda: self.switch_tab('pagamenti'),
            **tab_style
        )
        self.tab_buttons['pagamenti'].pack(side="left", padx=(0, 5))
        
        # Tab RiBa
        self.tab_buttons['riba'] = tk.Button(
            tab_header_frame,
            text="📋 RIBA",
            command=lambda: self.switch_tab('riba'),
            **tab_style
        )
        self.tab_buttons['riba'].pack(side="left")
        
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
        
        # Crea la barra dei pulsanti subito dopo i tab (in alto)
        # Deve essere creata come attributo di istanza per poter essere distrutta e ricreata
        self.button_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        
        # Contenuto tab (tutto il resto)
        self.content_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        
        # Pack nell'ordine corretto: prima button_frame, poi content_frame
        self.button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(10, 10))
        self.content_frame.pack(fill="both", expand=True)
        
        # Crea la barra dei pulsanti (dopo aver creato content_frame per riferimento)
        self.create_button_bar()
        
        # Attiva la tab predefinita (questo creerà anche la tabella)
        self.switch_tab('pagamenti')

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
        
        # Rimuovi tutti i widget dal content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Crea il componente appropriato
        if tab_name == 'riba':
            # Usa RibaTab invece di creare la tabella manualmente
            self.riba_tab = RibaTab(self.content_frame, self.db_path)
            self.riba_tab.pack(fill="both", expand=True)
        else:
            # Crea la tabella pagamenti
            self.riba_tab = None
            self.switch_to_pagamenti_table()
            self.load_data()
        
        # Ricrea la barra pulsanti per mostrare i pulsanti corretti
        self.create_button_bar()

    def create_button_bar(self):
        """Crea la barra dei pulsanti - i pulsanti cambiano in base al tab"""
        # Rimuovi tutti i widget esistenti nel button_frame
        if hasattr(self, 'button_frame'):
            for widget in self.button_frame.winfo_children():
                widget.destroy()
        icon_size = (32, 32)
        button_size = 40

        def add_button(frame, icon_name, text, command, fallback_color):
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

        # Pulsanti in base al tab corrente
        if self.current_tab_filter == 'pagamenti':
            buttons = [
                ("nuovo", "Nuovo", self.nuovo_pagamento, "#4CAF50"),
                ("modifica", "Modifica", self.modifica_pagamento, "#FF9800"),
                ("cancella", "Cancella", self.cancella_pagamento, "#f44336"),
                ("filtri", "Cancella filtri", self.clear_all_filters, "#607D8B")
            ]
        else:  # riba
            # Delega i metodi a RibaTab
            buttons = [
                ("nuovo", "Nuova Distinta", lambda: self.riba_tab.nuova_distinta() if self.riba_tab else None, "#4CAF50"),
                ("modifica", "Gestisci Distinte", lambda: self.riba_tab.gestisci_distinte() if self.riba_tab else None, "#FF9800"),
                ("pagamenti_riba", "Paga RiBa", lambda: self.riba_tab.paga_riba() if self.riba_tab else None, "#00BCD4"),
                ("cancella", "Elimina", lambda: self.riba_tab.elimina_selezionati() if self.riba_tab else None, "#f44336"),
                ("filtri", "Cancella filtri", self.clear_all_filters, "#607D8B")
            ]
        
        for icon, text, cmd, color in buttons:
            frame = tk.Frame(self.button_frame, bg=Style.BACKGROUND_COLOR)
            frame.pack(side="left", padx=(0, 25))
            add_button(frame, icon, text, cmd, color)
        
        # Aggiungi pulsante ordinamento a destra
        sort_frame = tk.Frame(self.button_frame, bg=Style.BACKGROUND_COLOR)
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

    def clear_all_filters(self, silent=False):
        """Cancella tutti i filtri"""
        if self.current_tab_filter == 'pagamenti':
            for key in self.active_filters_pagamenti.keys():
                self.active_filters_pagamenti[key] = ""
            self.apply_filters()
        else:
            # Delega a RibaTab
            if self.riba_tab:
                self.riba_tab.clear_all_filters()
                return
        
        if not silent:
            messagebox.showinfo("Filtri", "Tutti i filtri sono stati rimossi.")

    def create_table(self):
        """Crea la tabella iniziale (per pagamenti)"""
        self.switch_to_pagamenti_table()
    
    def switch_to_pagamenti_table(self):
        """Crea/cambia la tabella per pagamenti"""
        # Rimuovi la tabella esistente se presente e valida
        if hasattr(self, 'table_frame'):
            try:
                # Verifica se il widget esiste ancora (non è stato distrutto)
                self.table_frame.winfo_exists()
                # Se esiste, distruggi i suoi widget figli
                for widget in self.table_frame.winfo_children():
                    widget.destroy()
            except (tk.TclError, AttributeError):
                # Il widget è stato distrutto, ricreiamolo
                self.table_frame = None
        
        # Crea table_frame se non esiste
        if not hasattr(self, 'table_frame') or self.table_frame is None:
            self.table_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
            self.table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        columns = ("DATA", "TIPO PAG.", "TIPO MOV.", "SOGGETTO", "IMPORTO", "SPESE", "DOCUMENTO")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        # Configura le intestazioni delle colonne
        # Solo alcune colonne hanno filtri
        filterable_columns = {
            "DATA": ("data", "DATA"),
            "TIPO PAG.": ("tipo_pag", "TIPO PAG."),
            "TIPO MOV.": ("tipo_movimento", "TIPO MOV."),
            "SOGGETTO": ("soggetto", "SOGGETTO")
        }
        
        for col in columns:
            field_key = col.lower().replace(" ", "_").replace(".", "")
            if col in filterable_columns:
                field_key, col_title = filterable_columns[col]
                self.tree.heading(col, text=f"{col} ⧗", command=lambda f=field_key, c=col_title: self.show_filter_menu(f, c))
            else:
                self.tree.heading(col, text=col)

        for name, w, a in [("DATA", 120, "center"), ("TIPO PAG.", 120, "center"), ("TIPO MOV.", 100, "center"), 
                           ("SOGGETTO", 250, "w"), ("IMPORTO", 120, "e"), ("SPESE", 100, "e"), ("DOCUMENTO", 200, "w")]:
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
    
    def switch_to_riba_table(self):
        """Crea/cambia la tabella per RiBa - DEPRECATO: ora usa RibaTab"""
        # Questo metodo non è più usato, ma lo manteniamo per compatibilità
        pass

    def get_db_path(self):
        """Ottiene il percorso del database"""
        config = configparser.ConfigParser()
        config.read("config.ini", encoding="utf-8")
        return config.get("Autenticazione", "percorso_database", fallback="./database.db")

    def configure_style(self):
        """Configura lo stile per la tabella"""
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

    # Metodi placeholder - da implementare
    def load_data(self):
        """Carica i dati in base al tab corrente"""
        if self.current_tab_filter == 'pagamenti':
            self.load_data_pagamenti()
        else:
            # Delega a RibaTab
            if self.riba_tab:
                self.riba_tab.load_data()
    
    def load_data_pagamenti(self):
        """Carica i dati dei pagamenti"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se esiste la colonna segno nella tabella documenti
            cursor.execute("PRAGMA table_info(documenti)")
            colonne_info = cursor.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_segno = 'segno' in colonne_nomi
            
            # Verifica se esiste la colonna tipo_movimento
            cursor.execute("PRAGMA table_info(pagamenti)")
            colonne_pagamenti = [col[1] for col in cursor.fetchall()]
            has_tipo_movimento = 'tipo_movimento' in colonne_pagamenti
            
            # Verifica se esiste la tabella associazioni_pagamenti
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='associazioni_pagamenti'
            """)
            has_associazioni = cursor.fetchone() is not None
            
            # Costruisci la query usando associazioni_pagamenti se disponibile, altrimenti fallback su pagamenti_scadenze
            if has_associazioni:
                # Usa la nuova struttura associazioni_pagamenti
                if has_segno and has_tipo_movimento:
                    query = """
                        SELECT 
                            p.id AS pagamento_id,
                            p.data_pagamento AS data_pagamento,
                            p.modalita_pagamento AS tipo_pagamento,
                            p.tipo_movimento AS tipo_movimento,
                            s.ragione_sociale AS soggetto,
                            ap.importo_associato AS importo,
                            p.spese AS spese,
                            d.tipo_documento AS tipo_documento,
                            d.numero_documento AS numero_documento,
                            d.data_documento AS data_documento,
                            d.segno AS segno,
                            ap.tipo_associazione AS tipo_associazione
                        FROM associazioni_pagamenti ap
                        JOIN pagamenti p ON ap.id_pagamento = p.id
                        JOIN documenti d ON ap.id_documento = d.id
                        LEFT JOIN soggetti s ON s.id = d.soggetto_id
                        ORDER BY p.data_pagamento DESC
                    """
                elif has_tipo_movimento:
                    query = """
                        SELECT 
                            p.id AS pagamento_id,
                            p.data_pagamento AS data_pagamento,
                            p.modalita_pagamento AS tipo_pagamento,
                            p.tipo_movimento AS tipo_movimento,
                            s.ragione_sociale AS soggetto,
                            ap.importo_associato AS importo,
                            p.spese AS spese,
                            d.tipo_documento AS tipo_documento,
                            d.numero_documento AS numero_documento,
                            d.data_documento AS data_documento,
                            NULL AS segno,
                            ap.tipo_associazione AS tipo_associazione
                        FROM associazioni_pagamenti ap
                        JOIN pagamenti p ON ap.id_pagamento = p.id
                        JOIN documenti d ON ap.id_documento = d.id
                        LEFT JOIN soggetti s ON s.id = d.soggetto_id
                        ORDER BY p.data_pagamento DESC
                    """
                else:
                    # Fallback: usa pagamenti_scadenze se tipo_movimento non esiste
                    query = """
                        SELECT 
                            p.id AS pagamento_id,
                            p.data_pagamento AS data_pagamento,
                            p.modalita_pagamento AS tipo_pagamento,
                            NULL AS tipo_movimento,
                            s.ragione_sociale AS soggetto,
                            ps.importo AS importo,
                            p.spese AS spese,
                            d.tipo_documento AS tipo_documento,
                            d.numero_documento AS numero_documento,
                            d.data_documento AS data_documento,
                            NULL AS segno,
                            'PAGAMENTO' AS tipo_associazione
                        FROM pagamenti_scadenze ps
                        JOIN pagamenti p ON ps.pagamento_id = p.id
                        JOIN scadenze sc ON ps.scadenza_id = sc.id
                        JOIN documenti d ON sc.id_documento = d.id
                        LEFT JOIN soggetti s ON s.id = d.soggetto_id
                        ORDER BY p.data_pagamento DESC
                    """
            else:
                # Fallback: usa pagamenti_scadenze se associazioni_pagamenti non esiste
                if has_segno:
                    query = """
                        SELECT 
                            p.id AS pagamento_id,
                            p.data_pagamento AS data_pagamento,
                            p.modalita_pagamento AS tipo_pagamento,
                            COALESCE(p.tipo_movimento, 'INCASSO') AS tipo_movimento,
                            s.ragione_sociale AS soggetto,
                            ps.importo AS importo,
                            p.spese AS spese,
                            d.tipo_documento AS tipo_documento,
                            d.numero_documento AS numero_documento,
                            d.data_documento AS data_documento,
                            d.segno AS segno,
                            'PAGAMENTO' AS tipo_associazione
                        FROM pagamenti_scadenze ps
                        JOIN pagamenti p ON ps.pagamento_id = p.id
                        JOIN scadenze sc ON ps.scadenza_id = sc.id
                        JOIN documenti d ON sc.id_documento = d.id
                        LEFT JOIN soggetti s ON s.id = d.soggetto_id
                        ORDER BY p.data_pagamento DESC
                    """
                else:
                    query = """
                        SELECT 
                            p.id AS pagamento_id,
                            p.data_pagamento AS data_pagamento,
                            p.modalita_pagamento AS tipo_pagamento,
                            COALESCE(p.tipo_movimento, 'INCASSO') AS tipo_movimento,
                            s.ragione_sociale AS soggetto,
                            ps.importo AS importo,
                            p.spese AS spese,
                            d.tipo_documento AS tipo_documento,
                            d.numero_documento AS numero_documento,
                            d.data_documento AS data_documento,
                            NULL AS segno,
                            'PAGAMENTO' AS tipo_associazione
                        FROM pagamenti_scadenze ps
                        JOIN pagamenti p ON ps.pagamento_id = p.id
                        JOIN scadenze sc ON ps.scadenza_id = sc.id
                        JOIN documenti d ON sc.id_documento = d.id
                        LEFT JOIN soggetti s ON s.id = d.soggetto_id
                        ORDER BY p.data_pagamento DESC
                    """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            self.original_data = []
            for row in rows:
                # Estrai i campi (ora abbiamo tipo_movimento e tipo_associazione)
                tipo_movimento = str(row[3]) if len(row) > 3 and row[3] else "INCASSO"
                tipo_associazione = str(row[11]) if len(row) > 11 and row[11] else "PAGAMENTO"
                
                # Formatta il documento
                documento_formattato = self.format_documento(row[7], row[8], row[9])
                
                # Formatta la data
                data_str = str(row[1]) if row[1] else ""
                if data_str and '-' in data_str:
                    try:
                        data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                        data_str = data_obj.strftime("%d/%m/%Y")
                    except:
                        pass
                
                # Determina se è una nota di credito cliente o uno storno
                tipo_doc = str(row[7]).lower() if row[7] else ""
                segno = row[10] if len(row) > 10 else None
                
                # Verifica se è storno nota di credito
                is_storno_nc = (tipo_associazione == 'STORNO_NOTA_CREDITO')
                
                # Verifica se è nota di credito cliente
                is_nota_credito_cliente = False
                if segno is not None:
                    is_nota_credito_cliente = (segno == -1 and 'nc_cliente' in tipo_doc)
                else:
                    is_nota_credito_cliente = any(x in tipo_doc for x in ['nc_cliente', 'nota_credito_cliente'])
                
                # Calcola l'importo
                importo_raw = float(row[5]) if row[5] else 0.0
                if is_storno_nc or is_nota_credito_cliente:
                    # Per storni e note di credito, mostra sempre positivo (è già un credito)
                    importo_raw = abs(importo_raw)
                
                # Formatta l'importo per la visualizzazione
                importo_formattato = f"€ {importo_raw:,.2f}" if importo_raw != 0.0 else "€ 0.00"
                
                # Formatta le spese accessorie
                spese_raw = float(row[6]) if row[6] else 0.0
                spese_formattato = f"€ {spese_raw:,.2f}" if spese_raw != 0.0 else "€ 0.00"
                
                # Formatta il tipo di pagamento
                tipo_pagamento = str(row[2]) if row[2] else ""
                if tipo_pagamento == 'NOTA_CREDITO_APPLICATA':
                    # Se è un'associazione di tipo STORNO_NOTA_CREDITO, mostra come "Storno Nota Credito"
                    if tipo_associazione == 'STORNO_NOTA_CREDITO':
                        tipo_pagamento = 'Storno Nota Credito'
                    else:
                        tipo_pagamento = 'Nota Credito Applicata'
                
                self.original_data.append({
                    'pagamento_id': row[0],
                    'data': data_str,
                    'tipo_pag': tipo_pagamento,
                    'tipo_movimento': tipo_movimento,
                    'tipo_associazione': tipo_associazione,
                    'soggetto': str(row[4]) if len(row) > 4 and row[4] else "",
                    'importo': importo_formattato,
                    'importo_raw': importo_raw,  # Per filtri e ordinamento
                    'spese': spese_formattato,
                    'spese_raw': spese_raw,  # Per filtri e ordinamento
                    'documento': documento_formattato
                })

            # Applica filtri e ordinamento
            self.apply_filters()
        except Exception as e:
            messagebox.showerror("Errore DB", str(e))
            print(f"Errore caricamento pagamenti: {e}")
    
    def format_documento(self, tipo_documento, numero_documento, data_documento):
        """Formatta il documento nel formato richiesto"""
        if not tipo_documento:
            return ""
        
        # Converte il tipo documento nel formato abbreviato
        tipo_map = {
            'fattura_acquisto': 'FT. ACQUISTO',
            'fattura_vendita': 'FT. VENDITA',
            'fattura': 'FT.',
            'nota_credito': 'N.C.',
            'nota_debito': 'N.D.',
            'ricevuta': 'RIC.',
            'scontrino': 'SC.',
            'altro': 'DOC.'
        }
        
        tipo_formattato = tipo_map.get(tipo_documento.lower(), tipo_documento.upper())
        
        # Formatta la data da YYYY-MM-DD a DD/MM/YYYY
        data_formattata = ""
        if data_documento:
            try:
                data_obj = datetime.strptime(str(data_documento), '%Y-%m-%d')
                data_formattata = data_obj.strftime('%d/%m/%Y')
            except:
                data_formattata = str(data_documento)
        
        # Costruisce il formato finale
        numero_str = f"N. {numero_documento}" if numero_documento else ""
        data_str = f"DEL {data_formattata}" if data_formattata else ""
        
        parti = [tipo_formattato, numero_str, data_str]
        return " ".join([parte for parte in parti if parte])
    
    def apply_filters(self):
        """Applica i filtri in base al tab corrente"""
        if self.current_tab_filter == 'pagamenti':
            self.apply_filters_pagamenti()
        else:
            # Delega a RibaTab
            if self.riba_tab:
                self.riba_tab.apply_filters()
    
    def apply_filters_pagamenti(self):
        """Applica i filtri per pagamenti"""
        filtered_data = []
        for row in self.original_data:
            match = True
            for field, fval in self.active_filters_pagamenti.items():
                if not fval:
                    continue
                
                # Gestione filtro data con intervallo
                if field == 'data' and "|" in fval:
                    dal, al = fval.split("|")
                    try:
                        d = datetime.strptime(row["data"], "%d/%m/%Y")
                        if dal:
                            if d < datetime.strptime(dal, "%d/%m/%Y"): 
                                match = False
                                break
                        if al:
                            if d > datetime.strptime(al, "%d/%m/%Y"): 
                                match = False
                                break
                    except:
                        match = False
                        break
                # Per tipo_pag e soggetto usa match esatto (case-insensitive)
                elif field in ('tipo_pag', 'soggetto'):
                    if row[field].lower() != fval.lower():
                        match = False
                        break
                # Per importo e documento non applicare filtri (come richiesto)
                elif field in ('importo', 'documento'):
                    continue
                # Per altri campi usa ricerca parziale
                elif fval not in row[field].lower():
                    match = False
                    break
            
            if match:
                filtered_data.append(row)
        
        # Applica l'ordinamento
        if self.sort_column == 'data':
            # Ordina per data (formato dd/mm/yyyy)
            def sort_key_data(row):
                try:
                    parts = row['data'].split('/')
                    if len(parts) == 3:
                        return (int(parts[2]), int(parts[1]), int(parts[0]))  # yyyy, mm, dd
                    return (0, 0, 0)
                except:
                    return (0, 0, 0)
            filtered_data.sort(key=sort_key_data, reverse=(self.sort_direction == 'desc'))
        elif self.sort_column == 'soggetto':
            # Ordina per soggetto (alfabetico)
            filtered_data.sort(key=lambda row: row['soggetto'].lower(), reverse=(self.sort_direction == 'desc'))
        else:
            # Ordinamento predefinito per data (discendente)
            def sort_key_data(row):
                try:
                    parts = row['data'].split('/')
                    if len(parts) == 3:
                        return (int(parts[2]), int(parts[1]), int(parts[0]))
                    return (0, 0, 0)
                except:
                    return (0, 0, 0)
            filtered_data.sort(key=sort_key_data, reverse=True)
        
        # Salva i dati filtrati come attributo di istanza per la cancellazione
        self.filtered_data_pagamenti = filtered_data
        self.update_table_display_pagamenti(filtered_data)
    
    def update_table_display_pagamenti(self, data):
        """Aggiorna la visualizzazione della tabella pagamenti"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(data):
            # Formatta tipo_movimento per la visualizzazione
            tipo_mov = row.get('tipo_movimento', 'INCASSO')
            tipo_mov_display = 'INCASSO' if tipo_mov == 'INCASSO' else 'PAGAMENTO'
            
            values = [row['data'], row['tipo_pag'], tipo_mov_display, row['soggetto'], 
                     row['importo'], row['spese'], row['documento']]
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", tk.END, values=values, tags=(tag, f"id_{row['pagamento_id']}"))
        
        # Aggiorna il contatore
        self.counter_label.config(
            text=f"{len(data)} pagamenti visualizzati"
        )
    
    def show_filter_menu(self, field_name, column_title):
        """Mostra il menu per i filtri"""
        # Se siamo nel tab RiBa, delega a RibaTab
        if self.current_tab_filter == 'riba':
            if self.riba_tab:
                self.riba_tab.show_filter_menu(field_name, column_title)
            return
        
        win = tk.Toplevel(self)
        win.title(f"Filtro - {column_title}")
        win.geometry("320x250")
        win.configure(bg=Style.WHITE)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        frame = tk.Frame(win, bg=Style.WHITE, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=f"Filtro per {column_title}:", bg=Style.WHITE,
                 fg="#000", font=("Arial", 10, "bold")).pack(pady=(0, 10))

        active_filters = self.active_filters_pagamenti
        
        if field_name == "data":
            # Filtro data con intervallo per pagamenti
            from tkcalendar import DateEntry
            tk.Label(frame, text="Dal:", bg=Style.WHITE).pack()
            dal_entry = DateEntry(frame, date_pattern="dd/mm/yyyy", width=15)
            dal_entry.pack(pady=(0, 5))
            tk.Label(frame, text="Al:", bg=Style.WHITE).pack()
            al_entry = DateEntry(frame, date_pattern="dd/mm/yyyy", width=15)
            al_entry.pack(pady=(0, 10))
            
            # Recupera valori esistenti
            filtro_attuale = active_filters.get(field_name, "")
            if "|" in filtro_attuale:
                parti = filtro_attuale.split("|")
                if parti[0]:
                    try:
                        dal_entry.set_date(datetime.strptime(parti[0], "%d/%m/%Y"))
                    except:
                        pass
                if len(parti) > 1 and parti[1]:
                    try:
                        al_entry.set_date(datetime.strptime(parti[1], "%d/%m/%Y"))
                    except:
                        pass

            def apply_date():
                dal, al = dal_entry.get(), al_entry.get()
                active_filters["data"] = f"{dal}|{al}"
                self.apply_filters()
                win.destroy()

            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_date, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        elif field_name == "tipo_pag":
            # Menu a tendina per tipo pagamento
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT modalita_pagamento FROM pagamenti WHERE modalita_pagamento IS NOT NULL AND modalita_pagamento != '' ORDER BY modalita_pagamento")
                tipi_pagamento = [row[0] for row in cursor.fetchall()]
                conn.close()
            except Exception as e:
                print(f"Errore recupero tipi pagamento: {e}")
                tipi_pagamento = []
            
            # Aggiungi valori dai dati originali se non sono nel DB
            valori_esistenti = {row['tipo_pag'] for row in self.original_data if row['tipo_pag']}
            tipi_pagamento = sorted(set(tipi_pagamento) | valori_esistenti)
            
            combo = ttk.Combobox(frame, values=[""] + tipi_pagamento, state="readonly", width=25)
            combo.pack(pady=(0, 15))
            
            # Imposta il valore corrente se presente
            filtro_attuale = active_filters.get(field_name, "")
            if filtro_attuale:
                # Cerca il valore corrispondente (case-insensitive)
                for val in tipi_pagamento:
                    if val.lower() == filtro_attuale.lower():
                        combo.set(val)
                        break
            
            def apply_combo():
                valore_selezionato = combo.get()
                active_filters[field_name] = valore_selezionato.lower() if valore_selezionato else ""
                self.apply_filters()
                win.destroy()
            
            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_combo, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        elif field_name == "soggetto":
            # Autocompletamento con ricerca per soggetto (come in documenti_page.py)
            win.geometry("400x350")
            vals = sorted({r[field_name] for r in self.original_data if r[field_name]})
            
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
            
            # Imposta il valore corrente se presente
            filtro_attuale = active_filters.get(field_name, "")
            if filtro_attuale:
                # Cerca il valore corrispondente (case-insensitive)
                for val in vals:
                    if val.lower() == filtro_attuale.lower():
                        search_entry.insert(0, val)
                        filter_listbox()
                        # Seleziona il valore nella listbox
                        try:
                            idx = list(all_vals).index(val)
                            listbox.selection_set(idx)
                            listbox.see(idx)
                        except:
                            pass
                        break
            
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
                
                active_filters[field_name] = val.lower() if val else ""
                self.apply_filters()
                win.destroy()
            
            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_combo, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        win.bind('<Escape>', lambda e: win.destroy())
    
    def show_sort_menu(self):
        """Mostra il menu per l'ordinamento"""
        if self.current_tab_filter != 'pagamenti':
            # TODO: Implementare ordinamento per RiBa
            return
        
        menu = tk.Menu(self, tearoff=0)
        
        # Menu per pagamenti
        menu.add_command(label="📅 Data (più recente)", 
                        command=lambda: self.change_sort("data", "desc"))
        menu.add_command(label="📅 Data (più vecchio)", 
                        command=lambda: self.change_sort("data", "asc"))
        menu.add_separator()
        menu.add_command(label="👤 Soggetto (A-Z)", 
                        command=lambda: self.change_sort("soggetto", "asc"))
        menu.add_command(label="👤 Soggetto (Z-A)", 
                        command=lambda: self.change_sort("soggetto", "desc"))
        
        # Posiziona il menu sotto il pulsante
        x = self.sort_btn.winfo_rootx()
        y = self.sort_btn.winfo_rooty() + self.sort_btn.winfo_height()
        menu.post(x, y)
    
    def change_sort(self, column, direction):
        """Cambia l'ordinamento"""
        self.sort_column = column
        self.sort_direction = direction
        
        # Applica l'ordinamento ai dati filtrati
        if self.current_tab_filter == 'pagamenti':
            self.apply_filters_pagamenti()
        # RiBa non ha ordinamento per ora (gestito da RibaTab se necessario)
    
    # Metodi per pagamenti
    def nuovo_pagamento(self):
        """Apre la finestra per nuovo pagamento"""
        NuovoPagamentoWindow(self, self.db_path, on_save_callback=self.load_data)
    
    def modifica_pagamento(self):
        """Modifica pagamento"""
        messagebox.showinfo("Info", "Modifica pagamento - da implementare")
    
    def cancella_pagamento(self):
        """Cancella pagamento selezionato"""
        # Verifica che siamo nel tab pagamenti
        if self.current_tab_filter != 'pagamenti':
            return
        
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona un pagamento da cancellare dalla tabella")
            return
        
        # Conferma cancellazione
        if len(selected_items) == 1:
            msg = "Sei sicuro di voler cancellare il pagamento selezionato?\n\nQuesta operazione è irreversibile."
        else:
            msg = f"Sei sicuro di voler cancellare i {len(selected_items)} pagamenti selezionati?\n\nQuesta operazione è irreversibile."
        
        if not messagebox.askyesno("Conferma cancellazione", msg):
            return
            
        try:
            # Recupera gli ID dei pagamenti selezionati usando i tag degli item
            pagamenti_ids = []
            for item in selected_items:
                # Recupera i tag dell'item
                tags = self.tree.item(item, 'tags')
                if tags:
                    # Cerca il tag che inizia con "id_"
                    for tag in tags:
                        if tag.startswith('id_'):
                            pagamento_id = int(tag.split('_')[1])
                            pagamenti_ids.append(pagamento_id)
                            break
            
            if not pagamenti_ids:
                messagebox.showerror("Errore", "Impossibile recuperare gli ID dei pagamenti selezionati")
                return
            
            # Esegui cancellazione in transazione
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Cancella prima le righe in associazioni_pagamenti (tabella dipendente)
                for pagamento_id in pagamenti_ids:
                    cursor.execute("DELETE FROM associazioni_pagamenti WHERE id_pagamento = ?", (pagamento_id,))
                
                # Poi cancella i pagamenti dalla tabella principale
                for pagamento_id in pagamenti_ids:
                    cursor.execute("DELETE FROM pagamenti WHERE id = ?", (pagamento_id,))
                
                cursor.execute("COMMIT")
                conn.close()
                
                # Messaggio di successo
                if len(pagamenti_ids) == 1:
                    messagebox.showinfo("Successo", "Pagamento cancellato con successo!")
                else:
                    messagebox.showinfo("Successo", f"{len(pagamenti_ids)} pagamenti cancellati con successo!")
                
                # Ricarica i dati
                self.load_data()
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                conn.close()
                raise e
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la cancellazione: {str(e)}")
    
    # Metodi per RiBa - RIMOSSI: ora gestiti da RibaTab
    # Tutti i metodi RiBa sono stati spostati in pagamenti_page_riba.py


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pagamenti e RiBa Unificati")
    root.geometry("1200x700")
    app = PagamentiUnificatiApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()