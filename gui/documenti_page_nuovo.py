import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import sys

# Importa gli stili
sys.path.append('assets/style')
from styles import Style

class NuovoDocumentoWindow:
    def __init__(self, parent, db_path):
        self.parent = parent
        self.db_path = db_path
        self.callback_success = None
        self.nuovo_window = None
        self.scadenze_entries = []
        self.current_scadenze_count = 0
        
        # Crea la finestra
        self.create_window()
        
    def set_callback_success(self, callback):
        """Imposta una callback da chiamare dopo una creazione riuscita"""
        self.callback_success = callback
        
    def create_window(self):
        """Crea la finestra per nuovo documento"""
        self.nuovo_window = tk.Toplevel(self.parent)
        self.nuovo_window.title("Nuovo Documento")
        self.nuovo_window.geometry("600x700")
        self.nuovo_window.resizable(False, False)
        self.nuovo_window.configure(bg=Style.WHITE)
        self.nuovo_window.transient(self.parent)
        self.nuovo_window.grab_set()
        
        # Frame principale con scrollbar
        self.canvas = tk.Canvas(self.nuovo_window, bg=Style.WHITE)
        self.scrollbar = ttk.Scrollbar(self.nuovo_window, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=Style.WHITE)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas e scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Crea l'interfaccia
        self.create_interface()
        
    def create_interface(self):
        """Crea l'interfaccia grafica per il nuovo documento"""
        # Frame principale
        main_frame = tk.Frame(self.scrollable_frame, bg=Style.WHITE, padx=30, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="Nuovo Documento", 
                 bg=Style.WHITE, fg="#000000", 
                 font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        # Sezione Dati Documento
        tk.Label(main_frame, text="📄 Dati Documento", bg=Style.WHITE, 
                 fg="#1976D2", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Campo Data
        data_frame = tk.Frame(main_frame, bg=Style.WHITE)
        data_frame.pack(fill="x", pady=8)
        tk.Label(data_frame, text="Data Documento:*", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.data_entry = tk.Entry(data_frame, font=("Arial", 10), width=28)
        self.data_entry.insert(0, self.get_current_date())
        self.data_entry.pack(side="left", padx=(10, 0))
        
        # Campo Tipo
        tipo_frame = tk.Frame(main_frame, bg=Style.WHITE)
        tipo_frame.pack(fill="x", pady=8)
        tk.Label(tipo_frame, text="Tipo Documento:*", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.tipo_combobox = ttk.Combobox(tipo_frame, font=("Arial", 10), width=26, state="normal")
        self.tipo_combobox['values'] = ('FT_VENDITA', 'FT_ACQUISTO')
        self.tipo_combobox.set('FT_VENDITA')
        self.tipo_combobox.pack(side="left", padx=(10, 0))
        
        # Campo Numero
        numero_frame = tk.Frame(main_frame, bg=Style.WHITE)
        numero_frame.pack(fill="x", pady=8)
        tk.Label(numero_frame, text="Numero Documento:", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.numero_entry = tk.Entry(numero_frame, font=("Arial", 10), width=28)
        self.numero_entry.pack(side="left", padx=(10, 0))
        
        # Campo Soggetto
        soggetto_frame = tk.Frame(main_frame, bg=Style.WHITE)
        soggetto_frame.pack(fill="x", pady=8)
        tk.Label(soggetto_frame, text="Soggetto:*", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        
        # Frame per combobox e pulsante nuovo soggetto
        soggetto_input_frame = tk.Frame(soggetto_frame, bg=Style.WHITE)
        soggetto_input_frame.pack(side="left", padx=(10, 0))
        
        self.soggetto_combobox = ttk.Combobox(soggetto_input_frame, font=("Arial", 10), width=20, state="normal")
        self.load_soggetti()
        self.soggetto_combobox.pack(side="left")
        
        btn_nuovo_soggetto = tk.Button(soggetto_input_frame, text="+", 
                                      command=self.nuovo_soggetto,
                                      bg="#2196F3", fg="white", font=("Arial", 9, "bold"),
                                      width=3, cursor="hand2")
        btn_nuovo_soggetto.pack(side="left", padx=(5, 0))
        
        # Campo Imponibile
        imponibile_frame = tk.Frame(main_frame, bg=Style.WHITE)
        imponibile_frame.pack(fill="x", pady=8)
        tk.Label(imponibile_frame, text="Imponibile:*", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.imponibile_entry = tk.Entry(imponibile_frame, font=("Arial", 10), width=28)
        self.imponibile_entry.pack(side="left", padx=(10, 0))
        
        # Campo Importo Totale
        importo_frame = tk.Frame(main_frame, bg=Style.WHITE)
        importo_frame.pack(fill="x", pady=8)
        tk.Label(importo_frame, text="Importo Totale:*", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.importo_entry = tk.Entry(importo_frame, font=("Arial", 10), width=28)
        self.importo_entry.pack(side="left", padx=(10, 0))
        
        # Separatore
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=20)
        
        # Sezione Scadenze
        scadenze_header_frame = tk.Frame(main_frame, bg=Style.WHITE)
        scadenze_header_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(scadenze_header_frame, text="📅 Scadenze", bg=Style.WHITE, 
                 fg="#1976D2", font=("Arial", 12, "bold")).pack(side="left")
        
        # Pulsante per aggiungere scadenza
        btn_aggiungi_scadenza = tk.Button(scadenze_header_frame, text="+ Aggiungi Scadenza",
                                         command=self.aggiungi_scadenza,
                                         bg="#4CAF50", fg="white", font=("Arial", 9, "bold"),
                                         cursor="hand2", padx=10)
        btn_aggiungi_scadenza.pack(side="right")
        
        # Frame per le scadenze
        self.scadenze_container = tk.Frame(main_frame, bg=Style.WHITE)
        self.scadenze_container.pack(fill="x", pady=(0, 20))
        
        # Aggiungi una scadenza di default
        self.aggiungi_scadenza()
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg=Style.WHITE)
        button_frame.pack(pady=30)
        
        btn_salva = tk.Button(button_frame, text="💾 Salva Documento", command=self.salva_documento,
                             bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), 
                             width=18, cursor="hand2", pady=10)
        btn_salva.pack(side="left", padx=10)
        
        btn_annulla = tk.Button(button_frame, text="✖ Annulla", command=self.nuovo_window.destroy,
                               bg="#f44336", fg="white", font=("Arial", 11, "bold"), 
                               width=14, cursor="hand2", pady=10)
        btn_annulla.pack(side="left", padx=10)
    
    def get_current_date(self):
        """Restituisce la data corrente nel formato DD/MM/YYYY"""
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y")
    
    def load_soggetti(self):
        """Carica la lista dei soggetti dal database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, ragione_sociale FROM soggetti ORDER BY ragione_sociale")
            soggetti = cursor.fetchall()
            conn.close()
            
            # Crea un dizionario per memorizzare ID -> Ragione Sociale
            self.soggetti_dict = {row[1]: row[0] for row in soggetti}
            self.soggetto_combobox['values'] = list(self.soggetti_dict.keys())
            
            if soggetti:
                self.soggetto_combobox.set(list(self.soggetti_dict.keys())[0])
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei soggetti:\n{str(e)}")
            self.soggetti_dict = {}
    
    def nuovo_soggetto(self):
        """Apre una finestra per creare un nuovo soggetto"""
        nuovo_soggetto = simpledialog.askstring("Nuovo Soggetto", "Inserisci la ragione sociale del nuovo soggetto:")
        if nuovo_soggetto and nuovo_soggetto.strip():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO soggetti (ragione_sociale) VALUES (?)", (nuovo_soggetto.strip(),))
                conn.commit()
                conn.close()
                
                # Ricarica la lista dei soggetti
                self.load_soggetti()
                self.soggetto_combobox.set(nuovo_soggetto.strip())
                
                messagebox.showinfo("Successo", "Soggetto creato con successo!")
                
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nella creazione del soggetto:\n{str(e)}")
    
    def aggiungi_scadenza(self):
        """Aggiunge una nuova riga per una scadenza"""
        self.current_scadenze_count += 1
        idx = self.current_scadenze_count
        
        scad_frame = tk.LabelFrame(self.scadenze_container, text=f"Scadenza {idx}", 
                                   bg=Style.WHITE, font=("Arial", 9, "bold"),
                                   fg="#555", padx=10, pady=10)
        scad_frame.pack(fill="x", pady=5)
        
        # Data Scadenza
        data_scad_frame = tk.Frame(scad_frame, bg=Style.WHITE)
        data_scad_frame.pack(fill="x", pady=3)
        tk.Label(data_scad_frame, text="Data Scadenza:*", bg=Style.WHITE, 
                 font=("Arial", 9), width=15, anchor="w").pack(side="left")
        data_scad_entry = tk.Entry(data_scad_frame, font=("Arial", 9), width=15)
        data_scad_entry.pack(side="left", padx=(5, 0))
        
        # Tipo Pagamento
        tipo_pag_frame = tk.Frame(scad_frame, bg=Style.WHITE)
        tipo_pag_frame.pack(fill="x", pady=3)
        tk.Label(tipo_pag_frame, text="Tipo Pagamento:", bg=Style.WHITE, 
                 font=("Arial", 9), width=15, anchor="w").pack(side="left")
        tipo_pag_combobox = ttk.Combobox(tipo_pag_frame, font=("Arial", 9), width=13, state="normal")
        tipo_pag_combobox['values'] = ('BONIFICO', 'CONTANTI', 'ASSEGNO', 'CARTA CREDITO', 'RIBA', 'RID')
        tipo_pag_combobox.set('BONIFICO')
        tipo_pag_combobox.pack(side="left", padx=(5, 0))
        
        # Importo
        importo_frame = tk.Frame(scad_frame, bg=Style.WHITE)
        importo_frame.pack(fill="x", pady=3)
        tk.Label(importo_frame, text="Importo:*", bg=Style.WHITE, 
                 font=("Arial", 9), width=15, anchor="w").pack(side="left")
        importo_entry = tk.Entry(importo_frame, font=("Arial", 9), width=15)
        importo_entry.pack(side="left", padx=(5, 0))
        
        # Pulsante per rimuovere scadenza
        btn_rimuovi = tk.Button(scad_frame, text="✖", 
                               command=lambda f=scad_frame: self.rimuovi_scadenza(f),
                               bg="#f44336", fg="white", font=("Arial", 8, "bold"),
                               width=3, cursor="hand2")
        btn_rimuovi.pack(side="right", padx=(5, 0))
        
        # Memorizza i riferimenti agli entry
        self.scadenze_entries.append({
            'frame': scad_frame,
            'data_entry': data_scad_entry,
            'tipo_pag_combobox': tipo_pag_combobox,
            'importo_entry': importo_entry
        })
    
    def rimuovi_scadenza(self, frame):
        """Rimuove una scadenza dall'interfaccia"""
        if len(self.scadenze_entries) > 1:  # Mantieni almeno una scadenza
            # Trova e rimuovi dalla lista
            for i, entry in enumerate(self.scadenze_entries):
                if entry['frame'] == frame:
                    self.scadenze_entries.pop(i)
                    break
            
            # Distruggi il frame
            frame.destroy()
            
            # Rinumera le scadenze rimanenti
            for i, entry in enumerate(self.scadenze_entries, 1):
                entry['frame'].configure(text=f"Scadenza {i}")
        else:
            messagebox.showwarning("Attenzione", "Deve esserci almeno una scadenza.")
    
    def get_segno_from_tipo(self, tipo_documento):
        """Restituisce il segno in base al tipo di documento"""
        if tipo_documento == 'FT_VENDITA':
            return 1
        elif tipo_documento == 'FT_ACQUISTO':
            return -1
        else:
            return 1  # Default a 1 per sicurezza
    
    def salva_documento(self):
        """Salva il nuovo documento nel database"""
        # Validazione campi obbligatori
        data_doc = self.data_entry.get().strip()
        tipo_doc = self.tipo_combobox.get().strip()
        soggetto_nome = self.soggetto_combobox.get().strip()
        imponibile = self.imponibile_entry.get().strip()
        importo_totale = self.importo_entry.get().strip()
        
        if not data_doc or not tipo_doc or not soggetto_nome or not imponibile or not importo_totale:
            messagebox.showwarning("Attenzione", "Tutti i campi contrassegnati con * sono obbligatori.")
            return
        
        # Validazione tipo documento
        if tipo_doc not in ['FT_VENDITA', 'FT_ACQUISTO']:
            messagebox.showwarning("Attenzione", "Tipo documento non valido. Selezionare FT_VENDITA o FT_ACQUISTO.")
            return
        
        # Validazione imponibile
        try:
            imponibile_float = float(imponibile.replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Attenzione", "L'imponibile deve essere un numero valido.")
            return
        
        # Validazione importo totale
        try:
            importo_totale_float = float(importo_totale.replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Attenzione", "L'importo totale deve essere un numero valido.")
            return
        
        # Validazione scadenze
        scadenze_valide = []
        totale_scadenze = 0.0
        
        for i, scadenza in enumerate(self.scadenze_entries, 1):
            data_scad = scadenza['data_entry'].get().strip()
            tipo_pag = scadenza['tipo_pag_combobox'].get().strip()
            importo_scad = scadenza['importo_entry'].get().strip()
            
            if not data_scad or not importo_scad:
                messagebox.showwarning("Attenzione", f"Data e importo sono obbligatori per la scadenza {i}.")
                return
            
            try:
                importo_scad_float = float(importo_scad.replace(',', '.'))
                totale_scadenze += importo_scad_float
            except ValueError:
                messagebox.showwarning("Attenzione", f"L'importo della scadenza {i} deve essere un numero valido.")
                return
            
            scadenze_valide.append({
                'data_scadenza': data_scad,
                'tipo_pagamento': tipo_pag,
                'importo': importo_scad_float
            })
        
        # Verifica che il totale delle scadenze corrisponda all'importo totale
        if abs(totale_scadenze - importo_totale_float) > 0.01:  # Tolleranza per arrotondamenti
            messagebox.showwarning("Attenzione", 
                                 f"La somma delle scadenze ({totale_scadenze:.2f}) non corrisponde all'importo totale ({importo_totale_float:.2f}).")
            return
        
        # Ottieni l'ID del soggetto
        soggetto_id = self.soggetti_dict.get(soggetto_nome)
        if not soggetto_id:
            messagebox.showerror("Errore", "Soggetto non valido.")
            return
        
        # Determina il segno in base al tipo di documento
        segno = self.get_segno_from_tipo(tipo_doc)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Inserisci il documento con i campi totale e importo_imponibile
            cursor.execute("""
                INSERT INTO documenti (data_documento, tipo_documento, numero_documento, 
                                      soggetto_id, segno, totale, importo_imponibile)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data_doc, tipo_doc, self.numero_entry.get().strip(), 
                  soggetto_id, segno, importo_totale_float, imponibile_float))
            
            # Ottieni l'ID del documento appena inserito
            documento_id = cursor.lastrowid
            
            # Inserisci le scadenze
            for scadenza in scadenze_valide:
                cursor.execute("""
                    INSERT INTO scadenze (id_documento, data_scadenza, tipo_pagamento, importo_scadenza)
                    VALUES (?, ?, ?, ?)
                """, (documento_id, scadenza['data_scadenza'], scadenza['tipo_pagamento'], scadenza['importo']))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Documento creato con successo!")
            self.nuovo_window.destroy()
            
            # Chiama la callback di successo se impostata
            if self.callback_success:
                self.callback_success()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il salvataggio:\n{str(e)}")