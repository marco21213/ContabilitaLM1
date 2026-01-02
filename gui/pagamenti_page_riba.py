"""
Componente RiBa Tab - Gestione RiBa come componente riutilizzabile
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
import os
# Aggiungi il percorso per gli stili (relativo alla root del progetto)
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
style_path = os.path.join(project_root, 'assets', 'style')
if style_path not in sys.path:
    sys.path.insert(0, style_path)
from styles import Style


class RibaTab(tk.Frame):
    """Componente tab per gestione RiBa - può essere usato come tab in PagamentiUnificatiApp"""
    
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.original_data = []
        self.active_filters = {
            'cliente': '', 'documento': '', 'data_scadenza': '', 'importo': '', 'stato': '', 'distinta': ''
        }
        # Dizionario per tracciare le selezioni (item_id -> bool)
        self.selezioni = {}
        # Dizionario per memorizzare gli importi (item_id -> float)
        self.importi_dict = {}

        self.configure_style()
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.create_table()
        self.load_data()

    def configure_style(self):
        """Configura lo stile per la tabella"""
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Treeview.Heading",
            background=Style.MENU_HEADER_BG,
            foreground=Style.MENU_HEADER_FG,
            font=("Arial", 10, "bold"),
            padding=(5, 8),
            relief="solid",
            borderwidth=1
        )
        style.configure(
            "Treeview",
            font=("Arial", 9),
            rowheight=26,
            background="#FFFFFF",
            foreground="#000000",
            fieldbackground="#FFFFFF"
        )
        style.map(
            "Treeview",
            background=[('selected', '#4b6cb7')],
            foreground=[('selected', 'white')]
        )

    def create_table(self):
        """Crea la tabella RiBa"""
        columns = ("SELEZIONA", "CLIENTE", "DOCUMENTO", "DATA SCADENZA", "IMPORTO", "STATO", "DISTINTA", "DATA DISTINTA")

        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode='extended')
        
        # Configura le intestazioni delle colonne
        # Solo alcune colonne hanno filtri
        filterable_columns = {
            "CLIENTE": ("cliente", "CLIENTE"),
            "DATA SCADENZA": ("data_scadenza", "DATA SCADENZA"),
            "STATO": ("stato", "STATO"),
            "DISTINTA": ("distinta", "DISTINTA")
        }
        
        for col in columns:
            if col == 'SELEZIONA':
                # Colonna checkbox
                self.tree.heading('SELEZIONA', text='  ☐')
            elif col in filterable_columns:
                field_key, col_title = filterable_columns[col]
                self.tree.heading(col, text=f"{col} ⧗", command=lambda f=field_key, c=col_title: self.show_filter_menu(f, c))
            else:
                self.tree.heading(col, text=col)

        # Colonna checkbox
        self.tree.column('SELEZIONA', width=70, anchor='center')
        
        widths = [("CLIENTE", 200), ("DOCUMENTO", 120), ("DATA SCADENZA", 110), ("IMPORTO", 90),
                  ("STATO", 100), ("DISTINTA", 100), ("DATA DISTINTA", 100)]
        for name, w in widths:
            anchor = 'w' if name == 'CLIENTE' else 'center'
            self.tree.column(name, width=w, anchor=anchor)

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
        self.tree.tag_configure('selezionata', background='#BBDEFB', foreground='#000000')

        # Bind click per checkbox
        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<Double-1>', self.on_tree_double_click)

    def load_data(self):
        """Carica i dati delle RiBa"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica se la colonna distinta_id esiste nella tabella riba
            try:
                cur.execute("PRAGMA table_info(riba)")
                colonne_riba = [col[1] for col in cur.fetchall()]
                if 'distinta_id' not in colonne_riba:
                    cur.execute("ALTER TABLE riba ADD COLUMN distinta_id INTEGER")
                    conn.commit()
            except Exception as e:
                print(f"Errore verifica/aggiunta colonna distinta_id: {e}")
            
            # Verifica quali colonne esistono in distinte_riba
            try:
                cur.execute("PRAGMA table_info(distinte_riba)")
                colonne_info = cur.fetchall()
                colonne_nomi = [col[1] for col in colonne_info]
                has_numero_distinta = 'numero_distinta' in colonne_nomi
                has_data_distinta = 'data_distinta' in colonne_nomi
            except:
                has_numero_distinta = False
                has_data_distinta = False
            
            # Costruisci query dinamica
            # Usa COALESCE per usare sc.id se r.id è NULL (scadenza senza riga in riba)
            select_parts = [
                'COALESCE(r.id, sc.id) AS riba_id', 's.ragione_sociale', 'd.numero_documento', 'sc.data_scadenza', 
                'sc.importo_scadenza AS importo', 'COALESCE(r.stato, \'Da emettere\') AS stato', 'di.id AS distinta_id'
            ]
            
            if has_numero_distinta:
                select_parts.append('di.numero_distinta')
            else:
                select_parts.append('NULL AS numero_distinta')
            
            if has_data_distinta:
                select_parts.append('di.data_distinta')
            else:
                select_parts.append('di.data_creazione AS data_distinta')
            
            # Query che parte da scadenze per mostrare tutte le scadenze con tipo_pagamento = 'RIBA'
            # anche se non hanno ancora una riga in riba
            query = f"""
                SELECT {', '.join(select_parts)}
                FROM scadenze sc
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                LEFT JOIN riba r ON r.scadenza_id = sc.id
                LEFT JOIN distinte_riba di ON r.distinta_id = di.id
                WHERE sc.tipo_pagamento = 'RIBA'
                ORDER BY sc.data_scadenza DESC
            """
            
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            
            def formatta_data(data_str):
                """Converte la data da formato database (YYYY-MM-DD o altro) a dd/mm/yyyy"""
                if not data_str:
                    return ''
                try:
                    if '-' in data_str and len(data_str.split('-')) == 3:
                        parts = data_str.split('-')
                        if len(parts[0]) == 4:
                            return f"{parts[2]}/{parts[1]}/{parts[0]}"
                    elif '/' in data_str:
                        return data_str
                except:
                    pass
                return data_str
            
            self.original_data = []
            for r in rows:
                # Gestisci il caso in cui r[0] potrebbe essere NULL (scadenza senza riga in riba)
                riba_id = r[0] if r[0] is not None else None
                distinta_id = r[6] if len(r) > 6 and r[6] else None
                numero_distinta_raw = r[7] if len(r) > 7 and r[7] else None
                data_dist_raw = r[8] if len(r) > 8 and r[8] else ""
                
                # Formatta numero distinta
                if numero_distinta_raw:
                    try:
                        num_int = int(numero_distinta_raw)
                        dati_distinta = f"{num_int:05d}"
                    except:
                        dati_distinta = str(numero_distinta_raw)
                elif distinta_id:
                    dati_distinta = f"{distinta_id:05d}"
                else:
                    dati_distinta = ""
                
                data_dist = formatta_data(data_dist_raw)
                
                # Formatta data_scadenza
                data_scadenza_str = str(r[3]) if r[3] else ""
                data_scadenza_formattata = formatta_data(data_scadenza_str)
                
                self.original_data.append({
                    'id': riba_id, 'cliente': str(r[1]) if r[1] else "", 'documento': str(r[2]) if r[2] else "",
                    'data_scadenza': data_scadenza_formattata, 'importo': float(r[4]) if r[4] else 0.0,
                    'stato': str(r[5]) if r[5] else '', 'distinta': dati_distinta, 'data_distinta': data_dist
                })
            self.apply_filters()
        except Exception as e:
            messagebox.showerror("Errore DB", str(e))
            print(f"Errore caricamento RiBa: {e}")

    def apply_filters(self):
        """Applica i filtri per RiBa - uniformato con Pagamenti"""
        filtered_data = []
        for row in self.original_data:
            match = True
            for field, fval in self.active_filters.items():
                if not fval:
                    continue
                
                # Gestione filtro data con intervallo
                if field == 'data_scadenza' and "|" in fval:
                    dal, al = fval.split("|")
                    try:
                        d = datetime.strptime(row["data_scadenza"], "%d/%m/%Y")
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
                # Per cliente e stato usa match esatto (case-insensitive)
                elif field in ('cliente', 'stato'):
                    if row[field].lower() != fval.lower():
                        match = False
                        break
                # Per importo e documento non applicare filtri (come in Pagamenti)
                elif field in ('importo', 'documento'):
                    continue
                # Per altri campi usa ricerca parziale
                elif fval not in str(row.get(field, '')).lower():
                    match = False
                    break
            
            if match:
                filtered_data.append(row)
        
        self.update_table_display(filtered_data)

    def update_table_display(self, data):
        """Aggiorna la visualizzazione della tabella RiBa"""
        selezioni_salvate = self.selezioni.copy()
        importi_salvati = self.importi_dict.copy()
        
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        self.selezioni.clear()
        self.importi_dict.clear()
        
        for n, r in enumerate(data):
            checkbox_val = '  ☐'
            
            riba_id = r['id']
            importo = r['importo']
            
            item_id = self.tree.insert("", tk.END, 
                values=[checkbox_val, r['cliente'], r['documento'], r['data_scadenza'],
                        f"€ {r['importo']:,.2f}", r['stato'], r['distinta'], r['data_distinta']],
                tags=('evenrow' if n % 2 == 0 else 'oddrow', f"id_{r['id']}", f"dist_{r['distinta']}", f"importo_{importo}"))
            
            self.importi_dict[item_id] = importo
            self.selezioni[item_id] = False

    def show_filter_menu(self, field_name, column_title):
        """Mostra il menu per i filtri RiBa - uniformato con Pagamenti"""
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

        active_filters = self.active_filters
        
        if field_name == "data_scadenza":
            # Filtro data con intervallo usando DateEntry
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
                active_filters["data_scadenza"] = f"{dal}|{al}"
                self.apply_filters()
                win.destroy()

            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_date, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        elif field_name == "cliente":
            # Autocompletamento con ricerca per cliente (come in documenti_page.py)
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
        
        elif field_name == "stato":
            # Menu a tendina per stato
            stati_disponibili = ["Da emettere", "Emessa", "Pagata"]
            
            combo = ttk.Combobox(frame, values=[""] + stati_disponibili, state="readonly", width=25)
            combo.pack(pady=(0, 15))
            
            # Imposta il valore corrente se presente
            filtro_attuale = active_filters.get(field_name, "")
            if filtro_attuale:
                # Cerca il valore corrispondente (case-insensitive)
                for val in stati_disponibili:
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
        
        else:
            # Per altri campi usa Entry semplice
            win.geometry("320x200")
            entry = tk.Entry(frame, font=("Arial", 10), width=25)
            entry.insert(0, self.active_filters.get(field_name, "").replace("|", ""))
            entry.pack(pady=(0, 15))

            def apply_text():
                self.active_filters[field_name] = entry.get().strip().lower()
                self.apply_filters()
                win.destroy()

            tk.Button(frame, text="Applica", bg="#4CAF50", fg="white",
                      width=10, command=apply_text, cursor="hand2").pack(side="left", padx=5)
            tk.Button(frame, text="Chiudi", bg="#f44336", fg="white",
                      width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        win.bind('<Escape>', lambda e: win.destroy())

    def clear_all_filters(self):
        """Cancella tutti i filtri"""
        for key in self.active_filters.keys():
            self.active_filters[key] = ""
        self.apply_filters()
        messagebox.showinfo("Filtri", "Tutti i filtri sono stati rimossi.")

    # Metodi pubblici per i pulsanti (chiamati dal parent)
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

        listbox.bind('<ButtonRelease-1>', toggle_checkbox)
        
        def carica_note_credito():
            """Carica le note di credito disponibili per i clienti delle RiBa selezionate"""
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
            except Exception as e:
                messagebox.showerror('Errore DB', f'Errore nel caricamento note di credito: {str(e)}')

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
                        print(f"DEBUG: riba_id {riba_id} verificato - esiste in riba")
                    else:
                        # Non esiste in riba, probabilmente è uno scadenza_id
                        # Verifica se esiste in scadenze
                        cur.execute("SELECT id, importo_scadenza, data_scadenza FROM scadenze WHERE id = ?", (riba_id,))
                        scad_row = cur.fetchone()
                        if scad_row:
                            scadenze_da_creare_da_ids.append((riba_id, float(scad_row[1]) if scad_row[1] else 0.0, scad_row[2]))
                            print(f"DEBUG: riba_id {riba_id} non esiste in riba, ma esiste in scadenze - aggiunto alla lista da creare")
                        else:
                            print(f"DEBUG: ATTENZIONE: ID {riba_id} non esiste né in riba né in scadenze!")
                
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
                    """.format(','.join(['?'] * len(ids_riba))), ids_riba)
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
                
                totale_riba_count = len(ids_riba)
                msg = f'Distinta {num_distinta} (ID: {distinta_id}) creata con {totale_riba_count} Ri.Ba.\n'
                msg += f'Totale RiBa: € {totale_riba:,.2f}\n'
                if totale_nc > 0.01:
                    msg += f'Note Credito applicate: € {totale_nc:,.2f}\n'
                    msg += f'Importo netto distinta: € {importo_netto:,.2f}'
                else:
                    msg += f'Importo distinta: € {importo_netto:,.2f}'
                
                messagebox.showinfo('OK', msg)
                win.destroy(); self.load_data()
            except Exception as e:
                messagebox.showerror('Errore DB', str(e))

        btn_frame = tk.Frame(frame, bg=Style.WHITE)
        btn_frame.pack(fill='x', pady=(10,0))
        tk.Button(btn_frame, text='Crea Distinta', bg='#4CAF50', fg='white', command=crea_distinta).pack(side='left', padx=5)
        tk.Button(btn_frame, text='Annulla', bg='#f44336', fg='white', command=win.destroy).pack(side='left')
    
    def gestisci_distinte(self):
        """Apre la finestra di gestione distinte"""
        win = tk.Toplevel(self)
        win.title('Gestione Distinte Ri.Ba.')
        win.geometry('1000x700')
        win.transient(self)

        frame = tk.Frame(win, bg=Style.WHITE, padx=10, pady=10)
        frame.pack(fill='both', expand=True)

        # Titolo
        tk.Label(frame, text='Gestione Distinte Ri.Ba.', bg=Style.WHITE, 
                font=('Arial', 14, 'bold')).pack(pady=(0, 15))

        # Frame per la tabella (verrà posizionato dopo i bottoni)
        table_frame = tk.Frame(frame, bg=Style.WHITE)
        
        # Tabella distinte
        columns = ('ID', 'Numero', 'Data Distinta', 'Data Creazione', 'Banca', 'Num Ri.Ba.', 'Totale')
        tree_distinte = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree_distinte.heading(col, text=col)
            tree_distinte.column(col, width=100, anchor='center')
        
        # Aggiusta larghezza colonne
        tree_distinte.column('ID', width=50)
        tree_distinte.column('Numero', width=100)
        tree_distinte.column('Data Distinta', width=120)
        tree_distinte.column('Data Creazione', width=120)
        tree_distinte.column('Banca', width=200)
        tree_distinte.column('Num Ri.Ba.', width=80)
        tree_distinte.column('Totale', width=120)

        def carica_distinte():
            """Carica tutte le distinte dal database"""
            for item in tree_distinte.get_children():
                tree_distinte.delete(item)
            
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
                    data_creazione = row[3] or ''
                    banca = row[4] or ''
                    num_riba = row[5] or 0
                    totale = float(row[6]) if row[6] else 0.0
                    
                    # Formatta data distinta
                    data_distinta = formatta_data_distinta(data_distinta_raw)
                    
                    tree_distinte.insert('', tk.END, values=(
                        distinta_id, numero, data_distinta, data_creazione, 
                        banca, num_riba, f"€ {totale:,.2f}"
                    ), tags=(f"dist_{distinta_id}",))
                    
            except Exception as e:
                messagebox.showerror('Errore DB', f'Errore nel caricamento distinte: {str(e)}')

        def modifica_distinta():
            """Modifica la distinta selezionata"""
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            
            modifica_distinta_window(win, distinta_id, carica_distinte)

        def rimuovi_riba():
            """Rimuove Ri.Ba. dalla distinta selezionata"""
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            
            rimuovi_riba_window(win, distinta_id, carica_distinte)

        def esporta_pdf():
            """Esporta PDF della distinta selezionata"""
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            
            self.esporta_pdf_by_distinta(str(distinta_id))

        def stampa_distinta():
            """Stampa la distinta selezionata"""
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            
            # Usa la stessa funzione di esporta PDF e apre il file per la stampa
            self.esporta_pdf_by_distinta(str(distinta_id), apri_per_stampa=True)

        def modifica_distinta_window(parent, distinta_id, callback):
            """Finestra per modificare i dati della distinta e aggiungere Ri.Ba."""
            win_mod = tk.Toplevel(parent)
            win_mod.title(f'Modifica Distinta {distinta_id}')
            win_mod.geometry('600x650')
            win_mod.transient(parent)

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

            listbox_riba.bind('<ButtonRelease-1>', toggle_checkbox_riba)

            # Carica Ri.Ba. disponibili
            try:
                conn_riba = sqlite3.connect(self.db_path)
                cur_riba = conn_riba.cursor()
                cur_riba.execute("""
                    SELECT r.id, s.ragione_sociale, d.numero_documento, sc.data_scadenza, sc.importo_scadenza AS importo
                    FROM riba r
                    LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                    LEFT JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN soggetti s ON d.soggetto_id = s.id
                    WHERE r.stato = 'Da emettere' AND (r.distinta_id IS NULL OR r.distinta_id = 0)
                    ORDER BY sc.data_scadenza
                """)
                rows_riba = cur_riba.fetchall()
                conn_riba.close()
                
                for r in rows_riba:
                    riba_id = r[0]
                    importo = float(r[4]) if r[4] else 0.0
                    item_id = listbox_riba.insert('', tk.END, 
                                                 values=('  ☐', r[1] or '', r[2] or '', r[3] or '', f"€ {importo:,.2f}"), 
                                                 tags=(f"id_{riba_id}", f"importo_{importo}"))
                    selezioni_riba[item_id] = False
                    importi_dict_riba[item_id] = importo
            except Exception as e:
                messagebox.showerror('Errore DB', f'Errore nel caricamento Ri.Ba.: {str(e)}')

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
                    
                    # Verifica e crea colonne nella tabella riba se non esistono (per aggiornare anche le Ri.Ba. esistenti)
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
                    
                    # Aggiorna tutte le Ri.Ba. esistenti della distinta con i nuovi dati
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
                    
                    if update_existing_cols:
                        set_clauses_existing = [f"{col} = ?" for col in update_existing_cols]
                        query_update_existing = f"UPDATE riba SET {', '.join(set_clauses_existing)} WHERE distinta_id = ?"
                        cur.execute(query_update_existing, tuple(update_existing_vals + [distinta_id]))
                    
                    # Aggiungi Ri.Ba. selezionate
                    ids_riba = []
                    for item in listbox_riba.get_children():
                        if item in selezioni_riba and selezioni_riba[item]:
                            tags = listbox_riba.item(item, 'tags')
                            for t in tags:
                                if t.startswith('id_'):
                                    ids_riba.append(int(t[3:]))
                    
                    if ids_riba:
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
                        for riba_id in ids_riba:
                            params = [distinta_id]
                            params.extend(update_vals)
                            params.append(riba_id)
                            all_params.append(tuple(params))
                        
                        cur.executemany(query_update, all_params)
                    
                    conn.commit()
                    conn.close()
                    
                    msg = 'Distinta modificata'
                    if ids_riba:
                        msg += f' e aggiunte {len(ids_riba)} Ri.Ba.'
                    messagebox.showinfo('OK', msg)
                    win_mod.destroy()
                    callback()
                except Exception as e:
                    messagebox.showerror('Errore DB', str(e))

            btn_frame = tk.Frame(frame_mod, bg=Style.WHITE)
            btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
            tk.Button(btn_frame, text='Salva', bg='#4CAF50', fg='white', 
                     command=salva).pack(side='left', padx=5)
            tk.Button(btn_frame, text='Annulla', bg='#f44336', fg='white', 
                     command=win_mod.destroy).pack(side='left', padx=5)

        def rimuovi_riba_window(parent, distinta_id, callback):
            """Finestra per rimuovere Ri.Ba. da una distinta"""
            win_rem = tk.Toplevel(parent)
            win_rem.title(f'Rimuovi Ri.Ba. da Distinta {distinta_id}')
            win_rem.geometry('800x600')
            win_rem.transient(parent)

            frame_rem = tk.Frame(win_rem, bg=Style.WHITE, padx=10, pady=10)
            frame_rem.pack(fill='both', expand=True)

            tk.Label(frame_rem, text='Seleziona le Ri.Ba. da rimuovere dalla distinta:', bg=Style.WHITE, 
                    font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0,10))

            # Tabella con checkbox
            listbox = ttk.Treeview(frame_rem, columns=('seleziona','cliente','documento','scadenza','importo'), show='headings')
            listbox.heading('seleziona', text='  ☐')
            listbox.column('seleziona', width=60, anchor='center')
            for col, w in [('cliente',250),('documento',120),('scadenza',110),('importo',90)]:
                listbox.heading(col, text=col.capitalize())
                listbox.column(col, width=w)
            listbox.pack(fill='both', expand=True)
            
            listbox.tag_configure('selezionata', background='#BBDEFB', foreground='#000000')

            selezioni = {}

            def toggle_checkbox(event):
                item = listbox.identify_row(event.y)
                col = listbox.identify_column(event.x)
                if not item:
                    return
                if col == '#1' or (col and col != '#0'):
                    if item in selezioni:
                        selezioni[item] = not selezioni[item]
                    else:
                        selezioni[item] = True
                    
                    values = list(listbox.item(item, 'values'))
                    if selezioni[item]:
                        values[0] = '  ✓'
                        tags = list(listbox.item(item, 'tags'))
                        if 'selezionata' not in tags:
                            tags.append('selezionata')
                        listbox.item(item, tags=tags)
                    else:
                        values[0] = '  ☐'
                        tags = list(listbox.item(item, 'tags'))
                        if 'selezionata' in tags:
                            tags.remove('selezionata')
                        listbox.item(item, tags=tags)
                    listbox.item(item, values=values)

            listbox.bind('<ButtonRelease-1>', toggle_checkbox)

            # Carica Ri.Ba. della distinta
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT r.id, s.ragione_sociale, d.numero_documento, sc.data_scadenza, sc.importo_scadenza AS importo
                    FROM riba r
                    LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                    LEFT JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN soggetti s ON d.soggetto_id = s.id
                    WHERE r.distinta_id = ?
                    ORDER BY sc.data_scadenza
                """, (distinta_id,))
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror('Errore DB', str(e))
                win_rem.destroy()
                return

            for r in rows:
                riba_id = r[0]
                importo = float(r[4]) if r[4] else 0.0
                item_id = listbox.insert('', tk.END, 
                                        values=('  ☐', r[1] or '', r[2] or '', r[3] or '', f"€ {importo:,.2f}"), 
                                        tags=(f"id_{riba_id}",))
                selezioni[item_id] = False

            def salva_rimozione():
                ids = []
                for item in listbox.get_children():
                    if item in selezioni and selezioni[item]:
                        tags = listbox.item(item, 'tags')
                        for t in tags:
                            if t.startswith('id_'):
                                ids.append(int(t[3:]))
                
                if not ids:
                    messagebox.showwarning('Attenzione', 'Seleziona almeno una Ri.Ba.')
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
                    
                    # Costruisci query UPDATE dinamica
                    update_cols = ['distinta_id = NULL', "stato = 'Da emettere'"]
                    
                    if colonna_numero_riba_esiste:
                        update_cols.append('numero_riba = NULL')
                    if colonna_data_emissione_esiste:
                        update_cols.append('data_emissione = NULL')
                    if colonna_banca_appoggio_esiste:
                        update_cols.append('banca_appoggio = NULL')
                    
                    query_update = f"UPDATE riba SET {', '.join(update_cols)} WHERE id = ?"
                    cur.executemany(query_update, [(i,) for i in ids])
                    
                    conn.commit()
                    conn.close()
                    messagebox.showinfo('OK', f'Rimosse {len(ids)} Ri.Ba. dalla distinta')
                    win_rem.destroy()
                    callback()
                except Exception as e:
                    messagebox.showerror('Errore DB', str(e))

            btn_frame = tk.Frame(frame_rem, bg=Style.WHITE)
            btn_frame.pack(fill='x', pady=(10,0))
            tk.Button(btn_frame, text='Rimuovi Selezionate', bg='#f44336', fg='white', 
                     command=salva_rimozione).pack(side='left', padx=5)
            tk.Button(btn_frame, text='Annulla', bg='#607D8B', fg='white', 
                     command=win_rem.destroy).pack(side='left', padx=5)

        def carica_e_aggiorna():
            carica_distinte()
            self.load_data()  # Aggiorna anche la pagina principale

        # Funzioni wrapper che aggiornano anche la pagina principale
        def modifica_con_aggiornamento():
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            modifica_distinta_window(win, distinta_id, carica_e_aggiorna)

        def rimuovi_con_aggiornamento():
            sel = tree_distinte.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona una distinta')
                return
            item = tree_distinte.item(sel[0])
            values = item['values']
            distinta_id = values[0]
            rimuovi_riba_window(win, distinta_id, carica_e_aggiorna)

        # Bottoni azioni (layout verticale)
        btn_frame = tk.Frame(frame, bg=Style.WHITE)
        btn_frame.pack(fill='y', side='left', padx=(0, 10))

        tk.Button(btn_frame, text='Modifica', bg='#FF9800', fg='white', 
                 command=modifica_con_aggiornamento, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        tk.Button(btn_frame, text='Rimuovi Ri.Ba.', bg='#f44336', fg='white', 
                 command=rimuovi_con_aggiornamento, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        tk.Button(btn_frame, text='Esporta PDF', bg='#9C27B0', fg='white', 
                 command=esporta_pdf, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        tk.Button(btn_frame, text='Stampa', bg='#2196F3', fg='white', 
                 command=stampa_distinta, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        tk.Button(btn_frame, text='Aggiorna', bg='#607D8B', fg='white', 
                 command=carica_e_aggiorna, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        tk.Button(btn_frame, text='Chiudi', bg='#555555', fg='white', 
                 command=win.destroy, font=('Arial', 10, 'bold'), width=15).pack(pady=5)
        
        # Posiziona table_frame con scrollbar
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree_distinte.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree_distinte.xview)
        tree_distinte.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        tree_distinte.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Posiziona table_frame dopo i bottoni
        table_frame.pack(fill='both', expand=True, side='left')

        carica_distinte()
    
    def paga_riba(self):
        """Gestisce il pagamento delle RiBa selezionate"""
        ids_riba = []
        for item in self.tree.get_children():
            if item in self.selezioni and self.selezioni[item]:
                tags = self.tree.item(item, 'tags')
                for t in tags:
                    if t.startswith('id_'):
                        riba_id = int(t[3:])
                        ids_riba.append(riba_id)
                        break
        
        if not ids_riba:
            messagebox.showwarning('Attenzione', 'Seleziona almeno una Ri.Ba. da pagare (usando le checkbox)')
            return
        
        if not messagebox.askyesno('Conferma', f'Confermi il pagamento di {len(ids_riba)} Ri.Ba.?\n(La data di pagamento sarà quella di scadenza di ciascuna fattura)'):
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION")
            
            try:
                cur.execute("SELECT data_pagamento FROM riba LIMIT 1")
                colonna_data_pagamento_esiste = True
            except:
                colonna_data_pagamento_esiste = False
                try:
                    cur.execute("ALTER TABLE riba ADD COLUMN data_pagamento TEXT")
                    colonna_data_pagamento_esiste = True
                except:
                    pass
            
            riba_data = []
            soggetto_id = None
            for riba_id in ids_riba:
                cur.execute("""
                    SELECT r.scadenza_id, sc.importo_scadenza AS importo, sc.data_scadenza, d.soggetto_id
                    FROM riba r
                    JOIN scadenze sc ON r.scadenza_id = sc.id
                    JOIN documenti d ON sc.id_documento = d.id
                    WHERE r.id = ?
                """, (riba_id,))
                row = cur.fetchone()
                if row and row[0]:
                    scadenza_id = row[0]
                    importo = float(row[1]) if row[1] else 0.0
                    data_scadenza = row[2] if row[2] else None
                    if not data_scadenza:
                        continue
                    # Recupera soggetto_id (dovrebbe essere lo stesso per tutte le RiBa)
                    if not soggetto_id:
                        soggetto_id = row[3] if len(row) > 3 else None
                    riba_data.append({
                        'riba_id': riba_id,
                        'scadenza_id': scadenza_id,
                        'importo': importo,
                        'data_scadenza': data_scadenza,
                        'documento_id': None  # Sarà popolato dopo
                    })
            
            # Recupera gli ID dei documenti per ogni RiBa
            for riba in riba_data:
                cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (riba['scadenza_id'],))
                doc_row = cur.fetchone()
                if doc_row:
                    riba['documento_id'] = doc_row[0]
            
            if not riba_data:
                messagebox.showerror('Errore', 'Nessuna Ri.Ba. valida con scadenza associata')
                conn.rollback()
                conn.close()
                return
            
            # Le note di credito vengono ora gestite all'emissione della distinta, non al pagamento
            # Quindi qui creiamo solo i pagamenti normali per le RiBa
            
            # Verifica se esiste tipo_movimento
            try:
                cur.execute("SELECT tipo_movimento FROM pagamenti LIMIT 1")
                has_tipo_movimento = True
            except:
                has_tipo_movimento = False
            
            # 🔹 STEP: Crea pagamenti per le RiBa
            # Nota: le note di credito sono già state applicate alla distinta,
            # quindi qui calcoliamo l'importo netto e creiamo solo i pagamenti
            for riba in riba_data:
                # Calcola importo netto (dopo detrazione note di credito già applicate)
                cur.execute("""
                    SELECT 
                        sc.importo_scadenza 
                        - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0)
                        - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo
                    FROM scadenze sc
                    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = sc.id_documento
                    WHERE sc.id = ?
                    GROUP BY sc.id
                """, (riba['scadenza_id'],))
                residuo_row = cur.fetchone()
                importo_netto = float(residuo_row[0]) if residuo_row and residuo_row[0] else riba['importo']
                
                # Crea pagamento solo se c'è un importo da pagare
                if importo_netto > 0.01:
                    if has_tipo_movimento:
                        cur.execute("""
                            INSERT INTO pagamenti 
                            (data_pagamento, importo_pagamento, totale, modalita_pagamento, tipo_movimento)
                            VALUES (?, ?, ?, ?, ?)
                        """, (riba['data_scadenza'], importo_netto, importo_netto, 'RIBA', 'INCASSO'))
                    else:
                        cur.execute("""
                            INSERT INTO pagamenti 
                            (data_pagamento, importo_pagamento, totale, modalita_pagamento)
                            VALUES (?, ?, ?, ?)
                        """, (riba['data_scadenza'], importo_netto, importo_netto, 'RIBA'))
                    pagamento_id = cur.lastrowid
                    
                    # Associazione pagamento-documento (usando associazioni_pagamenti)
                    cur.execute("""
                        INSERT INTO associazioni_pagamenti 
                        (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                        VALUES (?, ?, ?, 'PAGAMENTO', ?)
                    """, (pagamento_id, riba['documento_id'], importo_netto, riba['data_scadenza']))
                    
                    # Verifica se la scadenza è ora completamente pagata
                    cur.execute("""
                        SELECT 
                            sc.importo_scadenza 
                            - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0)
                            - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo
                        FROM scadenze sc
                        LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = sc.id_documento
                        WHERE sc.id = ?
                        GROUP BY sc.id
                    """, (riba['scadenza_id'],))
                    residuo_finale_row = cur.fetchone()
                    
                    if residuo_finale_row and residuo_finale_row[0] <= 0.01:
                        # Se esiste una RIBA collegata, aggiorna lo stato in 'Pagata'
                        cur.execute("""
                            UPDATE riba
                            SET stato = 'Pagata'
                            WHERE scadenza_id = ?
                        """, (riba['scadenza_id'],))
            
            # Aggiorna data_pagamento se la colonna esiste
            if colonna_data_pagamento_esiste:
                for riba in riba_data:
                    cur.execute("UPDATE riba SET data_pagamento = ? WHERE id = ?", 
                               (riba['data_scadenza'], riba['riba_id']))
            
            # Calcola totale pagato prima di chiudere la connessione
            totale_pagato = 0.0
            for riba in riba_data:
                cur.execute("""
                    SELECT 
                        IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0)
                    FROM associazioni_pagamenti ap
                    WHERE ap.id_documento = ?
                """, (riba['documento_id'],))
                pagato_row = cur.fetchone()
                if pagato_row:
                    totale_pagato += float(pagato_row[0]) if pagato_row[0] else 0.0
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo('OK', f'Pagamento registrato per {len(riba_data)} Ri.Ba.\nImporto pagato: € {totale_pagato:,.2f}')
            self.load_data()
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            messagebox.showerror('Errore DB', f'Errore durante il salvataggio: {str(e)}')
    
    def elimina_selezionati(self):
        """Elimina RiBa selezionate"""
        ids = []
        for item in self.tree.get_children():
            if item in self.selezioni and self.selezioni[item]:
                tags = self.tree.item(item, 'tags')
                for t in tags:
                    if t.startswith('id_'):
                        riba_id = int(t[3:])
                        ids.append(riba_id)
                        break
        
        if not ids:
            messagebox.showwarning('Attenzione', 'Seleziona almeno una Ri.Ba. da eliminare (usando le checkbox)')
            return
        
        if not messagebox.askyesno('Conferma', f'Sei sicuro di eliminare {len(ids)} Ri.Ba.?'): 
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.executemany('DELETE FROM riba WHERE id = ?', [(i,) for i in ids])
            conn.commit()
            conn.close()
            messagebox.showinfo('OK', 'Eliminati')
            self.load_data()
        except Exception as e:
            messagebox.showerror('Errore DB', str(e))
    
    def on_tree_click(self, event):
        """Gestisce click sulla tabella RiBa"""
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item: return
        
        # Gestisce click sulla checkbox (colonna #1) o su qualsiasi altra colonna
        if col == '#1' or col:
            if item in self.selezioni:
                self.selezioni[item] = not self.selezioni[item]
            else:
                self.selezioni[item] = True
            
            values = list(self.tree.item(item, 'values'))
            if self.selezioni[item]:
                values[0] = '  ✓'
                tags = list(self.tree.item(item, 'tags'))
                if 'selezionata' not in tags:
                    tags.append('selezionata')
                self.tree.item(item, tags=tags)
            else:
                values[0] = '  ☐'
                tags = list(self.tree.item(item, 'tags'))
                if 'selezionata' in tags:
                    tags.remove('selezionata')
                self.tree.item(item, tags=tags)
            self.tree.item(item, values=values)
    
    def on_tree_double_click(self, event):
        """Gestisce doppio click sulla tabella RiBa"""
        item = self.tree.identify_row(event.y)
        if not item: return
        tags = self.tree.item(item, 'tags')
        distinta_id = None; riba_id = None
        for t in tags:
            if t.startswith('dist_'):
                val = t[5:]
                if val: distinta_id = val
            if t.startswith('id_'):
                riba_id = int(t[3:])
        if distinta_id:
            outdir = Path('distinte_pdf')
            pdf_trovato = None
            if outdir.exists():
                for pdf_file in outdir.glob(f"Distinta_{distinta_id}_*.pdf"):
                    pdf_trovato = pdf_file
                    break
            
            if pdf_trovato and pdf_trovato.exists():
                import subprocess
                import platform
                try:
                    if platform.system() == 'Windows':
                        os.startfile(str(pdf_trovato))
                    else:
                        subprocess.Popen(['xdg-open', str(pdf_trovato)])
                except Exception as e:
                    messagebox.showerror('Errore', f'Impossibile aprire il PDF: {str(e)}')
            else:
                self.esporta_pdf_by_distinta(distinta_id, apri_per_stampa=True)
        else:
            messagebox.showinfo('Dettaglio', f'Ri.Ba. id={riba_id} (nessuna distinta)')
    
    def esporta_pdf_by_distinta(self, distinta_id, apri_per_stampa=False):
        """Esporta PDF per una distinta"""
        try:
            conn = sqlite3.connect(self.db_path); cur = conn.cursor()
            cur.execute("SELECT id, data_creazione, numero_distinta, data_distinta FROM distinte_riba WHERE id = ?", (distinta_id,))
            dist = cur.fetchone()
            if not dist:
                messagebox.showerror('Errore', 'Distinta non trovata'); conn.close(); return
            cur.execute("""
                SELECT r.id, s.ragione_sociale, d.numero_documento, sc.data_scadenza, sc.importo_scadenza AS importo, r.stato
                FROM riba r
                LEFT JOIN scadenze sc ON r.scadenza_id = sc.id
                LEFT JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN soggetti s ON d.soggetto_id = s.id
                WHERE r.distinta_id = ?
                ORDER BY sc.data_scadenza
            """, (distinta_id,))
            rows = cur.fetchall(); conn.close()

            if not rows:
                messagebox.showinfo('Info', 'Nessuna Ri.Ba. nella distinta'); return

            outdir = Path('distinte_pdf')
            outdir.mkdir(exist_ok=True)
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = outdir / f"Distinta_{distinta_id}_{date_str}.pdf"

            c = canvas.Canvas(str(filename), pagesize=A4)
            width, height = A4
            x_margin = 40
            y = height - 60

            numero_display = dist[2] if dist[2] else str(dist[0])
            c.setFont('Helvetica-Bold', 14)
            c.drawString(x_margin, y, f"Distinta Ri.Ba. n. {numero_display}")
            c.setFont('Helvetica', 10)
            if dist[3]:
                c.drawString(x_margin, y-18, f"Data distinta: {dist[3]}")
            c.drawString(x_margin, y-36, f"Data creazione: {dist[1]}")
            c.drawString(x_margin, y-54, f"Generata il: {date_str}")

            y -= 80
            c.setFont('Helvetica-Bold', 10)
            c.drawString(x_margin, y, "Cliente")
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
                scad = r[3] or ''
                imp = float(r[4]) if r[4] else 0.0
                stato = r[5] or ''
                c.drawString(x_margin, y, cliente[:40])
                c.drawString(x_margin+250, y, docu)
                c.drawString(x_margin+360, y, scad)
                c.drawRightString(x_margin+520, y, f"€ {imp:,.2f}")
                y -= 14
                total += imp

            if y < 100:
                c.showPage(); y = height - 60
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
                messagebox.showinfo('PDF pronto per stampa', f'File aperto: {filename}')
            else:
                messagebox.showinfo('PDF creato', f'File generato: {filename}')
        except Exception as e:
            messagebox.showerror('Errore PDF', str(e))

