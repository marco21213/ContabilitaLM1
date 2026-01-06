"""
Componente Distinte RIBA Tab - Gestione distinte RIBA come componente riutilizzabile
Può essere utilizzato come tab all'interno di PagamentiUnificatiApp
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# per PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Importa gli stili
import sys
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
style_path = os.path.join(project_root, 'assets', 'style')
if style_path not in sys.path:
    sys.path.insert(0, style_path)
from styles import Style


class DistinteRibaTab(tk.Frame):
    """Componente tab per gestione Distinte RIBA"""
    
    def __init__(self, parent, db_path, riba_tab=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.riba_tab = riba_tab  # Riferimento alla tab RIBA per aggiornare i dati

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.configure(bg=Style.BACKGROUND_COLOR)
        self.create_ui()
        self.load_data()

    def create_ui(self):
        """Crea l'interfaccia utente della tab"""
        # Barra pulsanti
        button_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(5, 0))
        
        from PIL import Image, ImageTk
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
                         fg="#1f396a", font=("Arial", 10, "bold")).pack(pady=(2, 0))
            except Exception as e:
                print(f"Errore caricamento icona {icon_name}: {e}")
                btn = tk.Button(frame, text=text, command=command, bg=fallback_color,
                                fg="white", font=("Arial", 11, "bold"), cursor="hand2", width=12, height=2)
                btn.pack()

        buttons = [
            ("nuovo", "Nuova Distinta", self.nuova_distinta, "#4CAF50"),
            ("modifica", "Modifica", self.modifica_distinta, "#FF9800"),
            ("importa", "Stampa", self.stampa_distinta, "#2196F3"),
            ("cancella", "Cancella", self.cancella_distinta, "#f44336"),
        ]
        
        for icon, text, cmd, color in buttons:
            frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            frame.pack(side="left", padx=(0, 25))
            add_button(frame, icon, text, cmd, color)

        # Tabella distinte
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        columns = ('ID', 'Numero', 'Data Distinta', 'Data Creazione', 'Banca', 'Num Ri.Ba.', 'Totale')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='center')
        
        # Aggiusta larghezza colonne
        self.tree.column('ID', width=50)
        self.tree.column('Numero', width=100)
        self.tree.column('Data Distinta', width=120)
        self.tree.column('Data Creazione', width=120)
        self.tree.column('Banca', width=200)
        self.tree.column('Num Ri.Ba.', width=80)
        self.tree.column('Totale', width=120)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def load_data(self):
        """Carica tutte le distinte dal database"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica quali colonne esistono
            cur.execute("PRAGMA table_info(distinte_riba)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            
            has_numero_distinta = 'numero_distinta' in colonne_nomi
            has_data_distinta = 'data_distinta' in colonne_nomi
            has_banca_id = 'banca_id' in colonne_nomi
            
            # Costruisci query dinamica basata sulle colonne disponibili
            select_parts = ['di.id']
            if has_numero_distinta:
                select_parts.append('COALESCE(di.numero_distinta, di.id) AS numero')
            else:
                select_parts.append('di.id AS numero')
            
            if has_data_distinta:
                select_parts.append('di.data_distinta')
            else:
                select_parts.append('NULL AS data_distinta')
            
            select_parts.append('di.data_creazione')
            
            if has_banca_id:
                select_parts.append('b.denominazione')
            else:
                select_parts.append('NULL AS banca')
            
            select_parts.extend([
                'COUNT(r.id) AS num_riba',
                'COALESCE(SUM(sc.importo_scadenza), 0) AS totale'
            ])
            
            join_clause = ''
            if has_banca_id:
                join_clause = 'LEFT JOIN banche b ON di.banca_id = b.id'
            
            query = f"""
                SELECT {', '.join(select_parts)}
                FROM distinte_riba di
                LEFT JOIN riba r ON r.distinta_id = di.id
                LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                {join_clause}
                GROUP BY di.id
                ORDER BY di.id DESC
            """
            
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            
            def formatta_data_distinta(data_str):
                """Converte la data da formato database (YYYY-MM-DD o altro) a dd/mm/yyyy"""
                if not data_str:
                    return ''
                try:
                    # Prova formato YYYY-MM-DD
                    if '-' in data_str and len(data_str.split('-')) == 3:
                        parts = data_str.split('-')
                        if len(parts[0]) == 4:  # Anno a 4 cifre
                            return f"{parts[2]}/{parts[1]}/{parts[0]}"
                    # Se è già in formato dd/mm/yyyy, restituisci così com'è
                    elif '/' in data_str:
                        return data_str
                except:
                    pass
                return data_str
            
            for row in rows:
                distinta_id = row[0]
                numero = str(row[1]) if row[1] else str(distinta_id)
                data_distinta_raw = row[2] or ''
                data_creazione_raw = row[3] or ''
                banca = row[4] or ''
                num_riba = row[5] or 0
                totale = float(row[6]) if row[6] else 0.0
                
                # Formatta data distinta
                data_distinta = formatta_data_distinta(data_distinta_raw)
                # Formatta data creazione
                data_creazione = formatta_data_distinta(data_creazione_raw)
                
                self.tree.insert('', tk.END, values=(
                    distinta_id, numero, data_distinta, data_creazione, 
                    banca, num_riba, f"€ {totale:,.2f}"
                ), tags=(f"dist_{distinta_id}",))
                
        except Exception as e:
            messagebox.showerror('Errore DB', f'Errore nel caricamento distinte: {str(e)}')

    def nuova_distinta(self):
        """Crea nuova distinta RiBa"""
        # finestra di selezione Ri.Ba. Da emettere
        win = tk.Toplevel(self)
        win.title('Nuova Distinta Ri.Ba.')
        win.geometry('800x600')
        win.transient(self)

        frame = tk.Frame(win, bg=Style.WHITE, padx=10, pady=10)
        frame.pack(fill='both', expand=True)

        # Frame per i campi distinta
        info_frame = tk.Frame(frame, bg=Style.WHITE)
        info_frame.pack(fill='x', pady=(0,10))
        
        # Prima riga: Numero e Data
        tk.Label(info_frame, text='Numero Distinta:', bg=Style.WHITE, font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=(0,10), sticky='w')
        num_distinta_entry = tk.Entry(info_frame, font=('Arial', 10), width=20)
        num_distinta_entry.grid(row=0, column=1, padx=(0,30), sticky='w')
        
        tk.Label(info_frame, text='Data Distinta:', bg=Style.WHITE, font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=(0,10), sticky='w')
        data_distinta_entry = tk.Entry(info_frame, font=('Arial', 10), width=15)
        data_distinta_entry.insert(0, datetime.now().strftime('%d/%m/%Y'))
        data_distinta_entry.grid(row=0, column=3, sticky='w')
        
        # Seconda riga: Banca
        tk.Label(info_frame, text='Banca:', bg=Style.WHITE, font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=(0,10), pady=(10,0), sticky='w')
        banca_combo = ttk.Combobox(info_frame, font=('Arial', 10), width=30, state='readonly')
        banca_combo.grid(row=1, column=1, columnspan=2, pady=(10,0), sticky='w')
        
        # Carica le banche dal database
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, denominazione FROM banche ORDER BY denominazione")
            banche_rows = cur.fetchall()
            conn.close()
            # Crea dizionario per mappare nome banca -> id
            banche_dict = {}
            banche_nomi = []
            for banca_row in banche_rows:
                banche_dict[banca_row[1]] = banca_row[0]
                banche_nomi.append(banca_row[1])
            banca_combo['values'] = banche_nomi
        except Exception as e:
            messagebox.showerror('Errore DB', f'Errore nel caricamento banche: {str(e)}')
            banche_dict = {}
            banche_nomi = []
            banca_combo['values'] = []

        # Frame principale con PanedWindow per dividere RiBa e Note di Credito
        main_paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, sashwidth=5)
        main_paned.pack(fill='both', expand=True, pady=(0, 10))
        
        # Frame sinistro: RiBa
        left_frame = tk.Frame(main_paned, bg=Style.WHITE)
        main_paned.add(left_frame, width=500)
        
        lbl = tk.Label(left_frame, text='Seleziona le Ri.Ba. da includere nella distinta:', bg=Style.WHITE, font=('Arial', 11, 'bold'))
        lbl.pack(anchor='w', pady=(0,10))

        # Label per il totale RiBa (in alto, colore nero)
        totale_riba_label = tk.Label(left_frame, text='Totale RiBa selezionate: € 0,00', bg=Style.WHITE, 
                               font=('Arial', 11, 'bold'), fg='#000000')
        totale_riba_label.pack(anchor='w', pady=(0,10))
        
        # Frame destro: Note di Credito
        right_frame = tk.Frame(main_paned, bg=Style.WHITE)
        main_paned.add(right_frame, width=400)
        
        tk.Label(right_frame, text='Note di Credito Disponibili:', bg=Style.WHITE, font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0,10))
        
        # Label per il totale NC selezionate
        totale_nc_label = tk.Label(right_frame, text='Totale NC selezionate: € 0,00', bg=Style.WHITE, 
                               font=('Arial', 10, 'bold'), fg='blue')
        totale_nc_label.pack(anchor='w', pady=(0,5))
        
        # Label per l'importo netto distinta
        importo_netto_label = tk.Label(right_frame, text='Importo netto distinta: € 0,00', bg=Style.WHITE, 
                               font=('Arial', 11, 'bold'), fg='green')
        importo_netto_label.pack(anchor='w', pady=(0,10))

        # Variabile per tracciare l'ordinamento
        sort_column = None
        sort_reverse = False

        def ordina_tabella(col):
            nonlocal sort_column, sort_reverse
            if sort_column == col:
                sort_reverse = not sort_reverse
            else:
                sort_column = col
                sort_reverse = False
            
            # Ordina i dati preservando le selezioni
            items = list(listbox.get_children())
            items_data = []
            for item in items:
                values = listbox.item(item, 'values')
                tags = listbox.item(item, 'tags')
                # Memorizza se l'item era selezionato
                era_selezionato = item in selezioni and selezioni[item]
                items_data.append((item, values, tags, era_selezionato))
            
            # Determina l'indice della colonna
            colonne = ['seleziona', 'cliente', 'data', 'documento', 'scadenza', 'importo']
            try:
                col_idx = colonne.index(col)
            except ValueError:
                return  # Colonna non valida
            
            # Funzione di ordinamento
            def chiave_ordinamento(item_data):
                item, values, tags, era_selezionato = item_data
                val = values[col_idx] if col_idx < len(values) else ''
                
                # Ordinamento speciale per data (dd/mm/yyyy)
                if col == 'data' and val:
                    try:
                        parts = val.split('/')
                        if len(parts) == 3:
                            return (int(parts[2]), int(parts[1]), int(parts[0]))
                    except:
                        pass
                
                # Ordinamento speciale per numero documento (numerico se possibile)
                if col == 'documento' and val:
                    try:
                        return int(val)
                    except:
                        pass
                
                # Ordinamento standard
                return val.lower() if isinstance(val, str) else val
            
            items_data.sort(key=chiave_ordinamento, reverse=sort_reverse)
            
            # Aggiorna la visualizzazione preservando selezioni e dati
            # Svuota temporaneamente le selezioni e importi
            selezioni.clear()
            importi_dict.clear()
            
            # Elimina tutti gli item dalla vista
            for item in items:
                listbox.delete(item)
            
            for item_id_old, values, tags, era_selezionato in items_data:
                # Recupera i dati originali dai tags
                riba_id = None
                importo_val = None
                for t in tags:
                    if t.startswith('id_'):
                        riba_id = int(t[3:])
                    elif t.startswith('importo_'):
                        # Estrai il valore dopo 'importo_' usando replace invece di slicing
                        try:
                            importo_val = float(t.replace('importo_', '', 1))
                        except (ValueError, AttributeError):
                            importo_val = None
                
                # Crea nuovo item
                item_id_new = listbox.insert('', tk.END, values=values, tags=tags)
                
                # Ripristina selezione se era selezionato
                if era_selezionato:
                    selezioni[item_id_new] = True
                    # Aggiorna anche il checkbox visuale
                    values_list = list(values)
                    values_list[0] = '  ✓'
                    listbox.item(item_id_new, values=values_list)
                    # Aggiungi tag selezionata
                    tags_list = list(tags)
                    if 'selezionata' not in tags_list:
                        tags_list.append('selezionata')
                    listbox.item(item_id_new, tags=tags_list)
                
                # Ripristina importo nel dizionario
                if importo_val is not None:
                    importi_dict[item_id_new] = importo_val
            
            # Aggiorna totale dopo l'ordinamento
            aggiorna_totale()

        # Treeview con colonna checkbox (RiBa)
        listbox = ttk.Treeview(left_frame, columns=('seleziona','cliente','data','documento','scadenza','importo'), show='headings')
        # Usa caratteri checkbox più grandi
        listbox.heading('seleziona', text='  ☐')
        listbox.column('seleziona', width=70, anchor='center')
        for col, w in [('cliente',200),('data',100),('documento',120),('scadenza',110),('importo',90)]:
            listbox.heading(col, text=col.capitalize(), command=lambda c=col: ordina_tabella(c))
            listbox.column(col, width=w)
        listbox.pack(fill='both', expand=True)
        
        # Configura tag per evidenziare le righe selezionate (colore più scuro)
        listbox.tag_configure('selezionata', background='#BBDEFB', foreground='#000000')

        # Dizionario per tracciare le selezioni (item_id -> bool)
        selezioni = {}
        # Dizionario per memorizzare gli importi (item_id -> float)
        importi_dict = {}

        def toggle_checkbox(event):
            item = listbox.identify_row(event.y)
            col = listbox.identify_column(event.x)
            if not item:
                return
            # Permetti toggle cliccando sia sulla colonna checkbox che sulla riga
            # Se clicchi sulla colonna checkbox (#1) o su qualsiasi altra parte della riga
            if col == '#1' or (col and col != '#0'):  # colonna checkbox o altre colonne dati
                # Toggle selezione
                if item in selezioni:
                    selezioni[item] = not selezioni[item]
                else:
                    selezioni[item] = True
                
                # Aggiorna visualizzazione checkbox (usa caratteri più grandi)
                values = list(listbox.item(item, 'values'))
                if selezioni[item]:
                    values[0] = '  ✓'  # Check più grande
                    # Aggiungi tag per evidenziare la riga
                    tags = list(listbox.item(item, 'tags'))
                    if 'selezionata' not in tags:
                        tags.append('selezionata')
                    listbox.item(item, tags=tags)
                else:
                    values[0] = '  ☐'  # Box più grande
                    # Rimuovi tag di evidenziazione
                    tags = list(listbox.item(item, 'tags'))
                    if 'selezionata' in tags:
                        tags.remove('selezionata')
                    listbox.item(item, tags=tags)
                listbox.item(item, values=values)
                
                # Aggiorna totale e carica note di credito
                aggiorna_totale()
                carica_note_credito()

        # Tabella note di credito
        nc_listbox = ttk.Treeview(right_frame, columns=('seleziona','documento','data','residuo'), show='headings')
        nc_listbox.heading('seleziona', text='  ☐')
        nc_listbox.column('seleziona', width=50, anchor='center')
        nc_listbox.heading('documento', text='DOCUMENTO')
        nc_listbox.column('documento', width=150)
        nc_listbox.heading('data', text='DATA')
        nc_listbox.column('data', width=80, anchor='center')
        nc_listbox.heading('residuo', text='RESIDUO')
        nc_listbox.column('residuo', width=100, anchor='e')
        nc_listbox.pack(fill='both', expand=True, pady=(0, 10))
        
        # Dizionario per tracciare le selezioni NC
        selezioni_nc = {}
        importi_nc_dict = {}
        
        def toggle_nc_checkbox(event):
            item = nc_listbox.identify_row(event.y)
            col = nc_listbox.identify_column(event.x)
            if not item:
                return
            if col == '#1' or (col and col != '#0'):
                if item in selezioni_nc:
                    selezioni_nc[item] = not selezioni_nc[item]
                else:
                    selezioni_nc[item] = True
                
                values = list(nc_listbox.item(item, 'values'))
                if selezioni_nc[item]:
                    values[0] = '  ✓'
                else:
                    values[0] = '  ☐'
                nc_listbox.item(item, values=values)
                aggiorna_totale()
        
        nc_listbox.bind('<ButtonRelease-1>', toggle_nc_checkbox)
        
        def aggiorna_totale():
            try:
                # Verifica che i widget esistano ancora
                if not win.winfo_exists():
                    return
                # Totale RiBa
                totale_riba = 0.0
                for item in listbox.get_children():
                    if item in selezioni and selezioni[item]:
                        if item in importi_dict:
                            totale_riba += importi_dict[item]
                totale_riba_label.config(text=f'Totale RiBa selezionate: € {totale_riba:,.2f}')
                
                # Totale NC
                totale_nc = 0.0
                for item in nc_listbox.get_children():
                    if item in selezioni_nc and selezioni_nc[item]:
                        if item in importi_nc_dict:
                            totale_nc += importi_nc_dict[item]
                totale_nc_label.config(text=f'Totale NC selezionate: € {totale_nc:,.2f}')
                
                # Importo netto
                importo_netto = max(0, totale_riba - totale_nc)
                importo_netto_label.config(text=f'Importo netto distinta: € {importo_netto:,.2f}')
            except tk.TclError:
                # Widget distrutto, ignora
                pass
            except Exception as e:
                print(f"Errore in aggiorna_totale: {e}")

        listbox.bind('<ButtonRelease-1>', toggle_checkbox)
        
        def carica_note_credito():
            """Carica le note di credito disponibili per i clienti delle RiBa selezionate"""
            try:
                # Verifica che i widget esistano ancora
                if not win.winfo_exists():
                    return
                # Svuota la tabella NC
                for item in nc_listbox.get_children():
                    nc_listbox.delete(item)
                selezioni_nc.clear()
                importi_nc_dict.clear()
                
                # Raccogli i clienti delle RiBa selezionate
                clienti_ids = set()
                for item in listbox.get_children():
                    if item in selezioni and selezioni[item]:
                        tags = listbox.item(item, 'tags')
                        for t in tags:
                            if t.startswith('cliente_id_'):
                                cliente_id = int(t.replace('cliente_id_', '', 1))
                                clienti_ids.add(cliente_id)
                                break
                
                if not clienti_ids:
                    return
            except tk.TclError:
                # Widget distrutto, ignora
                return
            except Exception as e:
                print(f"Errore in carica_note_credito (inizializzazione): {e}")
                return
            
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                
                # Verifica se esiste la colonna segno
                cur.execute("PRAGMA table_info(documenti)")
                colonne_info = cur.fetchall()
                colonne_nomi = [col[1] for col in colonne_info]
                has_segno = 'segno' in colonne_nomi
                
                # Query per note di credito disponibili
                if has_segno:
                    query_nc = """
                        SELECT
                            sc.id AS scadenza_id,
                            d.id AS documento_id,
                            d.tipo_documento || ' ' || d.numero_documento AS documento,
                            d.data_documento,
                            ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo,
                            s.id AS soggetto_id
                        FROM scadenze sc
                        JOIN documenti d ON sc.id_documento = d.id
                        LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                        LEFT JOIN soggetti s ON d.soggetto_id = s.id
                        WHERE d.soggetto_id IN ({})
                          AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                               OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                          AND d.segno = -1
                        GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.importo_scadenza, d.id, s.id
                        HAVING residuo > 0.01
                        ORDER BY d.data_documento ASC
                    """.format(','.join(['?'] * len(clienti_ids)))
                else:
                    query_nc = """
                        SELECT
                            sc.id AS scadenza_id,
                            d.id AS documento_id,
                            d.tipo_documento || ' ' || d.numero_documento AS documento,
                            d.data_documento,
                            ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo,
                            s.id AS soggetto_id
                        FROM scadenze sc
                        JOIN documenti d ON sc.id_documento = d.id
                        LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                        LEFT JOIN soggetti s ON d.soggetto_id = s.id
                        WHERE d.soggetto_id IN ({})
                          AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                               OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                        GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.importo_scadenza, d.id, s.id
                        HAVING residuo > 0.01
                        ORDER BY d.data_documento ASC
                    """.format(','.join(['?'] * len(clienti_ids)))
                
                cur.execute(query_nc, list(clienti_ids))
                nc_rows = cur.fetchall()
                conn.close()
                
                def formatta_data(data_str):
                    """Converte la data da formato database (YYYY-MM-DD o altro) a dd/mm/yyyy"""
                    if not data_str:
                        return ''
                    try:
                        # Prova formato YYYY-MM-DD
                        if '-' in data_str and len(data_str.split('-')) == 3:
                            parts = data_str.split('-')
                            if len(parts[0]) == 4:  # Anno a 4 cifre
                                return f"{parts[2]}/{parts[1]}/{parts[0]}"
                        # Se è già in formato dd/mm/yyyy, restituisci così com'è
                        elif '/' in data_str:
                            return data_str
                    except:
                        pass
                    return data_str  # Se non riesce a convertire, restituisce l'originale
                
                for nc_row in nc_rows:
                    scadenza_id = nc_row[0]
                    documento_id = nc_row[1]
                    documento = nc_row[2]
                    data_doc = formatta_data(nc_row[3]) if nc_row[3] else ''
                    residuo = float(nc_row[4]) if nc_row[4] else 0.0
                    
                    item_id = nc_listbox.insert('', tk.END, values=(
                        '  ☐', documento, data_doc, f"{residuo:,.2f}"
                    ), tags=(f'scadenza_id_{scadenza_id}', f'documento_id_{documento_id}'))
                    
                    importi_nc_dict[item_id] = residuo
            except tk.TclError:
                # Widget distrutto, ignora
                pass
            except Exception as e:
                # Verifica che la finestra esista ancora prima di mostrare l'errore
                try:
                    if win.winfo_exists():
                        messagebox.showerror('Errore DB', f'Errore nel caricamento note di credito: {str(e)}')
                except:
                    pass

        # carica le Ri.Ba. da emettere
        try:
            conn = sqlite3.connect(self.db_path); cur = conn.cursor()
            # Verifica se la colonna distinta_id esiste nella tabella riba
            try:
                cur.execute("PRAGMA table_info(riba)")
                colonne_riba = [col[1] for col in cur.fetchall()]
                if 'distinta_id' not in colonne_riba:
                    cur.execute("ALTER TABLE riba ADD COLUMN distinta_id INTEGER")
                    conn.commit()
            except Exception as e:
                print(f"Errore verifica/aggiunta colonna distinta_id: {e}")
            
            # Query che parte da scadenze per trovare tutte le scadenze con tipo_pagamento = 'RIBA'
            # e che non hanno ancora una riga in riba o hanno una riga con stato 'Da emettere' non assegnata a distinta
            cur.execute("""
                SELECT 
                    COALESCE(r.id, sc.id) AS riba_id,
                    s.ragione_sociale, 
                    d.data_documento, 
                    d.numero_documento, 
                    sc.data_scadenza, 
                    sc.importo_scadenza AS importo, 
                    s.id AS soggetto_id, 
                    d.id AS documento_id,
                    sc.id AS scadenza_id
                FROM scadenze sc
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                LEFT JOIN riba r ON r.scadenza_id = sc.id
                WHERE sc.tipo_pagamento = 'RIBA'
                  AND (
                      r.id IS NULL 
                      OR (r.stato = 'Da emettere' AND (r.distinta_id IS NULL OR r.distinta_id = 0))
                  )
                ORDER BY sc.data_scadenza
            """)
            rows = cur.fetchall(); conn.close()
        except Exception as e:
            messagebox.showerror('Errore DB', str(e)); win.destroy(); return

        def formatta_data(data_str):
            """Converte la data da formato database (YYYY-MM-DD o altro) a dd/mm/yyyy"""
            if not data_str:
                return ''
            try:
                # Prova formato YYYY-MM-DD
                if '-' in data_str and len(data_str.split('-')) == 3:
                    parts = data_str.split('-')
                    if len(parts[0]) == 4:  # Anno a 4 cifre
                        return f"{parts[2]}/{parts[1]}/{parts[0]}"
                # Se è già in formato dd/mm/yyyy, restituisci così com'è
                elif '/' in data_str:
                    return data_str
            except:
                pass
            return data_str  # Se non riesce a convertire, restituisce l'originale

        try:
            if not win.winfo_exists():
                return
            for r in rows:
                riba_id = r[0]  # Può essere NULL se non esiste ancora una riga in riba
                scadenza_id = r[8] if len(r) > 8 else None  # ID della scadenza
                importo = float(r[5]) if r[5] else 0.0
                soggetto_id = r[6] if len(r) > 6 else None
                documento_id = r[7] if len(r) > 7 else None
                # Formatta la data in formato dd/mm/yyyy (r[2] è data_documento)
                data_doc = formatta_data(r[2] if r[2] else '')
                # Usa scadenza_id come identificatore se riba_id è NULL
                identificatore = riba_id if riba_id else scadenza_id
                tags_list = [f"id_{identificatore}", f"scadenza_id_{scadenza_id}", f"importo_{importo}"]
                if riba_id:
                    tags_list.append("riba_esistente")
                else:
                    tags_list.append("riba_da_creare")
                if soggetto_id:
                    tags_list.append(f"cliente_id_{soggetto_id}")
                if documento_id:
                    tags_list.append(f"documento_id_{documento_id}")
                item_id = listbox.insert('', tk.END, 
                                        values=('  ☐', r[1] or '', data_doc, r[3] or '', r[4] or '', f"€ {importo:,.2f}"), 
                                        tags=tuple(tags_list))
                selezioni[item_id] = False
                importi_dict[item_id] = importo  # Memorizza l'importo nel dizionario
        except tk.TclError:
            # Widget distrutto, ignora
            pass
        except Exception as e:
            print(f"Errore nel caricamento RiBa: {e}")
            try:
                if win.winfo_exists():
                    messagebox.showerror('Errore DB', f'Errore nel caricamento RiBa: {str(e)}')
            except:
                pass

        def crea_distinta():
            # Raccogli gli ID selezionati (riba_id o scadenza_id)
            ids_riba = []  # ID delle RiBa esistenti
            scadenze_da_creare = []  # (scadenza_id, importo, data_scadenza) per RiBa da creare
            for item in listbox.get_children():
                if item in selezioni and selezioni[item]:
                    tags = listbox.item(item, 'tags')
                    riba_id = None
                    scadenza_id = None
                    importo = importi_dict.get(item, 0.0)
                    for t in tags:
                        if t.startswith('id_'):
                            identificatore = int(t[3:])
                            if 'riba_esistente' in tags:
                                riba_id = identificatore
                            else:
                                scadenza_id = identificatore
                        elif t.startswith('scadenza_id_'):
                            scadenza_id = int(t[12:])
                    
                    if riba_id:
                        ids_riba.append(riba_id)
                    elif scadenza_id:
                        # Recupera data_scadenza dalla riga
                        values = listbox.item(item, 'values')
                        data_scadenza = values[4] if len(values) > 4 else None
                        scadenze_da_creare.append((scadenza_id, importo, data_scadenza))
            
            if not ids_riba and not scadenze_da_creare:
                messagebox.showwarning('Attenzione', 'Seleziona almeno una Ri.Ba.'); return
            
            # Ottieni il numero distinta
            num_distinta = num_distinta_entry.get().strip()
            if not num_distinta:
                messagebox.showwarning('Attenzione', 'Inserisci un numero distinta'); return
            
            # Ottieni la data distinta
            data_distinta = data_distinta_entry.get().strip()
            if not data_distinta:
                messagebox.showwarning('Attenzione', 'Inserisci una data distinta'); return
            
            # Ottieni la banca
            banca_selezionata = banca_combo.get().strip()
            if not banca_selezionata:
                messagebox.showwarning('Attenzione', 'Seleziona una banca'); return
            
            banca_id = banche_dict.get(banca_selezionata)
            if not banca_id:
                messagebox.showerror('Errore', 'Banca non valida'); return
            
            try:
                conn = sqlite3.connect(self.db_path); cur = conn.cursor()
                data_cre = datetime.now().strftime('%Y-%m-%d')
                
                # Verifica e crea le colonne se non esistono
                try:
                    cur.execute("SELECT numero_distinta FROM distinte_riba LIMIT 1")
                    colonna_num_esiste = True
                except:
                    colonna_num_esiste = False
                    try:
                        cur.execute("ALTER TABLE distinte_riba ADD COLUMN numero_distinta TEXT")
                        conn.commit()
                        colonna_num_esiste = True
                    except:
                        pass
                
                # Verifica colonna data_distinta
                try:
                    cur.execute("SELECT data_distinta FROM distinte_riba LIMIT 1")
                    colonna_data_esiste = True
                except:
                    colonna_data_esiste = False
                    try:
                        cur.execute("ALTER TABLE distinte_riba ADD COLUMN data_distinta TEXT")
                        conn.commit()
                        colonna_data_esiste = True
                    except:
                        pass
                
                # Verifica colonna banca_id
                try:
                    cur.execute("SELECT banca_id FROM distinte_riba LIMIT 1")
                    colonna_banca_esiste = True
                except:
                    colonna_banca_esiste = False
                    try:
                        cur.execute("ALTER TABLE distinte_riba ADD COLUMN banca_id INTEGER")
                        conn.commit()
                        colonna_banca_esiste = True
                    except:
                        pass
                
                # Verifica se il numero distinta esiste già
                if colonna_num_esiste:
                    try:
                        cur.execute("SELECT id FROM distinte_riba WHERE numero_distinta = ?", (num_distinta,))
                        if cur.fetchone():
                            messagebox.showerror('Errore', f'Il numero distinta {num_distinta} è già utilizzato')
                            conn.close()
                            return
                    except:
                        pass  # Se la query fallisce, continua comunque
                
                # Inserisci la distinta (l'ID sarà auto-incrementale)
                colonne = ['data_creazione']
                valori = [data_cre]
                
                if colonna_num_esiste:
                    colonne.append('numero_distinta')
                    valori.append(num_distinta)
                if colonna_data_esiste:
                    colonne.append('data_distinta')
                    valori.append(data_distinta)
                if colonna_banca_esiste:
                    colonne.append('banca_id')
                    valori.append(banca_id)
                
                # Costruisci la query in modo sicuro
                colonne_str = ', '.join(colonne)
                placeholders = ', '.join(['?'] * len(colonne))
                query = f"INSERT INTO distinte_riba ({colonne_str}) VALUES ({placeholders})"
                cur.execute(query, valori)
                distinta_id = cur.lastrowid
                
                # Verifica e crea colonne nella tabella riba se non esistono
                try:
                    cur.execute("SELECT numero_riba FROM riba LIMIT 1")
                    colonna_numero_riba_esiste = True
                except:
                    colonna_numero_riba_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN numero_riba TEXT")
                        conn.commit()
                        colonna_numero_riba_esiste = True
                    except:
                        pass
                
                try:
                    cur.execute("SELECT data_emissione FROM riba LIMIT 1")
                    colonna_data_emissione_esiste = True
                except:
                    colonna_data_emissione_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN data_emissione TEXT")
                        conn.commit()
                        colonna_data_emissione_esiste = True
                    except:
                        pass
                
                try:
                    cur.execute("SELECT banca_appoggio FROM riba LIMIT 1")
                    colonna_banca_appoggio_esiste = True
                except:
                    colonna_banca_appoggio_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN banca_appoggio TEXT")
                        conn.commit()
                        colonna_banca_appoggio_esiste = True
                    except:
                        pass
                
                # Verifica quali ID sono effettivamente riba_id esistenti e quali sono scadenza_id
                # Questa verifica deve avvenire PRIMA della creazione delle righe
                ids_riba_verificati = []
                scadenze_da_creare_da_ids = []
                
                for riba_id in ids_riba:
                    # Verifica se esiste nella tabella riba
                    cur.execute("SELECT id, scadenza_id FROM riba WHERE id = ?", (riba_id,))
                    row = cur.fetchone()
                    if row:
                        ids_riba_verificati.append(riba_id)
                    else:
                        # Non esiste in riba, probabilmente è uno scadenza_id
                        # Verifica se esiste in scadenze
                        cur.execute("SELECT id, importo_scadenza, data_scadenza FROM scadenze WHERE id = ?", (riba_id,))
                        scad_row = cur.fetchone()
                        if scad_row:
                            scadenze_da_creare_da_ids.append((riba_id, float(scad_row[1]) if scad_row[1] else 0.0, scad_row[2]))
                
                # Aggiungi le scadenze trovate alla lista da creare
                scadenze_da_creare.extend(scadenze_da_creare_da_ids)
                
                # Prima crea le righe in riba per le scadenze che non hanno ancora una riga
                for scadenza_id, importo, data_scadenza in scadenze_da_creare:
                    try:
                        # Crea la riga in riba
                        colonne_riba = ['scadenza_id', 'stato', 'distinta_id']
                        valori_riba = [scadenza_id, 'Emessa', distinta_id]
                        
                        if colonna_numero_riba_esiste:
                            colonne_riba.append('numero_riba')
                            valori_riba.append(num_distinta)
                        if colonna_data_emissione_esiste:
                            colonne_riba.append('data_emissione')
                            valori_riba.append(data_distinta)
                        if colonna_banca_appoggio_esiste:
                            colonne_riba.append('banca_appoggio')
                            valori_riba.append(banca_selezionata)
                        
                        # Verifica se esiste già una colonna data_scadenza o importo (per compatibilità)
                        try:
                            cur.execute("SELECT data_scadenza FROM riba LIMIT 1")
                            colonne_riba.append('data_scadenza')
                            valori_riba.append(data_scadenza if data_scadenza else '')
                        except:
                            pass
                        try:
                            cur.execute("SELECT importo FROM riba LIMIT 1")
                            colonne_riba.append('importo')
                            valori_riba.append(importo)
                        except:
                            pass
                        
                        colonne_str = ', '.join(colonne_riba)
                        placeholders = ', '.join(['?'] * len(colonne_riba))
                        query_insert = f"INSERT INTO riba ({colonne_str}) VALUES ({placeholders})"
                        cur.execute(query_insert, valori_riba)
                        # Aggiungi l'ID della riga appena creata alla lista delle RiBa verificate
                        nuovo_id = cur.lastrowid
                        ids_riba_verificati.append(nuovo_id)
                    except Exception as e:
                        messagebox.showerror('Errore', f'Errore creando riga riba per scadenza {scadenza_id}: {str(e)}')
                        raise
                
                # Verifica quali ID sono effettivamente riba_id esistenti e quali sono scadenza_id
                ids_riba_verificati = []
                scadenze_da_creare_da_ids = []
                
                for riba_id in ids_riba:
                    # Verifica se esiste nella tabella riba
                    cur.execute("SELECT id, scadenza_id FROM riba WHERE id = ?", (riba_id,))
                    row = cur.fetchone()
                    if row:
                        ids_riba_verificati.append(riba_id)
                    else:
                        # Non esiste in riba, probabilmente è uno scadenza_id
                        # Verifica se esiste in scadenze
                        cur.execute("SELECT id, importo_scadenza, data_scadenza FROM scadenze WHERE id = ?", (riba_id,))
                        scad_row = cur.fetchone()
                        if scad_row:
                            scadenze_da_creare_da_ids.append((riba_id, float(scad_row[1]) if scad_row[1] else 0.0, scad_row[2]))
                
                # Aggiungi le scadenze trovate alla lista da creare
                scadenze_da_creare.extend(scadenze_da_creare_da_ids)
                
                # Ora aggiorna tutte le RiBa (quelle esistenti e quelle appena create)
                if ids_riba_verificati:
                    try:
                        # Costruisci query UPDATE dinamica
                        update_cols = ['distinta_id', "stato = 'Emessa'"]
                        update_vals = []
                        
                        if colonna_numero_riba_esiste:
                            update_cols.append('numero_riba')
                            update_vals.append(num_distinta)
                        if colonna_data_emissione_esiste:
                            update_cols.append('data_emissione')
                            update_vals.append(data_distinta)
                        if colonna_banca_appoggio_esiste:
                            update_cols.append('banca_appoggio')
                            update_vals.append(banca_selezionata)
                        
                        # Costruisci la query UPDATE
                        set_clauses = []
                        param_idx = 0
                        for col in update_cols:
                            if '=' in col:
                                set_clauses.append(col)
                            else:
                                set_clauses.append(f"{col} = ?")
                                param_idx += 1
                        
                        query_update = f"UPDATE riba SET {', '.join(set_clauses)} WHERE id = ?"
                        
                        # Prepara i parametri per ogni riga
                        all_params = []
                        for riba_id in ids_riba_verificati:
                            params = [distinta_id]
                            params.extend(update_vals)
                            params.append(riba_id)
                            all_params.append(tuple(params))
                        
                        cur.executemany(query_update, all_params)
                    except Exception as e:
                        messagebox.showerror('Errore', f'Errore aggiornando righe riba: {str(e)}')
                        raise
                
                # 🔹 STEP: Gestisci note di credito selezionate
                # Raccogli le note di credito selezionate
                note_credito_selez = []
                for item in nc_listbox.get_children():
                    if item in selezioni_nc and selezioni_nc[item]:
                        tags = nc_listbox.item(item, 'tags')
                        scadenza_id = None
                        documento_id = None
                        for t in tags:
                            if t.startswith('scadenza_id_'):
                                scadenza_id = int(t.replace('scadenza_id_', '', 1))
                            elif t.startswith('documento_id_'):
                                documento_id = int(t.replace('documento_id_', '', 1))
                        if scadenza_id and documento_id:
                            residuo = importi_nc_dict.get(item, 0.0)
                            note_credito_selez.append({
                                'scadenza_id': scadenza_id,
                                'documento_id': documento_id,
                                'residuo': residuo
                            })
                
                # Se ci sono note di credito, crea le associazioni
                if note_credito_selez:
                    # Recupera i documenti delle RiBa selezionate
                    riba_documenti = {}
                    for item in listbox.get_children():
                        if item in selezioni and selezioni[item]:
                            tags = listbox.item(item, 'tags')
                            riba_id = None
                            documento_id = None
                            for t in tags:
                                if t.startswith('id_'):
                                    riba_id = int(t[3:])
                                elif t.startswith('documento_id_'):
                                    documento_id = int(t.replace('documento_id_', '', 1))
                            if riba_id and documento_id:
                                # Recupera importo RiBa
                                importo_riba = importi_dict.get(item, 0.0)
                                riba_documenti[riba_id] = {
                                    'documento_id': documento_id,
                                    'importo': importo_riba,
                                    'importo_netto': importo_riba
                                }
                    
                    # Distribuisci le note di credito alle RiBa (FIFO)
                    # Ordina RiBa per data scadenza
                    cur.execute("""
                        SELECT r.id, sc.data_scadenza, sc.importo_scadenza AS importo
                        FROM riba r
                        LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                        WHERE r.id IN ({})
                        ORDER BY sc.data_scadenza
                    """.format(','.join(['?'] * len(ids_riba_verificati))), ids_riba_verificati)
                    riba_ordered = cur.fetchall()
                    
                    # Ordina NC per data documento
                    note_credito_selez.sort(key=lambda x: x['residuo'], reverse=True)  # Prima le più grandi
                    
                    residuo_nc_totale = sum(nc['residuo'] for nc in note_credito_selez)
                    
                    # Verifica se esiste tipo_movimento
                    try:
                        cur.execute("SELECT tipo_movimento FROM pagamenti LIMIT 1")
                        has_tipo_movimento = True
                    except:
                        has_tipo_movimento = False
                    
                    # Applica NC alle RiBa
                    for riba_row in riba_ordered:
                        riba_id = riba_row[0]
                        if riba_id not in riba_documenti:
                            continue
                        
                        if residuo_nc_totale <= 0.01:
                            break
                        
                        importo_riba = riba_documenti[riba_id]['importo']
                        importo_da_stornare = min(importo_riba, residuo_nc_totale)
                        
                        if importo_da_stornare > 0.01:
                            # Trova la NC da applicare
                            for nc in note_credito_selez:
                                if nc['residuo'] <= 0.01:
                                    continue
                                importo_nc_disponibile = min(nc['residuo'], importo_da_stornare)
                                if importo_nc_disponibile > 0.01:
                                    # Crea pagamento per tracciare l'applicazione della NC
                                    if has_tipo_movimento:
                                        cur.execute("""
                                            INSERT INTO pagamenti 
                                            (data_pagamento, importo_pagamento, totale, modalita_pagamento, tipo_movimento) 
                                            VALUES (?, ?, ?, 'NOTA_CREDITO_APPLICATA', ?)
                                        """, (data_distinta, 0, 0, 'INCASSO'))
                                    else:
                                        cur.execute("""
                                            INSERT INTO pagamenti 
                                            (data_pagamento, importo_pagamento, totale, modalita_pagamento) 
                                            VALUES (?, ?, ?, 'NOTA_CREDITO_APPLICATA')
                                        """, (data_distinta, 0, 0))
                                    pagamento_nc_id = cur.lastrowid
                                    
                                    # Associazione: NC applicata al documento RiBa
                                    cur.execute("""
                                        INSERT INTO associazioni_pagamenti 
                                        (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                                        VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)
                                    """, (pagamento_nc_id, riba_documenti[riba_id]['documento_id'], importo_nc_disponibile, data_distinta))
                                    
                                    # Associazione: NC stessa (per tracciare che è stata utilizzata)
                                    cur.execute("""
                                        INSERT INTO associazioni_pagamenti 
                                        (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                                        VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)
                                    """, (pagamento_nc_id, nc['documento_id'], importo_nc_disponibile, data_distinta))
                                    
                                    nc['residuo'] -= importo_nc_disponibile
                                    residuo_nc_totale -= importo_nc_disponibile
                                    riba_documenti[riba_id]['importo_netto'] -= importo_nc_disponibile
                                    if riba_documenti[riba_id]['importo_netto'] < 0:
                                        riba_documenti[riba_id]['importo_netto'] = 0
                                    break
                
                conn.commit()
                conn.close()
                
                # Messaggio riepilogativo
                totale_riba = sum(importi_dict.get(item, 0) for item in listbox.get_children() 
                                 if item in selezioni and selezioni[item])
                totale_nc = sum(importi_nc_dict.get(item, 0) for item in nc_listbox.get_children() 
                               if item in selezioni_nc and selezioni_nc[item])
                importo_netto = max(0, totale_riba - totale_nc)
                
                totale_riba_count = len(ids_riba_verificati)
                msg = f'Distinta {num_distinta} (ID: {distinta_id}) creata con {totale_riba_count} Ri.Ba.\n'
                msg += f'Totale RiBa: € {totale_riba:,.2f}\n'
                if totale_nc > 0.01:
                    msg += f'Note Credito applicate: € {totale_nc:,.2f}\n'
                    msg += f'Importo netto distinta: € {importo_netto:,.2f}'
                else:
                    msg += f'Importo distinta: € {importo_netto:,.2f}'
                
                messagebox.showinfo('OK', msg)
                win.destroy()
                # Ricarica i dati della tabella distinte
                self.load_data()
                # Se riba_tab è disponibile, ricarica anche i suoi dati
                if self.riba_tab:
                    try:
                        # Verifica che il widget esista ancora
                        if hasattr(self.riba_tab, 'winfo_exists') and self.riba_tab.winfo_exists():
                            self.riba_tab.load_data()
                    except tk.TclError:
                        # Widget distrutto, ignora
                        pass
                    except Exception as e:
                        print(f"Errore nel ricaricamento riba_tab: {e}")
            except Exception as e:
                messagebox.showerror('Errore DB', str(e))

        btn_frame = tk.Frame(frame, bg=Style.WHITE)
        btn_frame.pack(fill='x', pady=(10,0))
        tk.Button(btn_frame, text='Crea Distinta', bg='#4CAF50', fg='white', command=crea_distinta).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Annulla', bg='#f44336', fg='white', command=win.destroy).pack(side='left')

    def modifica_distinta(self):
        """Modifica la distinta selezionata"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Attenzione', 'Seleziona una distinta')
            return
        
        item = self.tree.item(sel[0])
        values = item['values']
        distinta_id = values[0]
        
        self._modifica_distinta_window(distinta_id)

    def stampa_distinta(self):
        """Stampa la distinta selezionata"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Attenzione', 'Seleziona una distinta')
            return
        
        item = self.tree.item(sel[0])
        values = item['values']
        distinta_id = values[0]
        
        if self.riba_tab:
            self.riba_tab.esporta_pdf_by_distinta(str(distinta_id), apri_per_stampa=True)
        else:
            # Fallback se riba_tab non è disponibile
            self._esporta_pdf_by_distinta(str(distinta_id), apri_per_stampa=True)

    def cancella_distinta(self):
        """Elimina definitivamente la distinta selezionata"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Attenzione', 'Seleziona una distinta')
            return
        
        item = self.tree.item(sel[0])
        values = item['values']
        distinta_id = values[0]
        numero_distinta = values[1] if len(values) > 1 else str(distinta_id)
        
        # Chiedi conferma
        risposta = messagebox.askyesno(
            'Conferma eliminazione',
            f'Sei sicuro di voler eliminare definitivamente la distinta n. {numero_distinta}?\n\n'
            f'Questa operazione non può essere annullata e tutte le Ri.Ba. associate verranno rese disponibili.'
        )
        
        if not risposta:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica quali colonne esistono nella tabella riba
            try:
                cur.execute("SELECT numero_riba FROM riba LIMIT 1")
                colonna_numero_riba_esiste = True
            except:
                colonna_numero_riba_esiste = False
            
            try:
                cur.execute("SELECT data_emissione FROM riba LIMIT 1")
                colonna_data_emissione_esiste = True
            except:
                colonna_data_emissione_esiste = False
            
            try:
                cur.execute("SELECT banca_appoggio FROM riba LIMIT 1")
                colonna_banca_appoggio_esiste = True
            except:
                colonna_banca_appoggio_esiste = False
            
            # Resetta tutte le RiBa associate alla distinta
            update_cols = ['distinta_id = NULL', "stato = 'Da emettere'"]
            
            if colonna_numero_riba_esiste:
                update_cols.append('numero_riba = NULL')
            if colonna_data_emissione_esiste:
                update_cols.append('data_emissione = NULL')
            if colonna_banca_appoggio_esiste:
                update_cols.append('banca_appoggio = NULL')
            
            query_reset = f"UPDATE riba SET {', '.join(update_cols)} WHERE distinta_id = ?"
            cur.execute(query_reset, (distinta_id,))
            
            # Elimina la distinta
            cur.execute("DELETE FROM distinte_riba WHERE id = ?", (distinta_id,))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo('Distinta eliminata', f'La distinta n. {numero_distinta} è stata eliminata definitivamente.')
            
            # Ricarica i dati
            self.load_data()
            
            # Aggiorna anche la tab riba se disponibile
            if self.riba_tab:
                try:
                    if hasattr(self.riba_tab, 'winfo_exists') and self.riba_tab.winfo_exists():
                        self.riba_tab.load_data()
                except tk.TclError:
                    pass
                except Exception as e:
                    print(f"Errore nel ricaricamento riba_tab: {e}")
                    
        except Exception as e:
            messagebox.showerror('Errore', f'Errore durante l\'eliminazione della distinta:\n{str(e)}')

    def _esporta_pdf_by_distinta(self, distinta_id, apri_per_stampa=False):
        """Esporta PDF per una distinta (metodo fallback)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica se esiste la colonna banca_id
            cur.execute("PRAGMA table_info(distinte_riba)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_banca_id = 'banca_id' in colonne_nomi
            
            # Costruisci query dinamica per recuperare la banca
            if has_banca_id:
                query_distinta = """
                    SELECT di.id, di.numero_distinta, di.data_distinta, b.denominazione AS banca
                    FROM distinte_riba di
                    LEFT JOIN banche b ON di.banca_id = b.id
                    WHERE di.id = ?
                """
            else:
                query_distinta = """
                    SELECT id, numero_distinta, data_distinta, NULL AS banca
                    FROM distinte_riba
                    WHERE id = ?
                """
            
            cur.execute(query_distinta, (distinta_id,))
            dist = cur.fetchone()
            if not dist:
                messagebox.showerror('Errore', 'Distinta non trovata')
                conn.close()
                return
            # Recupera anche la data del documento
            cur.execute("""
                SELECT r.id, s.ragione_sociale, d.numero_documento, d.data_documento, sc.data_scadenza, sc.importo_scadenza AS importo, r.stato
                FROM riba r
                LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                WHERE r.distinta_id = ?
                ORDER BY sc.data_scadenza
            """, (distinta_id,))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                messagebox.showinfo('Info', 'Nessuna Ri.Ba. nella distinta')
                return

            outdir = Path('distinte_pdf')
            outdir.mkdir(exist_ok=True)
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = outdir / f"Distinta_{distinta_id}_{date_str}.pdf"

            c = canvas.Canvas(str(filename), pagesize=A4)
            width, height = A4
            x_margin = 40
            y = height - 60

            numero_display = dist[1] if dist[1] else str(dist[0])
            c.setFont('Helvetica-Bold', 14)
            c.drawString(x_margin, y, f"Distinta Ri.Ba. n. {numero_display}")
            c.setFont('Helvetica', 10)
            if dist[2]:
                c.drawString(x_margin, y-18, f"Data distinta: {dist[2]}")
            if dist[3]:
                c.drawString(x_margin, y-36, f"Banca di emissione: {dist[3]}")

            y -= 60
            c.setFont('Helvetica-Bold', 10)
            c.drawString(x_margin, y, "Cliente")
            c.drawString(x_margin+180, y, "Data")
            c.drawString(x_margin+250, y, "Documento")
            c.drawString(x_margin+360, y, "Scadenza")
            c.drawString(x_margin+450, y, "Importo")
            y -= 14
            c.setFont('Helvetica', 10)

            total = 0.0
            for r in rows:
                if y < 80:
                    c.showPage()
                    y = height - 60
                cliente = r[1] or ''
                docu = r[2] or ''
                data_doc = r[3] or ''
                scad = r[4] or ''
                imp = float(r[5]) if r[5] else 0.0
                stato = r[6] or ''
                c.drawString(x_margin, y, cliente[:35])
                c.drawString(x_margin+180, y, data_doc[:10])
                c.drawString(x_margin+250, y, docu)
                c.drawString(x_margin+360, y, scad)
                c.drawRightString(x_margin+520, y, f"€ {imp:,.2f}")
                y -= 14
                total += imp

            if y < 100:
                c.showPage()
                y = height - 60
            y -= 10
            c.setFont('Helvetica-Bold', 11)
            c.drawRightString(x_margin+520, y, f"Totale: € {total:,.2f}")

            c.save()
            
            if apri_per_stampa:
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    try:
                        os.startfile(str(filename))
                    except:
                        subprocess.Popen(['start', str(filename)], shell=True)
                else:
                    subprocess.Popen(['xdg-open', str(filename)])
                # Nessun messaggio di conferma per la stampa
            else:
                messagebox.showinfo('PDF creato', f'File generato: {filename}')
        except Exception as e:
            messagebox.showerror('Errore PDF', str(e))

    def _modifica_distinta_window(self, distinta_id):
        """Finestra per modificare i dati della distinta e aggiungere Ri.Ba."""
        win_mod = tk.Toplevel(self)
        win_mod.title(f'Modifica Distinta {distinta_id}')
        win_mod.geometry('600x650')
        win_mod.transient(self)

        frame_mod = tk.Frame(win_mod, bg=Style.WHITE, padx=20, pady=20)
        frame_mod.pack(fill='both', expand=True)

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica quali colonne esistono
            cur.execute("PRAGMA table_info(distinte_riba)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            
            # Costruisci query dinamica
            select_cols = []
            if 'numero_distinta' in colonne_nomi:
                select_cols.append('numero_distinta')
            else:
                select_cols.append('NULL AS numero_distinta')
                
            if 'data_distinta' in colonne_nomi:
                select_cols.append('data_distinta')
            else:
                select_cols.append('NULL AS data_distinta')
                
            if 'banca_id' in colonne_nomi:
                select_cols.append('banca_id')
            else:
                select_cols.append('NULL AS banca_id')
            
            query = f"SELECT {', '.join(select_cols)} FROM distinte_riba WHERE id = ?"
            cur.execute(query, (distinta_id,))
            row = cur.fetchone()
            
            # Carica banche
            try:
                cur.execute("SELECT id, denominazione FROM banche ORDER BY denominazione")
                banche_rows = cur.fetchall()
                banche_dict = {b[1]: b[0] for b in banche_rows}
                banche_nomi = [b[1] for b in banche_rows]
            except:
                banche_dict = {}
                banche_nomi = []
            
            conn.close()
        except Exception as e:
            messagebox.showerror('Errore DB', str(e))
            win_mod.destroy()
            return

        numero_val = str(distinta_id)
        data_val = datetime.now().strftime('%d/%m/%Y')
        banca_id_val = None
        
        if row:
            numero_val = row[0] if row[0] else str(distinta_id)
            # Converti data da YYYY-MM-DD a dd/mm/yyyy se necessario
            data_raw = row[1] if row[1] else None
            if data_raw:
                try:
                    # Prova formato YYYY-MM-DD
                    if '-' in data_raw and len(data_raw.split('-')) == 3:
                        parts = data_raw.split('-')
                        data_val = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    else:
                        data_val = data_raw  # Già in formato dd/mm/yyyy
                except:
                    data_val = datetime.now().strftime('%d/%m/%Y')
            else:
                data_val = datetime.now().strftime('%d/%m/%Y')
            banca_id_val = row[2] if len(row) > 2 and row[2] else None

        # Frame per dati distinta
        dati_frame = tk.LabelFrame(frame_mod, text='Dati Distinta', bg=Style.WHITE, 
                                  font=('Arial', 10, 'bold'), padx=10, pady=10)
        dati_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))

        tk.Label(dati_frame, text='Numero Distinta:', bg=Style.WHITE, 
                font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        num_entry = tk.Entry(dati_frame, font=('Arial', 10), width=20)
        num_entry.insert(0, numero_val)
        num_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dati_frame, text='Data Distinta:', bg=Style.WHITE, 
                font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        data_entry = tk.Entry(dati_frame, font=('Arial', 10), width=20)
        data_entry.insert(0, data_val)
        data_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(dati_frame, text='Banca:', bg=Style.WHITE, 
                font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        banca_combo = ttk.Combobox(dati_frame, values=banche_nomi, state='readonly', width=18)
        if banca_id_val:
            # Trova il nome della banca dal dizionario
            for nome, id_banca in banche_dict.items():
                if id_banca == banca_id_val:
                    banca_combo.set(nome)
                    break
        banca_combo.grid(row=2, column=1, padx=10, pady=5)
        
        # Frame per aggiungere Ri.Ba.
        aggiungi_frame = tk.LabelFrame(frame_mod, text='Aggiungi Ri.Ba.', bg=Style.WHITE, 
                                       font=('Arial', 10, 'bold'), padx=10, pady=10)
        aggiungi_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(0, 10))
        frame_mod.grid_rowconfigure(1, weight=1)
        frame_mod.grid_columnconfigure(0, weight=1)

        tk.Label(aggiungi_frame, text='Seleziona le Ri.Ba. da aggiungere:', bg=Style.WHITE, 
                font=('Arial', 10)).pack(anchor='w', pady=(0,5))

        # Tabella con checkbox per Ri.Ba. disponibili
        listbox_riba = ttk.Treeview(aggiungi_frame, columns=('seleziona','cliente','documento','scadenza','importo'), 
                                   show='headings', height=8)
        listbox_riba.heading('seleziona', text='  ☐')
        listbox_riba.column('seleziona', width=60, anchor='center')
        for col, w in [('cliente',200),('documento',120),('scadenza',110),('importo',90)]:
            listbox_riba.heading(col, text=col.capitalize())
            listbox_riba.column(col, width=w)
        listbox_riba.pack(fill='both', expand=True)
        listbox_riba.tag_configure('selezionata', background='#BBDEFB', foreground='#000000')

        selezioni_riba = {}
        importi_dict_riba = {}

        def toggle_checkbox_riba(event):
            try:
                # Verifica che la finestra esista ancora
                if not win_mod.winfo_exists():
                    return
                item = listbox_riba.identify_row(event.y)
                col = listbox_riba.identify_column(event.x)
                if not item:
                    return
                if col == '#1' or (col and col != '#0'):
                    if item in selezioni_riba:
                        selezioni_riba[item] = not selezioni_riba[item]
                    else:
                        selezioni_riba[item] = True
                    
                    values = list(listbox_riba.item(item, 'values'))
                    if selezioni_riba[item]:
                        values[0] = '  ✓'
                        tags = list(listbox_riba.item(item, 'tags'))
                        if 'selezionata' not in tags:
                            tags.append('selezionata')
                        listbox_riba.item(item, tags=tags)
                    else:
                        values[0] = '  ☐'
                        tags = list(listbox_riba.item(item, 'tags'))
                        if 'selezionata' in tags:
                            tags.remove('selezionata')
                        listbox_riba.item(item, tags=tags)
                    listbox_riba.item(item, values=values)
            except tk.TclError:
                # Widget distrutto, ignora
                pass
            except Exception as e:
                print(f"Errore in toggle_checkbox_riba: {e}")

        listbox_riba.bind('<ButtonRelease-1>', toggle_checkbox_riba)

        # Carica Ri.Ba. già nella distinta (selezionate) e disponibili (non selezionate)
        try:
            conn_riba = sqlite3.connect(self.db_path)
            cur_riba = conn_riba.cursor()
            
            # Prima carica le RiBa già nella distinta corrente
            cur_riba.execute("""
                SELECT r.id, s.ragione_sociale, d.numero_documento, sc.data_scadenza, sc.importo_scadenza AS importo
                FROM riba r
                LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                WHERE r.distinta_id = ?
                ORDER BY sc.data_scadenza
            """, (distinta_id,))
            rows_riba_nella_distinta = cur_riba.fetchall()
            
            # Poi carica le RiBa disponibili (partendo da scadenze per includere anche quelle senza riga in riba)
            # Escludi quelle già nella distinta corrente
            cur_riba.execute("""
                SELECT 
                    COALESCE(r.id, sc.id) AS riba_id,
                    s.ragione_sociale, 
                    d.numero_documento, 
                    sc.data_scadenza, 
                    sc.importo_scadenza AS importo
                FROM scadenze sc
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                LEFT JOIN riba r ON r.scadenza_id = sc.id
                WHERE sc.tipo_pagamento = 'RIBA'
                  AND (
                      r.id IS NULL 
                      OR (r.stato = 'Da emettere' AND (r.distinta_id IS NULL OR r.distinta_id = 0))
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM riba r2 
                      WHERE r2.scadenza_id = sc.id AND r2.distinta_id = ?
                  )
                ORDER BY sc.data_scadenza
            """, (distinta_id,))
            rows_riba_disponibili = cur_riba.fetchall()
            conn_riba.close()
            
            # Aggiungi le RiBa già nella distinta (selezionate)
            try:
                if not win_mod.winfo_exists():
                    return
                for r in rows_riba_nella_distinta:
                    try:
                        if not win_mod.winfo_exists():
                            break
                        riba_id = r[0]
                        importo = float(r[4]) if r[4] else 0.0
                        # Formatta la data scadenza se presente
                        data_scadenza = r[3] or ''
                        if data_scadenza and '-' in data_scadenza:
                            try:
                                parts = data_scadenza.split('-')
                                if len(parts) == 3 and len(parts[0]) == 4:
                                    data_scadenza = f"{parts[2]}/{parts[1]}/{parts[0]}"
                            except:
                                pass
                        item_id = listbox_riba.insert('', tk.END, 
                                                     values=('  ✓', r[1] or '', r[2] or '', data_scadenza, f"€ {importo:,.2f}"), 
                                                     tags=(f"id_{riba_id}", f"importo_{importo}", "selezionata"))
                        selezioni_riba[item_id] = True
                        importi_dict_riba[item_id] = importo
                    except tk.TclError:
                        # Widget distrutto durante l'inserimento, interrompi
                        break
                
                # Aggiungi le RiBa disponibili (non selezionate)
                for r in rows_riba_disponibili:
                    try:
                        if not win_mod.winfo_exists():
                            break
                        riba_id = r[0]  # Può essere r.id o sc.id
                        importo = float(r[4]) if r[4] else 0.0
                        # Formatta la data scadenza se presente
                        data_scadenza = r[3] or ''
                        if data_scadenza and '-' in data_scadenza:
                            try:
                                parts = data_scadenza.split('-')
                                if len(parts) == 3 and len(parts[0]) == 4:
                                    data_scadenza = f"{parts[2]}/{parts[1]}/{parts[0]}"
                            except:
                                pass
                        item_id = listbox_riba.insert('', tk.END, 
                                                     values=('  ☐', r[1] or '', r[2] or '', data_scadenza, f"€ {importo:,.2f}"), 
                                                     tags=(f"id_{riba_id}", f"importo_{importo}"))
                        selezioni_riba[item_id] = False
                        importi_dict_riba[item_id] = importo
                    except tk.TclError:
                        # Widget distrutto durante l'inserimento, interrompi
                        break
            except tk.TclError:
                # Widget distrutto, ignora
                pass
        except Exception as e:
            try:
                if win_mod.winfo_exists():
                    messagebox.showerror('Errore DB', f'Errore nel caricamento Ri.Ba.: {str(e)}')
            except:
                pass

        def salva():
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                
                # Verifica e crea colonne se necessario
                try:
                    cur.execute("ALTER TABLE distinte_riba ADD COLUMN numero_distinta TEXT")
                    conn.commit()
                except:
                    pass
                try:
                    cur.execute("ALTER TABLE distinte_riba ADD COLUMN data_distinta TEXT")
                    conn.commit()
                except:
                    pass
                try:
                    cur.execute("ALTER TABLE distinte_riba ADD COLUMN banca_id INTEGER")
                    conn.commit()
                except:
                    pass
                
                numero = num_entry.get().strip()
                data = data_entry.get().strip()
                banca_nome = banca_combo.get().strip()
                banca_id = banche_dict.get(banca_nome) if banca_nome else None
                
                cur.execute("""
                    UPDATE distinte_riba 
                    SET numero_distinta = ?, data_distinta = ?, banca_id = ?
                    WHERE id = ?
                """, (numero, data, banca_id, distinta_id))
                
                # Verifica e crea colonne nella tabella riba se non esistono
                try:
                    cur.execute("SELECT numero_riba FROM riba LIMIT 1")
                    colonna_numero_riba_esiste = True
                except:
                    colonna_numero_riba_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN numero_riba TEXT")
                        conn.commit()
                        colonna_numero_riba_esiste = True
                    except:
                        pass
                
                try:
                    cur.execute("SELECT data_emissione FROM riba LIMIT 1")
                    colonna_data_emissione_esiste = True
                except:
                    colonna_data_emissione_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN data_emissione TEXT")
                        conn.commit()
                        colonna_data_emissione_esiste = True
                    except:
                        pass
                
                try:
                    cur.execute("SELECT banca_appoggio FROM riba LIMIT 1")
                    colonna_banca_appoggio_esiste = True
                except:
                    colonna_banca_appoggio_esiste = False
                    try:
                        cur.execute("ALTER TABLE riba ADD COLUMN banca_appoggio TEXT")
                        conn.commit()
                        colonna_banca_appoggio_esiste = True
                    except:
                        pass
                
                # Raccogli tutte le RiBa selezionate
                ids_riba_selezionate = []
                for item in listbox_riba.get_children():
                    if item in selezioni_riba and selezioni_riba[item]:
                        tags = listbox_riba.item(item, 'tags')
                        for t in tags:
                            if t.startswith('id_'):
                                ids_riba_selezionate.append(int(t[3:]))
                                break
                
                # Prima rimuovi le RiBa che erano nella distinta ma ora sono deselezionate
                # Trova tutte le RiBa attualmente nella distinta
                cur.execute("SELECT id FROM riba WHERE distinta_id = ?", (distinta_id,))
                riba_attuali = [row[0] for row in cur.fetchall()]
                
                # Rimuovi quelle che non sono più selezionate
                riba_da_rimuovere = [r_id for r_id in riba_attuali if r_id not in ids_riba_selezionate]
                
                if riba_da_rimuovere:
                    # Costruisci query UPDATE dinamica per rimuovere
                    update_cols_remove = ['distinta_id = NULL', "stato = 'Da emettere'"]
                    
                    if colonna_numero_riba_esiste:
                        update_cols_remove.append('numero_riba = NULL')
                    if colonna_data_emissione_esiste:
                        update_cols_remove.append('data_emissione = NULL')
                    if colonna_banca_appoggio_esiste:
                        update_cols_remove.append('banca_appoggio = NULL')
                    
                    query_remove = f"UPDATE riba SET {', '.join(update_cols_remove)} WHERE id = ?"
                    cur.executemany(query_remove, [(r_id,) for r_id in riba_da_rimuovere])
                
                # Aggiorna tutte le Ri.Ba. esistenti della distinta con i nuovi dati (quelle che rimangono)
                update_existing_cols = []
                update_existing_vals = []
                
                if colonna_numero_riba_esiste:
                    update_existing_cols.append('numero_riba')
                    update_existing_vals.append(numero)
                if colonna_data_emissione_esiste:
                    update_existing_cols.append('data_emissione')
                    update_existing_vals.append(data)
                if colonna_banca_appoggio_esiste:
                    update_existing_cols.append('banca_appoggio')
                    update_existing_vals.append(banca_nome)
                
                # Aggiorna solo le RiBa che rimangono nella distinta
                riba_da_aggiornare = [r_id for r_id in ids_riba_selezionate if r_id in riba_attuali]
                if riba_da_aggiornare and update_existing_cols:
                    set_clauses_existing = [f"{col} = ?" for col in update_existing_cols]
                    query_update_existing = f"UPDATE riba SET {', '.join(set_clauses_existing)} WHERE id = ?"
                    all_params_update = [(val,) for val in update_existing_vals]
                    for riba_id in riba_da_aggiornare:
                        params = list(update_existing_vals)
                        params.append(riba_id)
                        cur.execute(query_update_existing, tuple(params))
                
                # Aggiungi le nuove RiBa selezionate (quelle che non erano già nella distinta)
                riba_da_aggiungere = [r_id for r_id in ids_riba_selezionate if r_id not in riba_attuali]
                
                if riba_da_aggiungere:
                    # Separa riba_id esistenti da scadenza_id (che richiedono creazione di nuova riga)
                    riba_id_esistenti = []
                    scadenze_da_creare = []
                    
                    for identificatore in riba_da_aggiungere:
                        # Verifica se esiste una riga in riba con questo ID
                        cur.execute("SELECT id, scadenza_id FROM riba WHERE id = ?", (identificatore,))
                        row = cur.fetchone()
                        if row:
                            # È un riba_id esistente
                            riba_id_esistenti.append(identificatore)
                        else:
                            # Verifica se è uno scadenza_id
                            cur.execute("SELECT id, importo_scadenza, data_scadenza FROM scadenze WHERE id = ?", (identificatore,))
                            scad_row = cur.fetchone()
                            if scad_row:
                                scadenze_da_creare.append((identificatore, float(scad_row[1]) if scad_row[1] else 0.0, scad_row[2]))
                    
                    # Prima crea le righe in riba per le scadenze che non hanno ancora una riga
                    for scadenza_id, importo, data_scadenza in scadenze_da_creare:
                        try:
                            colonne_riba = ['scadenza_id', 'stato', 'distinta_id']
                            valori_riba = [scadenza_id, 'Emessa', distinta_id]
                            
                            if colonna_numero_riba_esiste:
                                colonne_riba.append('numero_riba')
                                valori_riba.append(numero)
                            if colonna_data_emissione_esiste:
                                colonne_riba.append('data_emissione')
                                valori_riba.append(data)
                            if colonna_banca_appoggio_esiste:
                                colonne_riba.append('banca_appoggio')
                                valori_riba.append(banca_nome)
                            
                            # Verifica se esiste già una colonna data_scadenza o importo (per compatibilità)
                            try:
                                cur.execute("SELECT data_scadenza FROM riba LIMIT 1")
                                colonne_riba.append('data_scadenza')
                                valori_riba.append(data_scadenza if data_scadenza else '')
                            except:
                                pass
                            try:
                                cur.execute("SELECT importo FROM riba LIMIT 1")
                                colonne_riba.append('importo')
                                valori_riba.append(importo)
                            except:
                                pass
                            
                            colonne_str = ', '.join(colonne_riba)
                            placeholders = ', '.join(['?'] * len(colonne_riba))
                            query_insert = f"INSERT INTO riba ({colonne_str}) VALUES ({placeholders})"
                            cur.execute(query_insert, valori_riba)
                            # Aggiungi l'ID della riga appena creata alla lista delle RiBa esistenti
                            nuovo_id = cur.lastrowid
                            riba_id_esistenti.append(nuovo_id)
                        except Exception as e:
                            messagebox.showerror('Errore', f'Errore creando riga riba per scadenza {scadenza_id}: {str(e)}')
                            raise
                    
                    # Ora aggiorna tutte le RiBa (quelle esistenti e quelle appena create)
                    if riba_id_esistenti:
                        # Costruisci query UPDATE dinamica per le nuove Ri.Ba.
                        update_cols = ['distinta_id', "stato = 'Emessa'"]
                        update_vals = []
                        
                        if colonna_numero_riba_esiste:
                            update_cols.append('numero_riba')
                            update_vals.append(numero)
                        if colonna_data_emissione_esiste:
                            update_cols.append('data_emissione')
                            update_vals.append(data)
                        if colonna_banca_appoggio_esiste:
                            update_cols.append('banca_appoggio')
                            update_vals.append(banca_nome)
                        
                        # Costruisci la query UPDATE
                        set_clauses = []
                        for col in update_cols:
                            if '=' in col:
                                set_clauses.append(col)
                            else:
                                set_clauses.append(f"{col} = ?")
                        
                        query_update = f"UPDATE riba SET {', '.join(set_clauses)} WHERE id = ?"
                        
                        # Prepara i parametri per ogni riga
                        all_params = []
                        for riba_id in riba_id_esistenti:
                            params = [distinta_id]
                            params.extend(update_vals)
                            params.append(riba_id)
                            all_params.append(tuple(params))
                        
                        cur.executemany(query_update, all_params)
                
                conn.commit()
                conn.close()
                
                msg = 'Distinta modificata'
                if riba_da_aggiungere:
                    totale_aggiunte = len(riba_id_esistenti) if 'riba_id_esistenti' in locals() else len(riba_da_aggiungere)
                    msg += f'\nAggiunte {totale_aggiunte} Ri.Ba.'
                    if 'scadenze_da_creare' in locals() and scadenze_da_creare:
                        msg += f' (di cui {len(scadenze_da_creare)} create da scadenze)'
                if riba_da_rimuovere:
                    msg += f'\nRimosse {len(riba_da_rimuovere)} Ri.Ba.'
                if not riba_da_aggiungere and not riba_da_rimuovere:
                    msg += '\nNessuna modifica alle Ri.Ba.'
                messagebox.showinfo('OK', msg)
                win_mod.destroy()
                self.load_data()
                if self.riba_tab:
                    try:
                        # Verifica che il widget esista ancora
                        if hasattr(self.riba_tab, 'winfo_exists') and self.riba_tab.winfo_exists():
                            self.riba_tab.load_data()
                    except tk.TclError:
                        # Widget distrutto, ignora
                        pass
                    except Exception as e:
                        print(f"Errore nel ricaricamento riba_tab: {e}")
            except Exception as e:
                messagebox.showerror('Errore DB', str(e))

        btn_frame = tk.Frame(frame_mod, bg=Style.WHITE)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        tk.Button(btn_frame, text='Salva', bg='#4CAF50', fg='white', 
                 command=salva).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Annulla', bg='#f44336', fg='white', 
                 command=win_mod.destroy).pack(side='left', padx=5)


