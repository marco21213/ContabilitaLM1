import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date
from PIL import Image, ImageTk
from tkcalendar import DateEntry


class NuovoPagamentoWindow(tk.Toplevel):
    def __init__(self, parent, db_path, on_save_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.on_save_callback = on_save_callback
        self.title("Nuovo Pagamento")
        self.geometry("1200x700")
        self.transient(parent)
        self.grab_set()

        self.scadenze = []  # lista di dict
        self.note_credito = []  # lista di dict per note di credito disponibili
        self.note_credito_selezionate = []  # lista di note di credito selezionate

        self.create_widgets()
        self.load_soggetti()
        self.ensure_note_credito_table()

    def create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Soggetto con ricerca avanzata
        tk.Label(top_frame, text="Soggetto:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        # Frame per Entry e pulsante ricerca
        soggetto_frame = tk.Frame(top_frame)
        soggetto_frame.grid(row=0, column=1, sticky="w", padx=(8, 10))
        
        self.soggetto_entry = tk.Entry(soggetto_frame, font=("Arial", 10), width=47, state="readonly", bg="white")
        self.soggetto_entry.pack(side="left")
        
        self.soggetto_selected_id = None  # ID del soggetto selezionato
        
        btn_cerca_soggetto = tk.Button(soggetto_frame, text="🔍", 
                                       command=self.apri_ricerca_soggetto,
                                       bg="#2196F3", fg="white", font=("Arial", 9, "bold"),
                                       width=3, cursor="hand2", relief="flat")
        btn_cerca_soggetto.pack(side="left", padx=(5, 0))

        # Bottoni Salva in alto a destra con icone
        buttons_frame = tk.Frame(top_frame)
        buttons_frame.grid(row=0, column=4, padx=(20, 0), sticky="e")
        
        # Carica icone
        try:
            img_salva = Image.open("assets/icon/salva.png")
            img_salva = img_salva.resize((32, 32), Image.Resampling.LANCZOS)
            self.icon_salva = ImageTk.PhotoImage(img_salva)
            
            img_salva_nuovo = Image.open("assets/icon/salvaenuovo.png")
            img_salva_nuovo = img_salva_nuovo.resize((32, 32), Image.Resampling.LANCZOS)
            self.icon_salva_nuovo = ImageTk.PhotoImage(img_salva_nuovo)
            
            self.save_btn = tk.Button(buttons_frame, image=self.icon_salva, 
                                     command=self.salva_pagamento, cursor="hand2",
                                     bg="#4CAF50", relief="flat", borderwidth=0, width=40, height=40)
            self.save_btn.image = self.icon_salva  # Mantieni riferimento per evitare garbage collection
            self.save_btn.pack(side="left", padx=(0, 5))
            
            self.save_and_new_btn = tk.Button(buttons_frame, image=self.icon_salva_nuovo,
                                              command=self.salva_e_nuovo, cursor="hand2",
                                              bg="#2196F3", relief="flat", borderwidth=0, width=40, height=40)
            self.save_and_new_btn.image = self.icon_salva_nuovo  # Mantieni riferimento per evitare garbage collection
            self.save_and_new_btn.pack(side="left")
        except Exception as e:
            # Fallback se le icone non sono disponibili
            self.save_btn = tk.Button(buttons_frame, text="Salva", bg="#4CAF50", fg="white",
                                     command=self.salva_pagamento, cursor="hand2")
            self.save_btn.pack(side="left", padx=(0, 5))
            
            self.save_and_new_btn = tk.Button(buttons_frame, text="Salva e Nuovo", bg="#2196F3", fg="white",
                                             command=self.salva_e_nuovo, cursor="hand2")
            self.save_and_new_btn.pack(side="left")

        # Modalità con ricerca avanzata
        tk.Label(top_frame, text="Modalità:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        
        # Frame per Entry e pulsante ricerca
        modalita_frame = tk.Frame(top_frame)
        modalita_frame.grid(row=1, column=1, sticky="w", padx=(8, 10), pady=(8, 0))
        
        self.modalita_entry = tk.Entry(modalita_frame, font=("Arial", 10), width=27, state="readonly", bg="white")
        self.modalita_entry.pack(side="left")
        self.modalita_entry.insert(0, "CONTANTI")  # Valore predefinito
        
        self.modalita_selected = "CONTANTI"  # Valore selezionato
        
        btn_cerca_modalita = tk.Button(modalita_frame, text="🔍", 
                                       command=self.apri_ricerca_modalita,
                                       bg="#2196F3", fg="white", font=("Arial", 9, "bold"),
                                       width=3, cursor="hand2", relief="flat")
        btn_cerca_modalita.pack(side="left", padx=(5, 0))

        # Data pagamento (spostata sotto soggetto e modalità) con DateEntry
        tk.Label(top_frame, text="Data pagamento:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        data_frame = tk.Frame(top_frame)
        data_frame.grid(row=2, column=1, sticky="w", padx=(8, 10), pady=(8, 0))
        
        self.data_entry = DateEntry(data_frame, width=15, date_pattern="dd/mm/yyyy", 
                                    background='#4CAF50', foreground='white', 
                                    borderwidth=2, locale='it_IT')
        # DateEntry non può essere vuoto, ma l'utente può modificarlo
        # Non impostiamo una data di default, lasciamo che l'utente la selezioni
        self.data_entry.pack(side="left")

        # Totali
        tk.Label(top_frame, text="Totale Selezionati:", font=("Arial", 12, "bold")).grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.totale_selezionati_var = tk.StringVar(value="0.00")
        totale_selez_entry = tk.Entry(top_frame, textvariable=self.totale_selezionati_var, state="readonly", 
                                     width=15, font=("Arial", 10), bg="white", justify="right")
        totale_selez_entry.grid(row=1, column=3, sticky="w", padx=(8, 10), pady=(8, 0))

        # Spese Accessorie
        tk.Label(top_frame, text="Spese Accessorie:", font=("Arial", 12, "bold")).grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.spese_accessorie_var = tk.StringVar(value="0.00")
        spese_entry = tk.Entry(top_frame, textvariable=self.spese_accessorie_var, width=15, 
                              font=("Arial", 10), bg="white", justify="right")
        spese_entry.grid(row=2, column=3, sticky="w", padx=(8, 10), pady=(8, 0))

        # Totale Pagamento (editabile dall'utente)
        tk.Label(top_frame, text="Totale Pagamento:", font=("Arial", 12, "bold")).grid(row=3, column=2, sticky="w", pady=(8, 0))
        self.totale_pagamento_var = tk.StringVar(value="0.00")
        totale_pag_entry = tk.Entry(top_frame, textvariable=self.totale_pagamento_var, width=15,
                                   font=("Arial", 10), bg="white", justify="right")
        totale_pag_entry.grid(row=3, column=3, sticky="w", padx=(8, 10), pady=(8, 0))

        # Frame principale con paned window per dividere scadenze e note di credito
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        main_paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Frame sinistro: Scadenze
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=700)

        # Rimosso il messaggio sotto la tabella per una grafica più pulita
        
        # Tabella scadenze
        columns = ("CHECK", "DOCUMENTO", "DATA_DOC", "DATA_SCAD", "IMP_SCAD", "PAGATO", "RESIDUO")
        table_frame = tk.Frame(left_frame)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="none")
        self.tree.heading("CHECK", text="")
        self.tree.column("CHECK", width=40, anchor="center")
        self.tree.heading("DOCUMENTO", text="DOCUMENTO")
        self.tree.column("DOCUMENTO", width=220)
        for col in ("DATA_DOC", "DATA_SCAD", "IMP_SCAD", "PAGATO", "RESIDUO"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self.on_tree_click)

        # Note di credito ora sono mostrate nella lista principale insieme agli altri documenti
        # La sezione separata è stata rimossa per semplificare l'interfaccia

    def load_soggetti(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, ragione_sociale FROM soggetti ORDER BY ragione_sociale")
            rows = cur.fetchall()
            conn.close()

            self.soggetti = rows
            # Non serve più popolare la combobox, ora usiamo la ricerca avanzata

            self.payment_methods = [
                "CONTANTI", "ASSEGNO BANCARIO", "ASSEGNO CIRCOLARE",
                "BONIFICO", "CARTA DI CREDITO", "RID", "RIBA",
                "GIROCONTO", "SEPA", "PAGO PA"
            ]
            # Non serve più popolare la combobox, ora usiamo la ricerca avanzata

        except Exception as e:
            messagebox.showerror("Errore DB", str(e))

    def apri_ricerca_soggetto(self):
        """Apre la finestra di ricerca avanzata per il soggetto"""
        win = tk.Toplevel(self)
        win.title("Cerca Soggetto")
        win.geometry("400x350")
        win.configure(bg="white")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        frame = tk.Frame(win, bg="white", padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text="Cerca Soggetto:", bg="white",
                 fg="#000", font=("Arial", 10, "bold")).pack(pady=(0, 10))
        
        # Frame per ricerca
        search_frame = tk.Frame(frame, bg="white")
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Cerca:", bg="white", 
                font=("Arial", 9)).pack(side="left", padx=(0, 5))
        
        search_entry = tk.Entry(search_frame, font=("Arial", 10), width=20)
        search_entry.pack(side="left", fill="x", expand=True)
        
        # Listbox con scrollbar
        listbox_frame = tk.Frame(frame, bg="white")
        listbox_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, font=("Arial", 10), 
                            yscrollcommand=scrollbar.set, height=8)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Popola la listbox con tutti i soggetti
        vals = [r[1] for r in self.soggetti]  # ragione_sociale
        for val in vals:
            listbox.insert(tk.END, val)
        
        def filter_listbox(*args):
            """Filtra la listbox in base al testo digitato"""
            search_text = search_entry.get().lower()
            listbox.delete(0, tk.END)
            
            if not search_text:
                filtered = vals
            else:
                filtered = [v for v in vals if search_text in v.lower()]
                if not filtered:
                    listbox.insert(tk.END, "(Nessun risultato)")
                    listbox.itemconfig(0, {'fg': '#999'})
                    return
            
            for val in filtered:
                listbox.insert(tk.END, val)
            
            if len(filtered) == 1 and filtered[0]:
                listbox.selection_set(0)
                listbox.see(0)
            elif len(filtered) > 1:
                listbox.selection_set(0)
                listbox.see(0)
        
        def on_listbox_select(event):
            """Gestisce la selezione dalla listbox"""
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                if selected_text != "(Nessun risultato)":
                    search_entry.delete(0, tk.END)
                    search_entry.insert(0, selected_text)
        
        def on_listbox_double_click(event):
            """Applica la selezione con doppio click"""
            on_listbox_select(event)
            apply_selection()
        
        def on_search_key(event):
            """Gestisce i tasti nella ricerca"""
            if event.keysym == 'Down':
                listbox.focus_set()
                if listbox.size() > 0:
                    listbox.selection_set(0)
                    listbox.see(0)
                return "break"
            elif event.keysym == 'Return':
                selection = listbox.curselection()
                if selection:
                    apply_selection()
                return "break"
        
        def on_listbox_key(event):
            """Gestisce i tasti nella listbox"""
            if event.keysym == 'Return':
                apply_selection()
                return "break"
            elif event.keysym == 'Escape':
                win.destroy()
                return "break"
            elif event.keysym == 'Up' and listbox.curselection() and listbox.curselection()[0] == 0:
                search_entry.focus_set()
                return "break"
        
        def apply_selection():
            """Applica la selezione del soggetto"""
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                if selected_text == "(Nessun risultato)":
                    return
            else:
                selected_text = search_entry.get().strip()
                if selected_text not in vals:
                    val_lower = selected_text.lower()
                    for v in vals:
                        if v.lower().startswith(val_lower):
                            selected_text = v
                            break
                    else:
                        for v in vals:
                            if val_lower in v.lower():
                                selected_text = v
                                break
                        else:
                            return
            
            # Trova l'ID del soggetto selezionato
            for soggetto_id, ragione_sociale in self.soggetti:
                if ragione_sociale == selected_text:
                    self.soggetto_selected_id = soggetto_id
                    self.soggetto_entry.config(state="normal")
                    self.soggetto_entry.delete(0, tk.END)
                    self.soggetto_entry.insert(0, selected_text)
                    self.soggetto_entry.config(state="readonly")
                    self.load_scadenze_aperti(soggetto_id)
                    win.destroy()
                    return
        
        search_entry.bind('<KeyRelease>', filter_listbox)
        search_entry.bind('<KeyPress>', on_search_key)
        listbox.bind('<<ListboxSelect>>', on_listbox_select)
        listbox.bind('<Double-Button-1>', on_listbox_double_click)
        listbox.bind('<KeyPress>', on_listbox_key)
        win.bind('<Escape>', lambda e: win.destroy())
        search_entry.bind('<Escape>', lambda e: win.destroy())
        
        # Suggerimento
        tk.Label(frame, 
                text="💡 Digita per cercare, ↓↑ per navigare, Invio per selezionare, Esc per chiudere", 
                bg="white", fg="#666", font=("Arial", 8, "italic")).pack(pady=(0, 5))
        
        # Pulsanti
        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(pady=(10, 0))
        
        tk.Button(btn_frame, text="Seleziona", bg="#4CAF50", fg="white",
                 width=10, command=apply_selection, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Chiudi", bg="#f44336", fg="white",
                 width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        # Focus sul campo ricerca
        def set_focus():
            search_entry.focus_set()
        win.after(100, set_focus)
    
    def apri_ricerca_modalita(self):
        """Apre la finestra di ricerca avanzata per la modalità di pagamento"""
        win = tk.Toplevel(self)
        win.title("Cerca Modalità Pagamento")
        win.geometry("400x350")
        win.configure(bg="white")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        frame = tk.Frame(win, bg="white", padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text="Cerca Modalità:", bg="white",
                 fg="#000", font=("Arial", 10, "bold")).pack(pady=(0, 10))
        
        # Frame per ricerca
        search_frame = tk.Frame(frame, bg="white")
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Cerca:", bg="white", 
                font=("Arial", 9)).pack(side="left", padx=(0, 5))
        
        search_entry = tk.Entry(search_frame, font=("Arial", 10), width=20)
        search_entry.pack(side="left", fill="x", expand=True)
        
        # Listbox con scrollbar
        listbox_frame = tk.Frame(frame, bg="white")
        listbox_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, font=("Arial", 10), 
                            yscrollcommand=scrollbar.set, height=8)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Popola la listbox con tutte le modalità
        vals = self.payment_methods
        for val in vals:
            listbox.insert(tk.END, val)
        
        def filter_listbox(*args):
            """Filtra la listbox in base al testo digitato"""
            search_text = search_entry.get().lower()
            listbox.delete(0, tk.END)
            
            if not search_text:
                filtered = vals
            else:
                filtered = [v for v in vals if search_text in v.lower()]
                if not filtered:
                    listbox.insert(tk.END, "(Nessun risultato)")
                    listbox.itemconfig(0, {'fg': '#999'})
                    return
            
            for val in filtered:
                listbox.insert(tk.END, val)
            
            if len(filtered) == 1 and filtered[0]:
                listbox.selection_set(0)
                listbox.see(0)
            elif len(filtered) > 1:
                listbox.selection_set(0)
                listbox.see(0)
        
        def on_listbox_select(event):
            """Gestisce la selezione dalla listbox"""
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                if selected_text != "(Nessun risultato)":
                    search_entry.delete(0, tk.END)
                    search_entry.insert(0, selected_text)
        
        def on_listbox_double_click(event):
            """Applica la selezione con doppio click"""
            on_listbox_select(event)
            apply_selection()
        
        def on_search_key(event):
            """Gestisce i tasti nella ricerca"""
            if event.keysym == 'Down':
                listbox.focus_set()
                if listbox.size() > 0:
                    listbox.selection_set(0)
                    listbox.see(0)
                return "break"
            elif event.keysym == 'Return':
                selection = listbox.curselection()
                if selection:
                    apply_selection()
                return "break"
        
        def on_listbox_key(event):
            """Gestisce i tasti nella listbox"""
            if event.keysym == 'Return':
                apply_selection()
                return "break"
            elif event.keysym == 'Escape':
                win.destroy()
                return "break"
            elif event.keysym == 'Up' and listbox.curselection() and listbox.curselection()[0] == 0:
                search_entry.focus_set()
                return "break"
        
        def apply_selection():
            """Applica la selezione della modalità"""
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                if selected_text == "(Nessun risultato)":
                    return
            else:
                selected_text = search_entry.get().strip()
                if selected_text not in vals:
                    val_lower = selected_text.lower()
                    for v in vals:
                        if v.lower().startswith(val_lower):
                            selected_text = v
                            break
                    else:
                        for v in vals:
                            if val_lower in v.lower():
                                selected_text = v
                                break
                        else:
                            return
            
            # Aggiorna il campo modalità
            self.modalita_selected = selected_text
            self.modalita_entry.config(state="normal")
            self.modalita_entry.delete(0, tk.END)
            self.modalita_entry.insert(0, selected_text)
            self.modalita_entry.config(state="readonly")
            win.destroy()
        
        search_entry.bind('<KeyRelease>', filter_listbox)
        search_entry.bind('<KeyPress>', on_search_key)
        listbox.bind('<<ListboxSelect>>', on_listbox_select)
        listbox.bind('<Double-Button-1>', on_listbox_double_click)
        listbox.bind('<KeyPress>', on_listbox_key)
        win.bind('<Escape>', lambda e: win.destroy())
        search_entry.bind('<Escape>', lambda e: win.destroy())
        
        # Suggerimento
        tk.Label(frame, 
                text="💡 Digita per cercare, ↓↑ per navigare, Invio per selezionare, Esc per chiudere", 
                bg="white", fg="#666", font=("Arial", 8, "italic")).pack(pady=(0, 5))
        
        # Pulsanti
        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(pady=(10, 0))
        
        tk.Button(btn_frame, text="Seleziona", bg="#4CAF50", fg="white",
                 width=10, command=apply_selection, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Chiudi", bg="#f44336", fg="white",
                 width=10, command=win.destroy, cursor="hand2").pack(side="left")
        
        # Focus sul campo ricerca
        def set_focus():
            search_entry.focus_set()
        win.after(100, set_focus)
    
    def on_soggetto_selected(self, event=None):
        """Gestisce la selezione del soggetto (mantenuto per compatibilità)"""
        if self.soggetto_selected_id:
            self.load_scadenze_aperti(self.soggetto_selected_id)

    def load_scadenze_aperti(self, soggetto_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica se esiste la colonna segno
            cur.execute("PRAGMA table_info(documenti)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_segno = 'segno' in colonne_nomi
            
            # Query per documenti normali (fatture, ecc.) - escludi note di credito
            query_documenti = """
                SELECT
                    sc.id AS scadenza_id,
                    d.tipo_documento || ' ' || d.numero_documento AS documento,
                    d.data_documento,
                    sc.data_scadenza,
                    sc.importo_scadenza,
                    IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0) AS pagato,
                    IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS nc_applicata,
                    sc.importo_scadenza 
                    - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0)
                    - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo,
                    0 AS is_nota_credito,
                    d.id AS documento_id
                FROM scadenze sc
                JOIN documenti d ON sc.id_documento = d.id
                LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                WHERE d.soggetto_id = ?
                  AND NOT (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                           OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.data_scadenza, sc.importo_scadenza, d.id
                HAVING residuo > 0.01
            """
            
            # Query per note di credito disponibili
            if has_segno:
                query_nc = """
                    SELECT
                        sc.id AS scadenza_id,
                        'NC: ' || d.tipo_documento || ' ' || d.numero_documento AS documento,
                        d.data_documento,
                        sc.data_scadenza,
                        sc.importo_scadenza,
                        0 AS pagato,
                        IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS nc_applicata,
                        ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo,
                        1 AS is_nota_credito,
                        d.id AS documento_id
                    FROM scadenze sc
                    JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                    WHERE d.soggetto_id = ?
                      AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                           OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                      AND d.segno = -1
                    GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.data_scadenza, sc.importo_scadenza, d.id
                    HAVING residuo > 0.01
                """
            else:
                query_nc = """
                    SELECT
                        sc.id AS scadenza_id,
                        'NC: ' || d.tipo_documento || ' ' || d.numero_documento AS documento,
                        d.data_documento,
                        sc.data_scadenza,
                        sc.importo_scadenza,
                        0 AS pagato,
                        IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS nc_applicata,
                        ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo,
                        1 AS is_nota_credito,
                        d.id AS documento_id
                    FROM scadenze sc
                    JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                    WHERE d.soggetto_id = ?
                      AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                           OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                    GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.data_scadenza, sc.importo_scadenza, d.id
                    HAVING residuo > 0.01
                """
            
            # Esegui entrambe le query e unisci i risultati
            cur.execute(query_documenti, (soggetto_id,))
            rows_documenti = cur.fetchall()
            
            cur.execute(query_nc, (soggetto_id,))
            rows_nc = cur.fetchall()
            
            conn.close()

            self.scadenze = []
            # Aggiungi documenti normali
            for r in rows_documenti:
                sc = {
                    'scadenza_id': r[0],
                    'documento': r[1],
                    'data_documento': r[2],
                    'data_scadenza': r[3],
                    'importo_scadenza': float(r[4]) if r[4] else 0.0,
                    'pagato': float(r[5]) if r[5] else 0.0,
                    'nc_applicata': float(r[6]) if len(r) > 6 and r[6] else 0.0,
                    'residuo': float(r[7]) if len(r) > 7 and r[7] else 0.0,
                    'is_nota_credito': False,
                    'documento_id': r[9] if len(r) > 9 else None,
                    'selected': False
                }
                self.scadenze.append(sc)
            
            # Aggiungi note di credito
            for r in rows_nc:
                sc = {
                    'scadenza_id': r[0],
                    'documento': r[1],  # Già con prefisso "NC: "
                    'data_documento': r[2],
                    'data_scadenza': r[3],
                    'importo_scadenza': float(r[4]) if r[4] else 0.0,
                    'pagato': 0.0,  # Le NC non vengono pagate
                    'nc_applicata': float(r[6]) if len(r) > 6 and r[6] else 0.0,
                    'residuo': float(r[7]) if len(r) > 7 and r[7] else 0.0,
                    'is_nota_credito': True,  # Marca come nota di credito
                    'documento_id': r[9] if len(r) > 9 else None,
                    'selected': False
                }
                self.scadenze.append(sc)
            
            # Ordina per data scadenza
            self.scadenze.sort(key=lambda x: x['data_scadenza'])
            self.refresh_treeview()

        except Exception as e:
            messagebox.showerror("Errore DB", str(e))

    def ensure_note_credito_table(self):
        """Crea la tabella per tracciare l'applicazione delle note di credito se non esiste"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS note_credito_applicate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scadenza_id INTEGER NOT NULL,
                    nota_credito_scadenza_id INTEGER NOT NULL,
                    importo_applicato REAL NOT NULL,
                    data_applicazione TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scadenza_id) REFERENCES scadenze(id),
                    FOREIGN KEY (nota_credito_scadenza_id) REFERENCES scadenze(id)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Errore creazione tabella note_credito_applicate: {e}")

    def load_note_credito_disponibili(self, soggetto_id):
        """Carica le note di credito disponibili per il soggetto"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Verifica se esiste la colonna segno
            cur.execute("PRAGMA table_info(documenti)")
            colonne_info = cur.fetchall()
            colonne_nomi = [col[1] for col in colonne_info]
            has_segno = 'segno' in colonne_nomi
            
            # Query per trovare note di credito clienti disponibili
            # Per note di credito cliente: segno = -1, importo_scadenza negativo
            # Residuo = ABS(importo_scadenza) - applicato (sempre positivo)
            # Le note di credito NON vengono pagate, solo applicate ad altre scadenze
            # Usa associazioni_pagamenti per calcolare quanto è stato applicato
            if has_segno:
                query = """
                    SELECT
                        sc.id AS scadenza_id,
                        d.tipo_documento || ' ' || d.numero_documento AS documento,
                        d.data_documento,
                        sc.importo_scadenza,
                        0 AS pagato,
                        IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS applicato,
                        ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo
                    FROM scadenze sc
                    JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                    WHERE d.soggetto_id = ?
                      AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                           OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                      AND d.segno = -1
                    GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.importo_scadenza
                    HAVING residuo > 0.01
                    ORDER BY d.data_documento ASC;
                """
            else:
                query = """
                    SELECT
                        sc.id AS scadenza_id,
                        d.tipo_documento || ' ' || d.numero_documento AS documento,
                        d.data_documento,
                        sc.importo_scadenza,
                        0 AS pagato,
                        IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS applicato,
                        ABS(sc.importo_scadenza) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo
                    FROM scadenze sc
                    JOIN documenti d ON sc.id_documento = d.id
                    LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = d.id
                    WHERE d.soggetto_id = ?
                      AND (UPPER(d.tipo_documento) LIKE '%NC_CLIENTE%' 
                           OR UPPER(d.tipo_documento) LIKE '%NOTA_CREDITO_CLIENTE%')
                    GROUP BY sc.id, d.tipo_documento, d.numero_documento, d.data_documento, sc.importo_scadenza
                    HAVING residuo > 0.01
                    ORDER BY d.data_documento ASC;
                """
            
            cur.execute(query, (soggetto_id,))
            rows = cur.fetchall()
            conn.close()

            self.note_credito = []
            for r in rows:
                # Per le note di credito, l'importo_scadenza è negativo, ma il residuo è sempre positivo
                importo_scadenza = float(r[3]) if r[3] else 0.0
                residuo = float(r[6]) if r[6] else 0.0
                nc = {
                    'scadenza_id': r[0],
                    'documento': r[1],
                    'data_documento': r[2],
                    'importo': abs(importo_scadenza),  # Mostra sempre positivo nella UI
                    'pagato': 0.0,  # Le note di credito non vengono pagate
                    'applicato': float(r[5]) if r[5] else 0.0,
                    'residuo': residuo,  # Già calcolato come positivo
                    'selected': False
                }
                self.note_credito.append(nc)
            self.refresh_nc_treeview()

        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore caricamento note di credito: {str(e)}")

    def refresh_nc_treeview(self):
        """Aggiorna la visualizzazione delle note di credito"""
        for it in self.nc_tree.get_children():
            self.nc_tree.delete(it)

        for nc in self.note_credito:
            checked = "☑" if nc['selected'] else "☐"
            values = (
                checked,
                nc['documento'],
                nc['data_documento'],
                f"{nc['importo']:.2f}",
                f"{nc['residuo']:.2f}"
            )
            self.nc_tree.insert('', tk.END, values=values, iid=f"nc_{nc['scadenza_id']}")
        
        self.update_nc_totale()

    def on_nc_tree_click(self, event):
        """Gestisce il click sulla tabella note di credito"""
        region = self.nc_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.nc_tree.identify_column(event.x)
        if col != "#1":  # solo colonna checkbox
            return
        row_id = self.nc_tree.identify_row(event.y)
        if not row_id:
            return

        for nc in self.note_credito:
            if f"nc_{nc['scadenza_id']}" == row_id:
                nc['selected'] = not nc['selected']
                break
        self.refresh_nc_treeview()
        # Ricalcola i residui delle scadenze considerando le note di credito selezionate
        self.update_residui_con_nc()

    def update_nc_totale(self):
        """Aggiorna il totale delle note di credito selezionate"""
        totale = sum(nc['residuo'] for nc in self.note_credito if nc['selected'])
        self.nc_totale_var.set(f"{totale:.2f}")

    def update_residui_con_nc(self):
        """Ricalcola i residui delle scadenze considerando le note di credito selezionate"""
        # Aggiorna il totale selezionati (che considera già le NC)
        self.update_totale_selezionati()

    def refresh_treeview(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        for sc in self.scadenze:
            checked = "☑" if sc['selected'] else "☐"
            values = (
                checked,
                sc['documento'],
                sc['data_documento'],
                sc['data_scadenza'],
                f"{sc['importo_scadenza']:.2f}",
                f"{sc['pagato']:.2f}",
                f"{sc['residuo']:.2f}"
            )
            # Gestisci i tag: nota_credito e selected
            tags = []
            if sc.get('is_nota_credito', False):
                tags.append('nota_credito')
            if sc.get('selected', False):
                tags.append('selected')
            
            # Se è sia nota di credito che selezionata, usa un tag combinato
            if sc.get('is_nota_credito', False) and sc.get('selected', False):
                tags = ['nota_credito_selected']
            
            self.tree.insert('', tk.END, values=values, iid=str(sc['scadenza_id']), tags=tags if tags else ())
        
        # Configura i tag per le note di credito (giallo chiaro)
        self.tree.tag_configure('nota_credito', background='#FFF9C4')
        
        # Configura il tag per le righe selezionate (verde chiaro/azzurro)
        self.tree.tag_configure('selected', background='#C8E6C9', foreground='#000000')  # Verde chiaro
        
        # Configura il tag combinato per note di credito selezionate (giallo-verde)
        self.tree.tag_configure('nota_credito_selected', background='#DCEDC8', foreground='#000000')  # Giallo-verde chiaro

        self.update_totale_selezionati()

    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#1":  # solo colonna checkbox
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        for sc in self.scadenze:
            if str(sc['scadenza_id']) == row_id:
                sc['selected'] = not sc['selected']
                break
        self.refresh_treeview()

    def update_totale_selezionati(self):
        # Calcola totale documenti normali selezionati
        totale_documenti = sum(sc['residuo'] for sc in self.scadenze 
                              if sc['selected'] and not sc.get('is_nota_credito', False))
        
        # Sottrai le note di credito selezionate (dalla lista principale)
        totale_nc = sum(sc['residuo'] for sc in self.scadenze 
                       if sc['selected'] and sc.get('is_nota_credito', False))
        
        totale_dopo_nc = max(0, totale_documenti - totale_nc)  # Non può essere negativo
        
        self.totale_selezionati_var.set(f"{totale_dopo_nc:.2f}")
        
        # Suggerisci il totale pagamento come totale selezionati (dopo NC) + spese accessorie
        try:
            spese_accessorie = float(self.spese_accessorie_var.get().replace(',', '.') or 0)
        except ValueError:
            spese_accessorie = 0.0
        suggerito = totale_dopo_nc + spese_accessorie
        if float(self.totale_pagamento_var.get().replace(',', '.') or 0) == 0:
            self.totale_pagamento_var.set(f"{suggerito:.2f}")

    def reset_form(self):
        """Resetta il form ai valori iniziali"""
        # Reset soggetto
        self.soggetto_selected_id = None
        self.soggetto_entry.config(state="normal")
        self.soggetto_entry.delete(0, tk.END)
        self.soggetto_entry.config(state="readonly")
        
        # Reset data pagamento - DateEntry non può essere completamente vuoto
        # Impostiamo una data di default lontana per indicare che non è stata selezionata
        # L'utente dovrà selezionare manualmente la data
        try:
            from datetime import datetime
            # Impostiamo una data di default (es. 01/01/1900) per indicare che non è stata selezionata
            default_date = datetime(1900, 1, 1)
            self.data_entry.set_date(default_date)
        except:
            pass
        
        # Reset modalità
        self.modalita_selected = "CONTANTI"
        self.modalita_entry.config(state="normal")
        self.modalita_entry.delete(0, tk.END)
        self.modalita_entry.insert(0, "CONTANTI")
        self.modalita_entry.config(state="readonly")
        
        # Reset totali
        self.totale_selezionati_var.set("0.00")
        self.spese_accessorie_var.set("0.00")
        self.totale_pagamento_var.set("0.00")
        
        # Reset scadenze (deseleziona tutto)
        for sc in self.scadenze:
            sc['selected'] = False
        self.refresh_treeview()
        
        # Pulisci la lista scadenze se non c'è un soggetto selezionato
        if not self.soggetto_selected_id:
            self.scadenze = []
            for it in self.tree.get_children():
                self.tree.delete(it)

    def salva_e_nuovo(self):
        """Salva il pagamento e resetta il form per inserirne un altro"""
        # Chiama salva_pagamento ma con un flag per non chiudere
        # Duplico la logica di salva_pagamento ma senza self.destroy()
        try:
            totale_pagamento = float(self.totale_pagamento_var.get().replace(',', '.').strip() or 0)
        except ValueError:
            messagebox.showerror("Errore", "Inserisci un importo valido per il pagamento.")
            return
        
        try:
            spese_accessorie = float(self.spese_accessorie_var.get().replace(',', '.').strip() or 0)
        except ValueError:
            spese_accessorie = 0.0

        selezionati = [sc for sc in self.scadenze if sc['selected'] and not sc.get('is_nota_credito', False)]
        note_credito_selez = [sc for sc in self.scadenze if sc['selected'] and sc.get('is_nota_credito', False)]
        
        if not selezionati and not note_credito_selez:
            messagebox.showerror("Errore", "Seleziona almeno un documento o una nota di credito.")
            return

        if totale_pagamento < 0:
            messagebox.showerror("Errore", "Totale pagamento non valido.")
            return

        modalita = self.modalita_selected.strip()
        data_pag = self.data_entry.get().strip()
        
        # Verifica che la data sia stata selezionata (non quella di default)
        if not data_pag or data_pag == "01/01/1900":
            messagebox.showerror("Errore", "Seleziona una data di pagamento valida.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION;")
            
            pagamento_id = None
            pagamenti_nc_creati = []
            
            if not self.soggetto_selected_id:
                messagebox.showerror("Errore", "Seleziona un soggetto.")
                return
            
            cur.execute("SELECT tipo_soggetto FROM soggetti WHERE id = ?", (self.soggetto_selected_id,))
            tipo_soggetto_row = cur.fetchone()
            tipo_soggetto = tipo_soggetto_row[0] if tipo_soggetto_row else 'CLIENTE'
            tipo_movimento = 'INCASSO' if tipo_soggetto == 'CLIENTE' else 'PAGAMENTO'
            
            # Usa la stessa logica di salva_pagamento per note di credito e pagamenti
            # (copio la logica completa da salva_pagamento)
            if note_credito_selez and selezionati:
                selezionati.sort(key=lambda x: x['data_scadenza'])
                note_credito_selez.sort(key=lambda x: x['data_documento'])
                applicazioni_per_nc = {}
                
                for nc in note_credito_selez:
                    residuo_nc = nc['residuo']
                    if residuo_nc <= 0.01:
                        continue
                    documento_nc_id = nc.get('documento_id')
                    if not documento_nc_id:
                        cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (nc['scadenza_id'],))
                        doc_nc_row = cur.fetchone()
                        if not doc_nc_row:
                            continue
                        documento_nc_id = doc_nc_row[0]
                    cur.execute("SELECT segno FROM documenti WHERE id = ?", (documento_nc_id,))
                    segno_nc_row = cur.fetchone()
                    segno_nc = segno_nc_row[0] if segno_nc_row else -1
                    tipo_movimento_nc = 'INCASSO' if segno_nc == -1 else 'PAGAMENTO'
                    applicazioni_per_nc[nc['scadenza_id']] = []
                    
                    for sc in selezionati:
                        if residuo_nc <= 0.01:
                            break
                        documento_sc_id = sc.get('documento_id')
                        if not documento_sc_id:
                            cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (sc['scadenza_id'],))
                            doc_sc_row = cur.fetchone()
                            if not doc_sc_row:
                                continue
                            documento_sc_id = doc_sc_row[0]
                        residuo_scadenza = sc['residuo']
                        if residuo_scadenza <= 0.01:
                            continue
                        importo_da_applicare = min(residuo_nc, residuo_scadenza)
                        if importo_da_applicare > 0.01:
                            applicazioni_per_nc[nc['scadenza_id']].append((documento_sc_id, importo_da_applicare))
                            residuo_nc -= importo_da_applicare
                            sc['residuo'] -= importo_da_applicare
                            sc['nc_applicata'] = sc.get('nc_applicata', 0) + importo_da_applicare
                            if sc['residuo'] <= 0.01:
                                cur.execute("UPDATE riba SET stato = 'Pagata' WHERE scadenza_id = ?", (sc['scadenza_id'],))
                    
                    if applicazioni_per_nc[nc['scadenza_id']]:
                        totale_applicato_nc = sum(imp for _, imp in applicazioni_per_nc[nc['scadenza_id']])
                        cur.execute("INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento) VALUES (?, ?, ?, 'NOTA_CREDITO_APPLICATA', 0, ?)", (data_pag, 0, 0, tipo_movimento_nc))
                        pagamento_nc_id = cur.lastrowid
                        pagamenti_nc_creati.append(pagamento_nc_id)
                        for documento_id, importo_applicato in applicazioni_per_nc[nc['scadenza_id']]:
                            cur.execute("INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)", (pagamento_nc_id, documento_id, importo_applicato, data_pag))
                        cur.execute("INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)", (pagamento_nc_id, documento_nc_id, totale_applicato_nc, data_pag))
            
            if selezionati and totale_pagamento > 0.01:
                importo_pagamento = totale_pagamento - spese_accessorie
                cur.execute("INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento) VALUES (?, ?, ?, ?, ?, ?)", (data_pag, importo_pagamento, totale_pagamento, modalita, spese_accessorie, tipo_movimento))
                pagamento_id = cur.lastrowid
                selezionati.sort(key=lambda x: x['data_scadenza'])
                residuo_pagamento = totale_pagamento
                for sc in selezionati:
                    if residuo_pagamento <= 0:
                        break
                    cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (sc['scadenza_id'],))
                    doc_sc_row = cur.fetchone()
                    if not doc_sc_row:
                        continue
                    documento_id = doc_sc_row[0]
                    residuo_effettivo = sc['residuo']
                    if residuo_effettivo <= 0.01:
                        continue
                    da_pagare = min(residuo_effettivo, residuo_pagamento)
                    if da_pagare > 0.01:
                        cur.execute("INSERT INTO associazioni_pagamenti (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) VALUES (?, ?, ?, 'PAGAMENTO', ?)", (pagamento_id, documento_id, da_pagare, data_pag))
                        residuo_pagamento -= da_pagare
                        cur.execute("SELECT sc.importo_scadenza - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0) - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo FROM scadenze sc LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = sc.id_documento WHERE sc.id = ? GROUP BY sc.id", (sc['scadenza_id'],))
                        residuo_row = cur.fetchone()
                        if residuo_row and residuo_row[0] <= 0.01:
                            cur.execute("UPDATE riba SET stato = 'Pagata' WHERE scadenza_id = ?", (sc['scadenza_id'],))

            conn.commit()
            conn.close()

            msg = "Pagamento salvato con successo!\n"
            if pagamenti_nc_creati:
                totale_nc_applicato = sum(nc['residuo'] for nc in note_credito_selez)
                msg += f"Note di credito applicate: € {totale_nc_applicato:.2f}\n"
            if totale_pagamento > 0 and pagamento_id:
                msg += f"Totale: € {totale_pagamento:.2f}"
            
            messagebox.showinfo("Successo", msg)
            if self.on_save_callback:
                self.on_save_callback()
            
            # Salva il soggetto selezionato prima di resettare
            soggetto_id_da_ricaricare = self.soggetto_selected_id
            
            # Resetta il form invece di chiudere
            self.reset_form()
            
            # Ricarica le scadenze se c'era un soggetto selezionato
            if soggetto_id_da_ricaricare:
                self.soggetto_selected_id = soggetto_id_da_ricaricare
                # Trova il nome del soggetto e lo mostra nel campo
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT ragione_sociale FROM soggetti WHERE id = ?", (soggetto_id_da_ricaricare,))
                row = cur.fetchone()
                conn.close()
                if row:
                    self.soggetto_entry.config(state="normal")
                    self.soggetto_entry.delete(0, tk.END)
                    self.soggetto_entry.insert(0, row[0])
                    self.soggetto_entry.config(state="readonly")
                self.load_scadenze_aperti(soggetto_id_da_ricaricare)
        
        except sqlite3.Error as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            messagebox.showerror("Errore DB", str(e))
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            messagebox.showerror("Errore", str(e))

    def salva_pagamento(self):
        try:
            totale_pagamento = float(self.totale_pagamento_var.get().replace(',', '.').strip() or 0)
        except ValueError:
            messagebox.showerror("Errore", "Inserisci un importo valido per il pagamento.")
            return
        
        try:
            spese_accessorie = float(self.spese_accessorie_var.get().replace(',', '.').strip() or 0)
        except ValueError:
            spese_accessorie = 0.0

        # Separa documenti normali e note di credito dalla lista principale
        selezionati = [sc for sc in self.scadenze if sc['selected'] and not sc.get('is_nota_credito', False)]
        note_credito_selez = [sc for sc in self.scadenze if sc['selected'] and sc.get('is_nota_credito', False)]
        
        if not selezionati and not note_credito_selez:
            messagebox.showerror("Errore", "Seleziona almeno un documento o una nota di credito.")
            return

        if totale_pagamento < 0:
            messagebox.showerror("Errore", "Totale pagamento non valido.")
            return

        modalita = self.modalita_selected.strip()
        data_pag = self.data_entry.get().strip()
        
        # Verifica che la data sia stata selezionata (non quella di default)
        if not data_pag or data_pag == "01/01/1900":
            messagebox.showerror("Errore", "Seleziona una data di pagamento valida.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION;")
            
            pagamento_id = None
            pagamenti_nc_creati = []  # Lista dei pagamenti creati per le note di credito
            
            # Determina tipo_movimento in base al soggetto
            # Recupera il tipo del soggetto (cliente o fornitore)
            if not self.soggetto_selected_id:
                messagebox.showerror("Errore", "Seleziona un soggetto.")
                return
            
            cur.execute("""
                SELECT tipo_soggetto FROM soggetti WHERE id = ?
            """, (self.soggetto_selected_id,))
            tipo_soggetto_row = cur.fetchone()
            tipo_soggetto = tipo_soggetto_row[0] if tipo_soggetto_row else 'CLIENTE'
            tipo_movimento = 'INCASSO' if tipo_soggetto == 'CLIENTE' else 'PAGAMENTO'
            
            # 🔹 STEP 1: Applica le note di credito selezionate alle scadenze selezionate
            if note_credito_selez and selezionati:
                # Ordina scadenze per data (FIFO) e note di credito per data
                selezionati.sort(key=lambda x: x['data_scadenza'])
                note_credito_selez.sort(key=lambda x: x['data_documento'])
                
                # Raggruppa le applicazioni per nota di credito per creare un pagamento per ogni NC
                applicazioni_per_nc = {}  # {nc_scadenza_id: [(doc_id, importo), ...]}
                
                # Distribuisci le note di credito alle scadenze
                for nc in note_credito_selez:
                    residuo_nc = nc['residuo']
                    if residuo_nc <= 0.01:
                        continue
                    
                    # Usa documento_id dalla lista (già presente) o recupera dal database
                    documento_nc_id = nc.get('documento_id')
                    if not documento_nc_id:
                        cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (nc['scadenza_id'],))
                        doc_nc_row = cur.fetchone()
                        if not doc_nc_row:
                            continue
                        documento_nc_id = doc_nc_row[0]
                    
                    # Determina tipo_movimento per la NC (in base al segno del documento)
                    cur.execute("SELECT segno FROM documenti WHERE id = ?", (documento_nc_id,))
                    segno_nc_row = cur.fetchone()
                    segno_nc = segno_nc_row[0] if segno_nc_row else -1
                    tipo_movimento_nc = 'INCASSO' if segno_nc == -1 else 'PAGAMENTO'
                    
                    applicazioni_per_nc[nc['scadenza_id']] = []
                    
                    for sc in selezionati:
                        if residuo_nc <= 0.01:
                            break
                        
                        # Usa documento_id dalla lista (già presente) o recupera dal database
                        documento_sc_id = sc.get('documento_id')
                        if not documento_sc_id:
                            cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (sc['scadenza_id'],))
                            doc_sc_row = cur.fetchone()
                            if not doc_sc_row:
                                continue
                            documento_sc_id = doc_sc_row[0]
                        
                        # Calcola quanto residuo rimane sulla scadenza
                        residuo_scadenza = sc['residuo']
                        if residuo_scadenza <= 0.01:
                            continue
                        
                        # Applica la nota di credito (il minimo tra residuo NC e residuo scadenza)
                        importo_da_applicare = min(residuo_nc, residuo_scadenza)
                        
                        if importo_da_applicare > 0.01:
                            # Aggiungi all'elenco delle applicazioni per questa nota di credito
                            applicazioni_per_nc[nc['scadenza_id']].append((documento_sc_id, importo_da_applicare))
                            
                            residuo_nc -= importo_da_applicare
                            
                            # Aggiorna il residuo della scadenza nel dizionario per i calcoli successivi
                            sc['residuo'] -= importo_da_applicare
                            sc['nc_applicata'] = sc.get('nc_applicata', 0) + importo_da_applicare
                            
                            # Verifica se la scadenza è ora completamente saldata (solo con NC)
                            if sc['residuo'] <= 0.01:
                                cur.execute("""
                                    UPDATE riba
                                    SET stato = 'Pagata'
                                    WHERE scadenza_id = ?
                                """, (sc['scadenza_id'],))
                    
                    # 🔹 Crea un pagamento per questa nota di credito (se ci sono applicazioni)
                    if applicazioni_per_nc[nc['scadenza_id']]:
                        totale_applicato_nc = sum(imp for _, imp in applicazioni_per_nc[nc['scadenza_id']])
                        
                        # Crea un pagamento per tracciare l'applicazione della nota di credito
                        # Usa 'NOTA_CREDITO_APPLICATA' per la modalità (valore valido nel constraint)
                        cur.execute("""
                            INSERT INTO pagamenti 
                            (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento) 
                            VALUES (?, ?, ?, 'NOTA_CREDITO_APPLICATA', 0, ?)
                        """, (data_pag, 0, 0, tipo_movimento_nc))
                        pagamento_nc_id = cur.lastrowid
                        pagamenti_nc_creati.append(pagamento_nc_id)
                        
                        # Crea le associazioni per ogni documento a cui è stata applicata la NC
                        for documento_id, importo_applicato in applicazioni_per_nc[nc['scadenza_id']]:
                            # Associazione: NC applicata al documento fattura
                            cur.execute("""
                                INSERT INTO associazioni_pagamenti 
                                (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                                VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)
                            """, (pagamento_nc_id, documento_id, importo_applicato, data_pag))
                        
                        # 🔹 IMPORTANTE: Crea anche un'associazione per la nota di credito stessa
                        # Questo permette di tracciare che la NC è stata utilizzata e calcolare correttamente il residuo
                        cur.execute("""
                            INSERT INTO associazioni_pagamenti 
                            (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                            VALUES (?, ?, ?, 'STORNO_NOTA_CREDITO', ?)
                        """, (pagamento_nc_id, documento_nc_id, totale_applicato_nc, data_pag))
            
            # 🔹 Verifica e chiudi le note di credito completamente utilizzate
            # Dopo aver applicato tutte le note di credito, verifica quali sono completamente utilizzate
            for nc in note_credito_selez:
                # Recupera l'ID del documento nota di credito
                cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (nc['scadenza_id'],))
                doc_nc_row = cur.fetchone()
                
                if doc_nc_row:
                    documento_nc_id = doc_nc_row[0]
                    # Verifica il residuo totale del documento nota di credito usando associazioni_pagamenti
                    cur.execute("""
                        SELECT 
                            ABS(SUM(sc.importo_scadenza)) AS totale_importo,
                            IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS totale_applicato
                        FROM scadenze sc
                        LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = sc.id_documento
                        WHERE sc.id_documento = ?
                        GROUP BY sc.id_documento
                    """, (documento_nc_id,))
                    residuo_totale_row = cur.fetchone()
                    
                    if residuo_totale_row:
                        totale_importo = abs(float(residuo_totale_row[0])) if residuo_totale_row[0] else 0.0
                        totale_applicato = float(residuo_totale_row[1]) if residuo_totale_row[1] else 0.0
                        residuo_totale = totale_importo - totale_applicato
                        
                        # Se il residuo totale è <= 0.01, la nota di credito è completamente utilizzata
                        # Non serve creare un pagamento virtuale perché le associazioni già tracciano tutto
            
            # 🔹 STEP 2: Applica il pagamento alle scadenze (dopo le note di credito)
            # IMPORTANTE: Crea il pagamento solo se c'è un importo effettivo da pagare
            # Se ci sono solo note di credito senza pagamento, non creare un pagamento normale
            if selezionati and totale_pagamento > 0.01:
                # Calcola importo pagamento (senza spese accessorie) per la distribuzione alle scadenze
                importo_pagamento = totale_pagamento - spese_accessorie
                cur.execute(
                    "INSERT INTO pagamenti (data_pagamento, importo_pagamento, totale, modalita_pagamento, spese, tipo_movimento) VALUES (?, ?, ?, ?, ?, ?)",
                    (data_pag, importo_pagamento, totale_pagamento, modalita, spese_accessorie, tipo_movimento)
                )
                pagamento_id = cur.lastrowid

                # 🔹 Distribuzione FIFO: pago prima le scadenze più vecchie
                selezionati.sort(key=lambda x: x['data_scadenza'])
                
                # Usa sempre il totale pagamento (incluso spese accessorie) per la distribuzione
                residuo_pagamento = totale_pagamento

                for sc in selezionati:
                    if residuo_pagamento <= 0:
                        break
                    
                    # Recupera l'ID del documento della scadenza
                    cur.execute("SELECT id_documento FROM scadenze WHERE id = ?", (sc['scadenza_id'],))
                    doc_sc_row = cur.fetchone()
                    if not doc_sc_row:
                        continue
                    documento_id = doc_sc_row[0]
                    
                    # Usa il residuo aggiornato (dopo note di credito)
                    residuo_effettivo = sc['residuo']
                    if residuo_effettivo <= 0.01:
                        continue
                    
                    # Pagamento parziale o totale
                    da_pagare = min(residuo_effettivo, residuo_pagamento)
                    
                    if da_pagare > 0.01:
                        # Crea associazione pagamento-documento
                        cur.execute("""
                            INSERT INTO associazioni_pagamenti 
                            (id_pagamento, id_documento, importo_associato, tipo_associazione, data_associazione) 
                            VALUES (?, ?, ?, 'PAGAMENTO', ?)
                        """, (pagamento_id, documento_id, da_pagare, data_pag))
                        residuo_pagamento -= da_pagare

                        # 🔸 Verifica se la scadenza è ora completamente pagata usando associazioni_pagamenti
                        cur.execute("""
                            SELECT 
                                sc.importo_scadenza 
                                - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'PAGAMENTO' THEN ap.importo_associato ELSE 0 END), 0)
                                - IFNULL(SUM(CASE WHEN ap.tipo_associazione = 'STORNO_NOTA_CREDITO' THEN ap.importo_associato ELSE 0 END), 0) AS residuo
                            FROM scadenze sc
                            LEFT JOIN associazioni_pagamenti ap ON ap.id_documento = sc.id_documento
                            WHERE sc.id = ?
                            GROUP BY sc.id
                        """, (sc['scadenza_id'],))
                        residuo_row = cur.fetchone()

                        if residuo_row and residuo_row[0] <= 0.01:
                            # 🔸 Se esiste una RIBA collegata, aggiorna lo stato in 'Pagata'
                            cur.execute("""
                                UPDATE riba
                                SET stato = 'Pagata'
                                WHERE scadenza_id = ?
                            """, (sc['scadenza_id'],))

            conn.commit()
            conn.close()

            # Messaggio di successo
            msg = "Operazione completata con successo!\n"
            if pagamenti_nc_creati:
                totale_nc_applicato = 0
                for nc in note_credito_selez:
                    # Calcola quanto è stato effettivamente applicato
                    residuo_iniziale = nc['residuo']
                    # Il residuo iniziale è quello che poteva essere applicato
                    totale_nc_applicato += residuo_iniziale
                msg += f"Note di credito applicate: € {totale_nc_applicato:.2f}\n"
                msg += f"Pagamenti creati per note di credito: {len(pagamenti_nc_creati)} (ID: {', '.join(map(str, pagamenti_nc_creati))})\n"
            if totale_pagamento > 0 and pagamento_id:
                msg += f"Pagamento salvato (ID: {pagamento_id})\nTotale: € {totale_pagamento:.2f}"
            
            messagebox.showinfo("Successo", msg)
            if self.on_save_callback:
                self.on_save_callback()
            self.destroy()
        
        except sqlite3.Error as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            messagebox.showerror("Errore DB", str(e))
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            messagebox.showerror("Errore DB", str(e))
