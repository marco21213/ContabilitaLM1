import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import sys

# Importa gli stili
sys.path.append('assets/style')
from styles import Style

class ModificaDocumentoWindow:
    def __init__(self, parent, documento_id, db_path):
        self.parent = parent
        self.documento_id = documento_id
        self.db_path = db_path
        self.callback_success = None
        self.edit_window = None
        
        # Crea la finestra
        self.create_window()
        
    def set_callback_success(self, callback):
        """Imposta una callback da chiamare dopo una modifica riuscita"""
        self.callback_success = callback
        
    def create_window(self):
        """Crea la finestra di modifica documento"""
        self.edit_window = tk.Toplevel(self.parent)
        self.edit_window.title("Modifica Documento")
        self.edit_window.geometry("550x600")
        self.edit_window.resizable(False, False)
        self.edit_window.configure(bg=Style.WHITE)
        self.edit_window.transient(self.parent)
        self.edit_window.grab_set()
        
        # Frame principale con scrollbar
        self.canvas = tk.Canvas(self.edit_window, bg=Style.WHITE)
        self.scrollbar = ttk.Scrollbar(self.edit_window, orient="vertical", command=self.canvas.yview)
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
        
        # Carica e mostra i dati
        self.load_and_display_data()
        
    def load_and_display_data(self):
        """Carica i dati dal database e li mostra nella finestra"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Dati documento
            cursor.execute("""
                SELECT d.data_documento, d.tipo_documento, d.numero_documento, 
                       d.soggetto_id, s.ragione_sociale
                FROM documenti d
                LEFT JOIN soggetti s ON s.id = d.soggetto_id
                WHERE d.id = ?
            """, (self.documento_id,))
            doc_data = cursor.fetchone()
            
            # Dati scadenze
            cursor.execute("""
                SELECT id, data_scadenza, tipo_pagamento, importo_scadenza
                FROM scadenze
                WHERE id_documento = ?
                ORDER BY data_scadenza
            """, (self.documento_id,))
            scadenze_data = cursor.fetchall()
            
            conn.close()
            
            if not doc_data:
                messagebox.showerror("Errore", "Documento non trovato nel database.")
                self.edit_window.destroy()
                return
            
            # Mostra i dati nell'interfaccia
            self.create_interface(doc_data, scadenze_data)
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei dati:\n{str(e)}")
            if self.edit_window:
                self.edit_window.destroy()
            return
    
    def create_interface(self, doc_data, scadenze_data):
        """Crea l'interfaccia grafica con i dati del documento"""
        # Frame principale
        main_frame = tk.Frame(self.scrollable_frame, bg=Style.WHITE, padx=30, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="Modifica Documento", 
                 bg=Style.WHITE, fg="#000000", 
                 font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        # Sezione Dati Documento
        tk.Label(main_frame, text="📄 Dati Documento", bg=Style.WHITE, 
                 fg="#1976D2", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Campo Data
        data_frame = tk.Frame(main_frame, bg=Style.WHITE)
        data_frame.pack(fill="x", pady=8)
        tk.Label(data_frame, text="Data Documento:", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.data_entry = tk.Entry(data_frame, font=("Arial", 10), width=28)
        self.data_entry.insert(0, doc_data[0])
        self.data_entry.pack(side="left", padx=(10, 0))
        
        # Campo Tipo
        tipo_frame = tk.Frame(main_frame, bg=Style.WHITE)
        tipo_frame.pack(fill="x", pady=8)
        tk.Label(tipo_frame, text="Tipo Documento:", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.tipo_entry = tk.Entry(tipo_frame, font=("Arial", 10), width=28)
        self.tipo_entry.insert(0, doc_data[1])
        self.tipo_entry.pack(side="left", padx=(10, 0))
        
        # Campo Numero
        numero_frame = tk.Frame(main_frame, bg=Style.WHITE)
        numero_frame.pack(fill="x", pady=8)
        tk.Label(numero_frame, text="Numero Documento:", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        self.numero_entry = tk.Entry(numero_frame, font=("Arial", 10), width=28)
        self.numero_entry.insert(0, doc_data[2] if doc_data[2] else "")
        self.numero_entry.pack(side="left", padx=(10, 0))
        
        # Campo Soggetto (readonly per ora)
        soggetto_frame = tk.Frame(main_frame, bg=Style.WHITE)
        soggetto_frame.pack(fill="x", pady=8)
        tk.Label(soggetto_frame, text="Soggetto:", bg=Style.WHITE, 
                 font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        soggetto_label = tk.Label(soggetto_frame, text=doc_data[4] if doc_data[4] else "N/A",
                                  bg="#f5f5f5", font=("Arial", 10), width=28, 
                                  anchor="w", relief="solid", borderwidth=1, padx=5)
        soggetto_label.pack(side="left", padx=(10, 0))
        
        # Separatore
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=20)
        
        # Sezione Scadenze
        tk.Label(main_frame, text="📅 Scadenze e Pagamenti", bg=Style.WHITE, 
                 fg="#1976D2", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Lista scadenze modificabili
        self.scadenze_entries = []
        
        if scadenze_data:
            for idx, scadenza in enumerate(scadenze_data, 1):
                scad_id, data_scad, tipo_pag, importo = scadenza
                
                scad_frame = tk.LabelFrame(main_frame, text=f"Scadenza {idx}", 
                                           bg=Style.WHITE, font=("Arial", 9, "bold"),
                                           fg="#555", padx=10, pady=10)
                scad_frame.pack(fill="x", pady=10)
                
                # Data Scadenza
                data_scad_frame = tk.Frame(scad_frame, bg=Style.WHITE)
                data_scad_frame.pack(fill="x", pady=5)
                tk.Label(data_scad_frame, text="Data Scadenza:", bg=Style.WHITE, 
                         font=("Arial", 9), width=18, anchor="w").pack(side="left")
                data_scad_entry = tk.Entry(data_scad_frame, font=("Arial", 9), width=28)
                data_scad_entry.insert(0, data_scad if data_scad else "")
                data_scad_entry.pack(side="left", padx=(5, 0))
                
                # Tipo Pagamento
                tipo_pag_frame = tk.Frame(scad_frame, bg=Style.WHITE)
                tipo_pag_frame.pack(fill="x", pady=5)
                tk.Label(tipo_pag_frame, text="Tipo Pagamento:", bg=Style.WHITE, 
                         font=("Arial", 9), width=18, anchor="w").pack(side="left")
                tipo_pag_entry = tk.Entry(tipo_pag_frame, font=("Arial", 9), width=28)
                tipo_pag_entry.insert(0, tipo_pag if tipo_pag else "")
                tipo_pag_entry.pack(side="left", padx=(5, 0))
                
                # Importo (readonly)
                importo_frame = tk.Frame(scad_frame, bg=Style.WHITE)
                importo_frame.pack(fill="x", pady=5)
                tk.Label(importo_frame, text="Importo:", bg=Style.WHITE, 
                         font=("Arial", 9), width=18, anchor="w").pack(side="left")
                importo_text = f"€ {importo:,.2f}" if importo else "€ 0.00"
                tk.Label(importo_frame, text=importo_text, bg="#f5f5f5", 
                         font=("Arial", 9), width=28, anchor="e", 
                         relief="solid", borderwidth=1, padx=5).pack(side="left", padx=(5, 0))
                
                self.scadenze_entries.append({
                    'id': scad_id,
                    'data_entry': data_scad_entry,
                    'tipo_pag_entry': tipo_pag_entry
                })
        else:
            # Nessuna scadenza trovata
            no_scadenze_frame = tk.Frame(main_frame, bg=Style.WHITE)
            no_scadenze_frame.pack(fill="x", pady=20)
            tk.Label(no_scadenze_frame, text="Nessuna scadenza trovata per questo documento",
                     bg=Style.WHITE, fg="#666", font=("Arial", 10, "italic")).pack()
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg=Style.WHITE)
        button_frame.pack(pady=30)
        
        btn_salva = tk.Button(button_frame, text="💾 Salva", command=self.salva_modifiche,
                             bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), 
                             width=14, cursor="hand2", pady=10)
        btn_salva.pack(side="left", padx=10)
        
        btn_annulla = tk.Button(button_frame, text="✖ Annulla", command=self.edit_window.destroy,
                               bg="#f44336", fg="white", font=("Arial", 11, "bold"), 
                               width=14, cursor="hand2", pady=10)
        btn_annulla.pack(side="left", padx=10)
    
    def salva_modifiche(self):
        """Salva le modifiche nel database"""
        new_data = self.data_entry.get().strip()
        new_tipo = self.tipo_entry.get().strip()
        new_numero = self.numero_entry.get().strip()
        
        if not new_data or not new_tipo:
            messagebox.showwarning("Attenzione", "Data e Tipo documento sono obbligatori.")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Aggiorna documento
            cursor.execute("""
                UPDATE documenti 
                SET data_documento = ?, tipo_documento = ?, numero_documento = ?
                WHERE id = ?
            """, (new_data, new_tipo, new_numero, self.documento_id))
            
            # Aggiorna scadenze solo se presenti
            if hasattr(self, 'scadenze_entries') and self.scadenze_entries:
                for scad_entry in self.scadenze_entries:
                    new_data_scad = scad_entry['data_entry'].get().strip()
                    new_tipo_pag = scad_entry['tipo_pag_entry'].get().strip()
                    
                    if new_data_scad:  # Solo se la data è presente
                        cursor.execute("""
                            UPDATE scadenze 
                            SET data_scadenza = ?, tipo_pagamento = ?
                            WHERE id = ?
                        """, (new_data_scad, new_tipo_pag, scad_entry['id']))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Documento modificato con successo.")
            self.edit_window.destroy()
            
            # Chiama la callback di successo se impostata
            if self.callback_success:
                self.callback_success()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la modifica:\n{str(e)}")