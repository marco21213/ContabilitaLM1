"""
Pagina Ricette Laboratorio - Gestione ricette (colori) del laboratorio
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import configparser
import os
from datetime import datetime
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style

# Importa funzioni per configurazione email dal database
import sys
import os
# Aggiungi il percorso alla root del progetto per importare scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.email_config_db import get_email_config_decrypted


class RicettaLaboratorioDialog(tk.Toplevel):
    """Dialog per creare/modificare una ricetta (colore) del laboratorio"""
    
    def __init__(self, parent, db_path, ricetta_data=None, on_success=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.ricetta_data = ricetta_data
        self.on_success = on_success
        
        self.title("Nuova Ricetta" if ricetta_data is None else "Modifica Ricetta")
        self.geometry("700x700")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        self.center_window()
        self.transient(parent)
        self.grab_set()
        
        self.load_references()
        self.create_widgets()
        
        if ricetta_data:
            self.populate_fields()
    
    def center_window(self):
        """Centra la finestra rispetto al parent"""
        self.update_idletasks()
        width = 700
        height = 700
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        
        x = max(0, x)
        y = max(0, y)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def load_references(self):
        """Carica riferimenti e categorie per i combobox"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Carica riferimenti
            cursor.execute("SELECT id, descrizione FROM riferimenti_laboratorio ORDER BY descrizione")
            self.riferimenti = cursor.fetchall()
            
            # Carica categorie
            cursor.execute("SELECT id, descrizione FROM categorie_laboratorio ORDER BY descrizione")
            self.categorie = cursor.fetchall()
            
            conn.close()
        except Exception as e:
            print(f"Errore nel caricamento riferimenti/categorie: {e}")
            self.riferimenti = []
            self.categorie = []
    
    def create_widgets(self):
        """Crea i widget del form"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Data
        tk.Label(main_frame, text="Data*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        self.data_entry = DateEntry(main_frame, date_pattern="dd/mm/yyyy", width=15, font=("Arial", 10))
        self.data_entry.grid(row=0, column=1, sticky="w", pady=10, padx=(10, 0))
        
        # Nome
        tk.Label(main_frame, text="Nome*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=1, column=0, sticky="w", pady=10)
        self.nome_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.nome_entry.grid(row=1, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Codice
        tk.Label(main_frame, text="Codice*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=2, column=0, sticky="w", pady=10)
        self.codice_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.codice_entry.grid(row=2, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Riferimento con pulsante NUOVO
        tk.Label(main_frame, text="Riferimento:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=3, column=0, sticky="w", pady=10)
        riferimento_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        riferimento_frame.grid(row=3, column=1, sticky="ew", pady=10, padx=(10, 0))
        riferimento_frame.grid_columnconfigure(0, weight=1)
        
        self.riferimento_combo = ttk.Combobox(riferimento_frame, font=("Arial", 10), state="readonly", width=30)
        self.riferimento_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Popola il combobox riferimenti
        riferimenti_values = [""] + [f"{r[0]} - {r[1]}" for r in self.riferimenti]
        self.riferimento_combo['values'] = riferimenti_values
        
        # Pulsante NUOVO per riferimento
        btn_nuovo_rif = tk.Button(riferimento_frame, text="NUOVO", 
                                  command=self.nuovo_riferimento,
                                  bg="#4CAF50", fg="white",
                                  font=("Arial", 9, "bold"),
                                  padx=10, pady=2, cursor="hand2")
        btn_nuovo_rif.grid(row=0, column=1, sticky="e")
        
        # Categoria con pulsante NUOVO
        tk.Label(main_frame, text="Categoria:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=4, column=0, sticky="w", pady=10)
        categoria_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        categoria_frame.grid(row=4, column=1, sticky="ew", pady=10, padx=(10, 0))
        categoria_frame.grid_columnconfigure(0, weight=1)
        
        self.categoria_combo = ttk.Combobox(categoria_frame, font=("Arial", 10), state="readonly", width=30)
        self.categoria_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Popola il combobox categorie
        categorie_values = [""] + [f"{c[0]} - {c[1]}" for c in self.categorie]
        self.categoria_combo['values'] = categorie_values
        
        # Pulsante NUOVO per categoria
        btn_nuovo_cat = tk.Button(categoria_frame, text="NUOVO", 
                                  command=self.nuova_categoria,
                                  bg="#4CAF50", fg="white",
                                  font=("Arial", 9, "bold"),
                                  padx=10, pady=2, cursor="hand2")
        btn_nuovo_cat.grid(row=0, column=1, sticky="e")
        
        # Note (campo singola riga)
        tk.Label(main_frame, text="Note:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=5, column=0, sticky="w", pady=10)
        self.note_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.note_entry.grid(row=5, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Sezione Righe Colori
        tk.Label(main_frame, text="Righe Colori:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold"), width=15, anchor="w").grid(row=6, column=0, sticky="nw", pady=(15, 5))
        
        # Frame contenitore con scrollbar per le righe colori
        righe_container = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        righe_container.grid(row=6, column=1, columnspan=2, sticky="nsew", pady=10, padx=(10, 0))
        righe_container.grid_columnconfigure(0, weight=1)
        righe_container.grid_rowconfigure(0, weight=1)
        
        # Canvas per lo scroll
        self.canvas_righe = tk.Canvas(righe_container, bg=Style.BACKGROUND_COLOR, highlightthickness=0)
        scrollbar_righe = ttk.Scrollbar(righe_container, orient="vertical", command=self.canvas_righe.yview)
        
        # Frame scrollabile per le righe
        self.righe_frame = tk.Frame(self.canvas_righe, bg=Style.BACKGROUND_COLOR)
        self.righe_frame.bind(
            "<Configure>",
            lambda e: self.canvas_righe.configure(scrollregion=self.canvas_righe.bbox("all"))
        )
        
        self.canvas_righe.create_window((0, 0), window=self.righe_frame, anchor="nw")
        self.canvas_righe.configure(yscrollcommand=scrollbar_righe.set)
        
        self.canvas_righe.grid(row=0, column=0, sticky="nsew")
        scrollbar_righe.grid(row=0, column=1, sticky="ns")
        
        # Configura la larghezza del canvas window
        def configure_canvas_width(event):
            canvas_width = event.width
            self.canvas_righe.itemconfig(self.canvas_righe.find_all()[0], width=canvas_width)
        
        self.canvas_righe.bind('<Configure>', configure_canvas_width)
        
        # Configurazione colonne del frame righe
        self.righe_frame.grid_columnconfigure(1, weight=1)
        self.righe_frame.grid_columnconfigure(3, weight=1)
        
        # Lista per memorizzare i widget Entry e i frame delle righe
        self.colore_entries = []
        self.quantita_entries = []
        self.righe_frames = []  # Per memorizzare i frame delle righe aggiuntive
        
        # Crea 4 coppie di campi COLORE - QUANTITA predefinite
        for i in range(4):
            self.aggiungi_riga_colore_widget(self.righe_frame, i, is_default=True)
        
        # Frame per pulsanti righe
        righe_buttons_frame = tk.Frame(righe_container, bg=Style.BACKGROUND_COLOR)
        righe_buttons_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")
        
        btn_aggiungi_riga = tk.Button(righe_buttons_frame, text="+ Aggiungi Riga", 
                                      command=lambda: self.aggiungi_riga_colore_widget(self.righe_frame, len(self.colore_entries)),
                                      bg="#4CAF50", fg="white",
                                      font=("Arial", 9, "bold"),
                                      padx=10, pady=2, cursor="hand2")
        btn_aggiungi_riga.pack(side="left", padx=2)
        
        # Bottoni
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20, sticky="e")
        
        btn_annulla = tk.Button(button_frame, text="Annulla", 
                               command=self.destroy,
                               bg="#666666", fg="white",
                               font=("Arial", 10, "bold"),
                               padx=20, pady=5, cursor="hand2")
        btn_annulla.pack(side="right", padx=5)
        
        btn_salva = tk.Button(button_frame, text="Salva", 
                             command=self.salva_ricetta,
                             bg="#4CAF50", fg="white",
                             font=("Arial", 10, "bold"),
                             padx=20, pady=5, cursor="hand2")
        btn_salva.pack(side="right", padx=5)
        
        self.nome_entry.focus()
    
    def populate_fields(self):
        """Popola i campi con i dati esistenti"""
        # Data
        if self.ricetta_data.get('data'):
            try:
                # Converte da dd/mm/yyyy a oggetto datetime
                data_obj = datetime.strptime(self.ricetta_data['data'], "%d/%m/%Y")
                self.data_entry.set_date(data_obj)
            except:
                pass
        
        # Nome
        self.nome_entry.insert(0, self.ricetta_data.get('nome', ''))
        
        # Codice
        self.codice_entry.insert(0, self.ricetta_data.get('codice', ''))
        
        # Riferimento
        riferimento_id = self.ricetta_data.get('riferimento')
        if riferimento_id:
            for r in self.riferimenti:
                if r[0] == riferimento_id:
                    self.riferimento_combo.set(f"{r[0]} - {r[1]}")
                    break
        
        # Categoria
        categoria_id = self.ricetta_data.get('categoria')
        if categoria_id:
            for c in self.categorie:
                if c[0] == categoria_id:
                    self.categoria_combo.set(f"{c[0]} - {c[1]}")
                    break
        
        # Note
        self.note_entry.insert(0, self.ricetta_data.get('note', ''))
        
        # Carica righe colori se in modifica
        if self.ricetta_data.get('id'):
            self.load_righe_colori(self.ricetta_data['id'])
        else:
            # Inizializza lista vuota per nuove ricette
            self.righe_colori = []
    
    def salva_ricetta(self):
        """Salva la ricetta nel database"""
        nome = self.nome_entry.get().strip().upper()  # Converti in maiuscolo
        codice = self.codice_entry.get().strip().upper()  # Converti in maiuscolo
        data = self.data_entry.get_date().strftime("%d/%m/%Y")
        
        if not nome:
            messagebox.showerror("Errore", "Il nome è obbligatorio!")
            return
        
        if not codice:
            messagebox.showerror("Errore", "Il codice è obbligatorio!")
            return
        
        if not data:
            messagebox.showerror("Errore", "La data è obbligatoria!")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Estrai ID riferimento
            riferimento_id = None
            riferimento_selezionato = self.riferimento_combo.get()
            if riferimento_selezionato:
                riferimento_id = int(riferimento_selezionato.split(" - ")[0])
            
            # Estrai ID categoria
            categoria_id = None
            categoria_selezionata = self.categoria_combo.get()
            if categoria_selezionata:
                categoria_id = int(categoria_selezionata.split(" - ")[0])
            
            note = self.note_entry.get().strip().upper()  # Converti in maiuscolo
            
            # Raccogli le righe colori dai campi Entry
            self.collect_righe_colori()
            
            # Valida le quantità delle righe colori
            for riga in self.righe_colori:
                if riga['quantita'] < 0:
                    messagebox.showerror("Errore", "Le quantità devono essere positive o zero!")
                    return
            
            if self.ricetta_data:
                # Modifica
                ricetta_id = self.ricetta_data['id']
                cursor.execute("""
                    UPDATE colori_laboratorio 
                    SET data = ?, codice = ?, nome = ?, riferimento = ?, categoria = ?, note = ?
                    WHERE id = ?
                """, (data, codice, nome, riferimento_id, categoria_id, note, ricetta_id))
            else:
                # Nuova ricetta
                cursor.execute("""
                    INSERT INTO colori_laboratorio (data, codice, nome, riferimento, categoria, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data, codice, nome, riferimento_id, categoria_id, note))
                ricetta_id = cursor.lastrowid
            
            # Salva/aggiorna righe colori
            self.salva_righe_colori(cursor, ricetta_id)
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Ricetta salvata con successo!")
            if self.on_success:
                self.on_success()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la ricetta: {str(e)}")
    
    def nuovo_riferimento(self):
        """Apre un dialog per creare un nuovo riferimento"""
        dialog = tk.Toplevel(self)
        dialog.title("Nuovo Riferimento")
        dialog.geometry("400x150")
        dialog.configure(bg=Style.BACKGROUND_COLOR)
        dialog.transient(self)
        dialog.grab_set()
        
        # Centra la finestra
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"400x150+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(1, weight=1)
        
        tk.Label(main_frame, text="Descrizione*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        desc_entry = tk.Entry(main_frame, font=("Arial", 10))
        desc_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20, sticky="e")
        
        def salva_riferimento():
            descrizione = desc_entry.get().strip().upper()  # Converti in maiuscolo
            if not descrizione:
                messagebox.showerror("Errore", "La descrizione è obbligatoria!")
                return
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO riferimenti_laboratorio (descrizione)
                    VALUES (?)
                """, (descrizione,))
                conn.commit()
                nuovo_id = cursor.lastrowid
                conn.close()
                
                # Aggiorna la lista riferimenti e il combobox
                self.load_references()
                riferimenti_values = [""] + [f"{r[0]} - {r[1]}" for r in self.riferimenti]
                self.riferimento_combo['values'] = riferimenti_values
                self.riferimento_combo.set(f"{nuovo_id} - {descrizione}")
                
                messagebox.showinfo("Successo", "Riferimento creato con successo!")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il riferimento: {str(e)}")
        
        btn_annulla = tk.Button(button_frame, text="Annulla", 
                               command=dialog.destroy,
                               bg="#666666", fg="white",
                               font=("Arial", 10, "bold"),
                               padx=20, pady=5, cursor="hand2")
        btn_annulla.pack(side="right", padx=5)
        
        btn_salva = tk.Button(button_frame, text="Salva", 
                             command=salva_riferimento,
                             bg="#4CAF50", fg="white",
                             font=("Arial", 10, "bold"),
                             padx=20, pady=5, cursor="hand2")
        btn_salva.pack(side="right", padx=5)
        
        desc_entry.focus()
    
    def nuova_categoria(self):
        """Apre un dialog per creare una nuova categoria"""
        dialog = tk.Toplevel(self)
        dialog.title("Nuova Categoria")
        dialog.geometry("600x350")
        dialog.configure(bg=Style.BACKGROUND_COLOR)
        dialog.transient(self)
        dialog.grab_set()
        
        # Centra la finestra
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"600x350+{x}+{y}")
        
        main_frame = tk.Frame(dialog, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Descrizione
        tk.Label(main_frame, text="Descrizione*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        desc_entry = tk.Entry(main_frame, font=("Arial", 10))
        desc_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Codifica
        tk.Label(main_frame, text="Codifica:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=1, column=0, sticky="w", pady=10)
        codifica_entry = tk.Entry(main_frame, font=("Arial", 10))
        codifica_entry.grid(row=1, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Informazioni
        tk.Label(main_frame, text="Informazioni:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="nw").grid(row=2, column=0, sticky="nw", pady=10)
        informazioni_text = tk.Text(main_frame, font=("Arial", 10), height=8, wrap=tk.WORD)
        informazioni_text.grid(row=2, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="e")
        
        def salva_categoria():
            descrizione = desc_entry.get().strip().upper()  # Converti in maiuscolo
            if not descrizione:
                messagebox.showerror("Errore", "La descrizione è obbligatoria!")
                return
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                codifica = codifica_entry.get().strip().upper() if codifica_entry.get().strip() else ""
                informazioni = informazioni_text.get('1.0', tk.END).strip().upper() if informazioni_text.get('1.0', tk.END).strip() else ""
                
                cursor.execute("""
                    INSERT INTO categorie_laboratorio (descrizione, codifica, informazioni)
                    VALUES (?, ?, ?)
                """, (descrizione, codifica, informazioni))
                conn.commit()
                nuovo_id = cursor.lastrowid
                conn.close()
                
                # Aggiorna la lista categorie e il combobox
                self.load_references()
                categorie_values = [""] + [f"{c[0]} - {c[1]}" for c in self.categorie]
                self.categoria_combo['values'] = categorie_values
                self.categoria_combo.set(f"{nuovo_id} - {descrizione}")
                
                messagebox.showinfo("Successo", "Categoria creata con successo!")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare la categoria: {str(e)}")
        
        btn_annulla = tk.Button(button_frame, text="Annulla", 
                               command=dialog.destroy,
                               bg="#666666", fg="white",
                               font=("Arial", 10, "bold"),
                               padx=20, pady=5, cursor="hand2")
        btn_annulla.pack(side="right", padx=5)
        
        btn_salva = tk.Button(button_frame, text="Salva", 
                             command=salva_categoria,
                             bg="#4CAF50", fg="white",
                             font=("Arial", 10, "bold"),
                             padx=20, pady=5, cursor="hand2")
        btn_salva.pack(side="right", padx=5)
        
        desc_entry.focus()
    
    def aggiungi_riga_colore_widget(self, parent_frame, index, is_default=False):
        """Aggiunge una nuova riga COLORE-QUANTITÀ al frame"""
        riga_frame = tk.Frame(parent_frame, bg=Style.BACKGROUND_COLOR)
        riga_frame.grid(row=index, column=0, columnspan=4, sticky="ew", pady=2)
        riga_frame.grid_columnconfigure(1, weight=1)
        riga_frame.grid_columnconfigure(3, weight=1)
        
        # Label COLORE
        label_text = f"Colore {index+1}:" if is_default else f"Colore {index+1}:"
        tk.Label(riga_frame, text=label_text, bg=Style.BACKGROUND_COLOR,
                font=("Arial", 9), width=10, anchor="w").grid(row=0, column=0, sticky="w", pady=2, padx=(0, 5))
        
        # Entry COLORE
        colore_entry = tk.Entry(riga_frame, font=("Arial", 10))
        colore_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(0, 10))
        self.colore_entries.append(colore_entry)
        
        # Label QUANTITA
        tk.Label(riga_frame, text="Quantità:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 9), width=10, anchor="w").grid(row=0, column=2, sticky="w", pady=2, padx=(0, 5))
        
        # Entry QUANTITA
        quantita_entry = tk.Entry(riga_frame, font=("Arial", 10), width=15)
        quantita_entry.grid(row=0, column=3, sticky="w", pady=2)
        self.quantita_entries.append(quantita_entry)
        
        # Pulsante rimuovi (solo per righe aggiuntive, non per le prime 4)
        if not is_default:
            btn_rimuovi = tk.Button(riga_frame, text="✕", 
                                   command=lambda idx=index: self.rimuovi_riga_colore_widget(idx),
                                   bg="#f44336", fg="white",
                                   font=("Arial", 9, "bold"),
                                   width=3, height=1, cursor="hand2")
            btn_rimuovi.grid(row=0, column=4, sticky="e", padx=(5, 0))
            self.righe_frames.append((riga_frame, index))
        
        # Aggiorna lo scroll region
        parent_frame.update_idletasks()
        if hasattr(self, 'canvas_righe'):
            self.canvas_righe.update_idletasks()
            self.canvas_righe.configure(scrollregion=self.canvas_righe.bbox("all"))
    
    def rimuovi_riga_colore_widget(self, index):
        """Rimuove una riga COLORE-QUANTITÀ (solo righe aggiuntive, non le prime 4)"""
        if index < 4:
            # Non permettere la rimozione delle prime 4 righe
            return
        
        # Trova il frame corrispondente
        frame_to_remove = None
        for i, (frame, idx) in enumerate(self.righe_frames):
            if idx == index:
                frame_to_remove = frame
                self.righe_frames.pop(i)
                break
        
        if frame_to_remove:
            # Rimuovi i widget Entry dalla lista
            if index < len(self.colore_entries):
                self.colore_entries.pop(index)
            if index < len(self.quantita_entries):
                self.quantita_entries.pop(index)
            
            # Distruggi il frame
            frame_to_remove.destroy()
            
            # Riorganizza gli indici delle righe rimanenti
            self.riorganizza_righe()
    
    def riorganizza_righe(self):
        """Riorganizza le etichette delle righe dopo una rimozione"""
        # Aggiorna le etichette delle prime 4 righe (sempre presenti)
        for i in range(min(4, len(self.colore_entries))):
            # Le prime 4 righe non hanno pulsante rimuovi, quindi non serve aggiornare le etichette
            pass
        
        # Aggiorna le etichette delle righe aggiuntive
        for i, (frame, old_idx) in enumerate(self.righe_frames):
            # Trova i label nel frame e aggiorna il testo
            for widget in frame.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget("text").startswith("Colore"):
                    widget.config(text=f"Colore {old_idx+1}:")
                    break
            # Aggiorna l'indice nel tuple
            self.righe_frames[i] = (frame, old_idx)
    
    def collect_righe_colori(self):
        """Raccoglie le righe colori dai campi Entry (solo quelle compilate)"""
        self.righe_colori = []
        for i in range(len(self.colore_entries)):
            if i < len(self.colore_entries) and i < len(self.quantita_entries):
                colore = self.colore_entries[i].get().strip().upper()  # Converti in maiuscolo
                quantita_str = self.quantita_entries[i].get().strip()
                
                # Salva solo se entrambi i campi sono compilati
                if colore and quantita_str:
                    try:
                        quantita = float(quantita_str)
                        if quantita >= 0:  # Permetti anche 0
                            self.righe_colori.append({
                                'descrizione': colore,
                                'quantita': round(quantita, 2),
                                'id': None  # Sarà assegnato al salvataggio
                            })
                    except ValueError:
                        # Ignora valori non numerici, l'utente vedrà l'errore al salvataggio
                        pass
    
    def load_righe_colori(self, ricetta_id):
        """Carica le righe colori esistenti per una ricetta e le popola nei campi Entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, descrizione, quantita
                FROM righe_colori_laboratorio
                WHERE colore = ?
                ORDER BY id
            """, (ricetta_id,))
            
            righe = cursor.fetchall()
            conn.close()
            
            self.righe_colori = []
            
            # Popola le prime 4 righe (sempre presenti)
            for i, riga in enumerate(righe[:4]):
                riga_dict = {
                    'id': riga[0],
                    'descrizione': riga[1],
                    'quantita': riga[2]
                }
                self.righe_colori.append(riga_dict)
                
                # Popola i campi Entry esistenti
                if i < len(self.colore_entries):
                    self.colore_entries[i].insert(0, riga[1])
                if i < len(self.quantita_entries):
                    self.quantita_entries[i].insert(0, f"{riga[2]:.2f}")
            
            # Aggiungi righe aggiuntive se ce ne sono più di 4
            for i, riga in enumerate(righe[4:], start=4):
                riga_dict = {
                    'id': riga[0],
                    'descrizione': riga[1],
                    'quantita': riga[2]
                }
                self.righe_colori.append(riga_dict)
                
                # Aggiungi una nuova riga widget
                self.aggiungi_riga_colore_widget(self.righe_frame, i, is_default=False)
                
                # Popola i campi appena creati
                if i < len(self.colore_entries):
                    self.colore_entries[i].insert(0, riga[1])
                if i < len(self.quantita_entries):
                    self.quantita_entries[i].insert(0, f"{riga[2]:.2f}")
                
        except Exception as e:
            print(f"Errore nel caricamento righe colori: {e}")
    
    def salva_righe_colori(self, cursor, ricetta_id):
        """Salva le righe colori nel database"""
        # Prima elimina tutte le righe esistenti per questa ricetta
        cursor.execute("DELETE FROM righe_colori_laboratorio WHERE colore = ?", (ricetta_id,))
        
        # Poi inserisci le nuove righe (solo quelle compilate)
        for riga in self.righe_colori:
            cursor.execute("""
                INSERT INTO righe_colori_laboratorio (descrizione, quantita, colore)
                VALUES (?, ?, ?)
            """, (riga['descrizione'], riga['quantita'], ricetta_id))


class VisualizzaRicettaDialog(tk.Toplevel):
    """Dialog per visualizzare e ricalcolare una ricetta"""
    
    def __init__(self, parent, db_path, ricetta_data):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.ricetta_data = ricetta_data
        self.righe_colori = []
        
        self.title(f"Visualizza Ricetta - {ricetta_data.get('nome', '')}")
        self.geometry("800x700")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        self.center_window()
        self.transient(parent)
        self.grab_set()
        
        self.load_righe_colori()
        self.create_widgets()
    
    def center_window(self):
        """Centra la finestra rispetto al parent"""
        self.update_idletasks()
        width = 800
        height = 700
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        
        x = max(0, x)
        y = max(0, y)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def load_righe_colori(self):
        """Carica le righe colori della ricetta"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, descrizione, quantita
                FROM righe_colori_laboratorio
                WHERE colore = ?
                ORDER BY id
            """, (self.ricetta_data['id'],))
            
            righe = cursor.fetchall()
            conn.close()
            
            self.righe_colori = []
            for riga in righe:
                self.righe_colori.append({
                    'id': riga[0],
                    'descrizione': riga[1],
                    'quantita': riga[2]
                })
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento delle righe colori: {str(e)}")
            self.righe_colori = []
    
    def create_widgets(self):
        """Crea i widget del dialog"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Informazioni ricetta
        info_frame = tk.LabelFrame(main_frame, text="Informazioni Ricetta", 
                                   bg=Style.BACKGROUND_COLOR, fg="#1f396a",
                                   font=("Arial", 11, "bold"), padx=10, pady=10)
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Dettagli ricetta
        tk.Label(info_frame, text="Nome:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(info_frame, text=self.ricetta_data.get('nome', ''), bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(info_frame, text="Codice:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=1, column=0, sticky="w", pady=5)
        tk.Label(info_frame, text=self.ricetta_data.get('codice', ''), bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(info_frame, text="Data:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=2, column=0, sticky="w", pady=5)
        tk.Label(info_frame, text=self.ricetta_data.get('data', ''), bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=2, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(info_frame, text="Riferimento:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=3, column=0, sticky="w", pady=5)
        tk.Label(info_frame, text=self.ricetta_data.get('riferimento_desc', '-'), bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(info_frame, text="Categoria:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=4, column=0, sticky="w", pady=5)
        tk.Label(info_frame, text=self.ricetta_data.get('categoria_desc', '-'), bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        
        if self.ricetta_data.get('note'):
            tk.Label(info_frame, text="Note:", bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10), width=15, anchor="w").grid(row=5, column=0, sticky="w", pady=5)
            tk.Label(info_frame, text=self.ricetta_data.get('note', ''), bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10)).grid(row=5, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Sezione Righe Colori
        righe_frame = tk.LabelFrame(main_frame, text="Righe Colori", 
                                    bg=Style.BACKGROUND_COLOR, fg="#1f396a",
                                    font=("Arial", 11, "bold"), padx=10, pady=10)
        righe_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        righe_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Frame scrollabile per le righe
        canvas = tk.Canvas(righe_frame, bg=Style.BACKGROUND_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(righe_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Style.BACKGROUND_COLOR)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        righe_frame.grid_rowconfigure(0, weight=1)
        righe_frame.grid_columnconfigure(0, weight=1)
        
        # Calcola quantità totale attuale
        quantita_totale_attuale = sum(riga['quantita'] for riga in self.righe_colori)
        
        # Header tabella
        header_frame = tk.Frame(scrollable_frame, bg=Style.BACKGROUND_COLOR)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        tk.Label(header_frame, text="Colore", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold"), width=30, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
        tk.Label(header_frame, text="Quantità Attuale", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold"), width=20, anchor="center").grid(row=0, column=1, sticky="ew")
        tk.Label(header_frame, text="Quantità Ricalcolata", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold"), width=20, anchor="center").grid(row=0, column=2, sticky="ew", padx=(10, 0))
        
        # Lista per memorizzare i label delle quantità ricalcolate
        self.quantita_ricalcolate_labels = []
        
        # Mostra le righe colori
        for i, riga in enumerate(self.righe_colori):
            row_frame = tk.Frame(scrollable_frame, bg=Style.BACKGROUND_COLOR)
            row_frame.grid(row=i+1, column=0, columnspan=3, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(1, weight=1)
            
            tk.Label(row_frame, text=riga['descrizione'], bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10), width=30, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
            tk.Label(row_frame, text=f"{riga['quantita']:.2f}", bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10), width=20, anchor="center").grid(row=0, column=1, sticky="ew")
            quantita_label = tk.Label(row_frame, text="", bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10, "bold"), fg="#4CAF50", width=20, anchor="center")
            quantita_label.grid(row=0, column=2, sticky="ew", padx=(10, 0))
            self.quantita_ricalcolate_labels.append(quantita_label)
        
        # Sezione Ricalcolo
        ricalcolo_frame = tk.LabelFrame(main_frame, text="Ricalcolo Quantità", 
                                       bg=Style.BACKGROUND_COLOR, fg="#1f396a",
                                       font=("Arial", 11, "bold"), padx=10, pady=10)
        ricalcolo_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        ricalcolo_frame.grid_columnconfigure(1, weight=1)
        
        tk.Label(ricalcolo_frame, text="Quantità Totale Attuale:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=20, anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(ricalcolo_frame, text=f"{quantita_totale_attuale:.2f}", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10, "bold"), width=15, anchor="w").grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(ricalcolo_frame, text="Nuova Quantità Totale:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=20, anchor="w").grid(row=1, column=0, sticky="w", pady=5)
        self.nuova_quantita_entry = tk.Entry(ricalcolo_frame, font=("Arial", 10), width=15)
        self.nuova_quantita_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        self.nuova_quantita_entry.insert(0, str(quantita_totale_attuale))
        
        tk.Label(ricalcolo_frame, text="Approssimazione:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=20, anchor="w").grid(row=2, column=0, sticky="w", pady=5)
        self.approssimazione_combo = ttk.Combobox(ricalcolo_frame, font=("Arial", 10), 
                                                   state="readonly", width=12, values=["1", "0.5", "0.1"])
        self.approssimazione_combo.set("0.5")  # Default
        self.approssimazione_combo.grid(row=2, column=1, sticky="w", pady=5, padx=(10, 0))
        
        btn_ricalcola = tk.Button(ricalcolo_frame, text="Ricalcola", 
                                 command=self.ricalcola_quantita,
                                 bg="#2196F3", fg="white",
                                 font=("Arial", 10, "bold"),
                                 padx=20, pady=5, cursor="hand2")
        btn_ricalcola.grid(row=2, column=2, sticky="e", padx=(10, 0))
        
        # Pulsanti
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        
        btn_invia_email = tk.Button(button_frame, text="Invia via Email", 
                                    command=self.invia_email_pdf,
                                    bg="#4CAF50", fg="white",
                                    font=("Arial", 10, "bold"),
                                    padx=20, pady=5, cursor="hand2")
        btn_invia_email.pack(side="right", padx=5)
        
        btn_chiudi = tk.Button(button_frame, text="Chiudi", 
                              command=self.destroy,
                              bg="#666666", fg="white",
                              font=("Arial", 10, "bold"),
                              padx=20, pady=5, cursor="hand2")
        btn_chiudi.pack(side="right", padx=5)
        
        # Esegui ricalcolo iniziale
        self.ricalcola_quantita()
    
    def ricalcola_quantita(self):
        """Ricalcola le quantità proporzionalmente con approssimazione"""
        try:
            nuova_quantita_totale = float(self.nuova_quantita_entry.get().strip())
            if nuova_quantita_totale < 0:
                messagebox.showerror("Errore", "La quantità deve essere positiva!")
                return
            
            # Ottieni il valore di approssimazione
            approssimazione = float(self.approssimazione_combo.get())
            
            # Calcola quantità totale attuale
            quantita_totale_attuale = sum(riga['quantita'] for riga in self.righe_colori)
            
            if quantita_totale_attuale == 0:
                messagebox.showwarning("Attenzione", "La quantità totale attuale è zero. Impossibile ricalcolare.")
                return
            
            # Calcola il fattore di proporzione
            fattore = nuova_quantita_totale / quantita_totale_attuale
            
            # Aggiorna i label con le nuove quantità (approssimate)
            for i, riga in enumerate(self.righe_colori):
                nuova_quantita = riga['quantita'] * fattore
                # Applica approssimazione: arrotonda al multiplo più vicino del valore di approssimazione
                nuova_quantita_arrotondata = round(nuova_quantita / approssimazione) * approssimazione
                
                # Determina il numero di decimali da mostrare in base all'approssimazione
                if approssimazione == 1:
                    decimali = 0
                elif approssimazione == 0.5:
                    decimali = 1
                else:  # 0.1
                    decimali = 1
                
                self.quantita_ricalcolate_labels[i].config(text=f"{nuova_quantita_arrotondata:.{decimali}f}")
                
        except ValueError:
            messagebox.showerror("Errore", "Inserisci un valore numerico valido!")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel ricalcolo: {str(e)}")
    
    def genera_pdf_ricetta(self):
        """Genera il PDF della ricetta ricalcolata"""
        try:
            # Ottieni le quantità ricalcolate
            approssimazione = float(self.approssimazione_combo.get())
            nuova_quantita_totale = float(self.nuova_quantita_entry.get().strip())
            quantita_totale_attuale = sum(riga['quantita'] for riga in self.righe_colori)
            fattore = nuova_quantita_totale / quantita_totale_attuale if quantita_totale_attuale > 0 else 1
            
            # Crea directory per PDF se non esiste
            outdir = Path('report_pdf')
            outdir.mkdir(exist_ok=True)
            
            # Nome file
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_ricetta = self.ricetta_data.get('nome', 'Ricetta').replace(' ', '_')
            filename = outdir / f"Ricetta_{nome_ricetta}_{date_str}.pdf"
            
            # Crea PDF
            c = canvas.Canvas(str(filename), pagesize=A4)
            width, height = A4
            x_margin = 40
            y = height - 40
            
            # Intestazione
            c.setFont('Helvetica-Bold', 16)
            c.drawString(x_margin, y, "RICETTA LABORATORIO")
            y -= 25
            
            c.setFont('Helvetica', 10)
            c.drawString(x_margin, y, f"Nome: {self.ricetta_data.get('nome', '')}")
            y -= 15
            c.drawString(x_margin, y, f"Codice: {self.ricetta_data.get('codice', '')}")
            y -= 15
            c.drawString(x_margin, y, f"Data: {self.ricetta_data.get('data', '')}")
            y -= 15
            c.drawString(x_margin, y, f"Riferimento: {self.ricetta_data.get('riferimento_desc', '-')}")
            y -= 15
            c.drawString(x_margin, y, f"Categoria: {self.ricetta_data.get('categoria_desc', '-')}")
            y -= 15
            if self.ricetta_data.get('note'):
                c.drawString(x_margin, y, f"Note: {self.ricetta_data.get('note', '')}")
                y -= 15
            y -= 10
            
            # Linea separatrice
            c.line(x_margin, y, width - x_margin, y)
            y -= 20
            
            # Informazioni ricalcolo
            c.setFont('Helvetica-Bold', 11)
            c.drawString(x_margin, y, "RICETTA RICALCOLATA")
            y -= 15
            c.setFont('Helvetica', 10)
            c.drawString(x_margin, y, f"Quantità Totale Originale: {quantita_totale_attuale:.2f}")
            y -= 15
            c.drawString(x_margin, y, f"Quantità Totale Ricalcolata: {nuova_quantita_totale:.2f}")
            y -= 15
            c.drawString(x_margin, y, f"Approssimazione: {approssimazione}")
            y -= 15
            c.drawString(x_margin, y, f"Data generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 20
            
            # Linea separatrice
            c.line(x_margin, y, width - x_margin, y)
            y -= 20
            
            # Intestazione colonne
            c.setFont('Helvetica-Bold', 10)
            c.drawString(x_margin, y, "Colore")
            c.drawString(x_margin + 250, y, "Quantità Originale")
            c.drawString(x_margin + 400, y, "Quantità Ricalcolata")
            y -= 15
            c.line(x_margin, y, width - x_margin, y)
            y -= 10
            
            # Righe colori
            c.setFont('Helvetica', 9)
            for riga in self.righe_colori:
                if y < 80:
                    c.showPage()
                    y = height - 40
                
                nuova_quantita = riga['quantita'] * fattore
                nuova_quantita_arrotondata = round(nuova_quantita / approssimazione) * approssimazione
                
                # Determina decimali
                if approssimazione == 1:
                    decimali = 0
                elif approssimazione == 0.5:
                    decimali = 1
                else:
                    decimali = 1
                
                c.drawString(x_margin, y, riga['descrizione'][:40])
                c.drawString(x_margin + 250, y, f"{riga['quantita']:.2f}")
                c.drawString(x_margin + 400, y, f"{nuova_quantita_arrotondata:.{decimali}f}")
                y -= 15
            
            c.save()
            return filename
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella generazione del PDF: {str(e)}")
            return None
    
    def invia_email_pdf(self):
        """Invia il PDF della ricetta ricalcolata via email"""
        try:
            # Carica configurazione email dal database
            try:
                email_config = get_email_config_decrypted()
                smtp_server = email_config.get('smtp_server', '')
                smtp_port = email_config.get('smtp_port', 587)
                email_mittente = email_config.get('email_mittente', '')
                email_password = email_config.get('email_password', '')
                email_destinatario = email_config.get('email_destinatario', '')
            except Exception as e:
                messagebox.showerror("Errore", f"Configurazione email non trovata nel database. Configura le impostazioni email nella finestra di configurazione.\n\nErrore: {str(e)}")
                return
            
            if not smtp_server or not email_mittente or not email_password:
                messagebox.showerror("Errore", "Configurazione email incompleta. Verifica le impostazioni nella finestra di configurazione.")
                return
            
            if not email_destinatario:
                email_destinatario = email_mittente  # Fallback al mittente
            
            # Chiedi conferma email destinatario
            dialog = tk.Toplevel(self)
            dialog.title("Invia Email")
            dialog.geometry("400x150")
            dialog.configure(bg=Style.BACKGROUND_COLOR)
            dialog.transient(self)
            dialog.grab_set()
            
            # Centra la finestra
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (150 // 2)
            dialog.geometry(f"400x150+{x}+{y}")
            
            main_frame = tk.Frame(dialog, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            main_frame.grid_columnconfigure(1, weight=1)
            
            tk.Label(main_frame, text="Email Destinatario:", bg=Style.BACKGROUND_COLOR,
                    font=("Arial", 10), width=20, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
            email_entry = tk.Entry(main_frame, font=("Arial", 10), width=30)
            email_entry.insert(0, email_destinatario)
            email_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
            
            button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
            button_frame.grid(row=1, column=0, columnspan=2, pady=20, sticky="e")
            
            def invia():
                destinatario = email_entry.get().strip()
                if not destinatario:
                    messagebox.showerror("Errore", "Inserisci un indirizzo email destinatario!")
                    return
                
                dialog.destroy()
                
                # Genera PDF
                messagebox.showinfo("Info", "Generazione PDF in corso...")
                pdf_path = self.genera_pdf_ricetta()
                
                if not pdf_path:
                    return
                
                try:
                    # Crea messaggio email
                    msg = MIMEMultipart()
                    msg['From'] = email_mittente
                    msg['To'] = destinatario
                    msg['Subject'] = self.ricetta_data.get('codice', '')
                    
                    body = f"""
Ricetta: {self.ricetta_data.get('nome', '')}
Codice: {self.ricetta_data.get('codice', '')}
Data: {self.ricetta_data.get('data', '')}

Quantità Totale Ricalcolata: {self.nuova_quantita_entry.get()}
Approssimazione: {self.approssimazione_combo.get()}

In allegato il PDF con i dettagli della ricetta ricalcolata.
"""
                    msg.attach(MIMEText(body, 'plain'))
                    
                    # Allega PDF
                    with open(pdf_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {Path(pdf_path).name}'
                    )
                    msg.attach(part)
                    
                    # Invia email
                    messagebox.showinfo("Info", "Invio email in corso...")
                    server = smtplib.SMTP(smtp_server, int(smtp_port))
                    server.starttls()
                    server.login(email_mittente, email_password)
                    text = msg.as_string()
                    server.sendmail(email_mittente, destinatario, text)
                    server.quit()
                    
                    messagebox.showinfo("Successo", f"Email inviata con successo a {destinatario}!")
                    
                except Exception as e:
                    messagebox.showerror("Errore", f"Errore nell'invio dell'email: {str(e)}")
            
            btn_annulla = tk.Button(button_frame, text="Annulla", 
                                   command=dialog.destroy,
                                   bg="#666666", fg="white",
                                   font=("Arial", 10, "bold"),
                                   padx=20, pady=5, cursor="hand2")
            btn_annulla.pack(side="right", padx=5)
            
            btn_invia = tk.Button(button_frame, text="Invia", 
                                 command=invia,
                                 bg="#4CAF50", fg="white",
                                 font=("Arial", 10, "bold"),
                                 padx=20, pady=5, cursor="hand2")
            btn_invia.pack(side="right", padx=5)
            
            email_entry.focus()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella configurazione email: {str(e)}")


class RicetteLaboratorioPage(tk.Frame):
    """Pagina per la gestione delle ricette (colori) del laboratorio"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.db_path = self.get_db_path()
        
        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return
        
        self.original_data = []
        
        self.configure_style()
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        self.create_button_bar()
        self.create_table()
        self.load_data()
    
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
    
    def create_button_bar(self):
        """Crea la barra dei pulsanti"""
        button_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(Style.CONTENT_PADDING, 10))
        
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
            ("nuovo", "Nuovo", self.nuova_ricetta, "#4CAF50"),
            ("modifica", "Modifica", self.modifica_ricetta, "#FF9800"),
            ("cancella", "Cancella", self.cancella_ricetta, "#f44336"),
            ("cronologia", "Visualizza", self.visualizza_ricetta, "#2196F3"),
            ("info", "Categorie", self.apri_categorie, "#9C27B0")
        ]
        
        for icon, text, cmd, color in buttons:
            frame = tk.Frame(button_frame, bg=Style.BACKGROUND_COLOR)
            frame.pack(side="left", padx=(0, 25))
            add_button(frame, icon, text, cmd, color)
        
        # Contatore
        self.counter_label = tk.Label(
            button_frame,
            text="",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 10)
        )
        self.counter_label.pack(side="right", padx=(20, 0))
    
    def create_table(self):
        """Crea la tabella delle ricette"""
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        columns = ("DATA", "CODICE", "CATEGORIA", "COLORE", "RIFERIMENTO", "NOTE")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("DATA", width=120, anchor="center")
        self.tree.column("CODICE", width=150, anchor="w")
        self.tree.column("CATEGORIA", width=200, anchor="w")
        self.tree.column("COLORE", width=200, anchor="w")
        self.tree.column("RIFERIMENTO", width=200, anchor="w")
        self.tree.column("NOTE", width=300, anchor="w")
        
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
    
    def ensure_tables_exist(self):
        """Verifica e crea le tabelle se non esistono"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica e crea riferimenti_laboratorio (senza codifica)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riferimenti_laboratorio'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS riferimenti_laboratorio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        descrizione TEXT NOT NULL
                    )
                """)
            else:
                # Verifica se esiste la colonna codifica e rimuovila se presente
                cursor.execute("PRAGMA table_info(riferimenti_laboratorio)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'codifica' in columns:
                    # SQLite non supporta DROP COLUMN direttamente, quindi ricreiamo la tabella
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS riferimenti_laboratorio_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            descrizione TEXT NOT NULL
                        )
                    """)
                    cursor.execute("INSERT INTO riferimenti_laboratorio_new (id, descrizione) SELECT id, descrizione FROM riferimenti_laboratorio")
                    cursor.execute("DROP TABLE riferimenti_laboratorio")
                    cursor.execute("ALTER TABLE riferimenti_laboratorio_new RENAME TO riferimenti_laboratorio")
            
            # Verifica e crea righe_colori_laboratorio
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='righe_colori_laboratorio'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS righe_colori_laboratorio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        descrizione TEXT NOT NULL,
                        quantita REAL NOT NULL,
                        colore INTEGER NOT NULL,
                        FOREIGN KEY (colore) REFERENCES colori_laboratorio(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_righe_colori_laboratorio_colore ON righe_colori_laboratorio(colore)")
            
            # Verifica se la tabella colori_laboratorio esiste
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='colori_laboratorio'
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS colori_laboratorio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT NOT NULL,
                        codice TEXT NOT NULL,
                        nome TEXT NOT NULL,
                        riferimento INTEGER,
                        categoria INTEGER,
                        note TEXT,
                        FOREIGN KEY (riferimento) REFERENCES riferimenti_laboratorio(id),
                        FOREIGN KEY (categoria) REFERENCES categorie_laboratorio(id)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_categoria ON colori_laboratorio(categoria)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_riferimento ON colori_laboratorio(riferimento)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_colori_laboratorio_data ON colori_laboratorio(data)")
            else:
                # Verifica se il campo codice esiste, altrimenti lo aggiunge
                cursor.execute("PRAGMA table_info(colori_laboratorio)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'codice' not in columns:
                    cursor.execute("ALTER TABLE colori_laboratorio ADD COLUMN codice TEXT NOT NULL DEFAULT ''")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Errore nella creazione delle tabelle: {e}")
            return False
    
    def load_data(self):
        """Carica i dati dal database"""
        # Assicurati che le tabelle esistano
        if not self.ensure_tables_exist():
            messagebox.showerror("Errore", 
                "Impossibile creare le tabelle necessarie.\n"
                "Chiudi l'applicazione e riprova.")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    c.id,
                    c.data,
                    c.codice,
                    c.nome,
                    c.riferimento,
                    c.categoria,
                    c.note,
                    r.descrizione AS riferimento_desc,
                    cat.descrizione AS categoria_desc
                FROM colori_laboratorio c
                LEFT JOIN riferimenti_laboratorio r ON c.riferimento = r.id
                LEFT JOIN categorie_laboratorio cat ON c.categoria = cat.id
                ORDER BY c.data DESC, c.id DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            self.original_data = []
            for row in rows:
                self.original_data.append({
                    'id': row['id'],
                    'data': row['data'],
                    'codice': row['codice'],
                    'nome': row['nome'],
                    'riferimento': row['riferimento'],
                    'riferimento_desc': row['riferimento_desc'] or '',
                    'categoria': row['categoria'],
                    'categoria_desc': row['categoria_desc'] or '',
                    'note': row['note'] or ''
                })
            
            self.update_table_display()
            
        except sqlite3.OperationalError as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei dati: {str(e)}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei dati: {str(e)}")
    
    def update_table_display(self):
        """Aggiorna la visualizzazione della tabella"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, row in enumerate(self.original_data):
            # Tronca le note se troppo lunghe
            note_display = row['note']
            if len(note_display) > 50:
                note_display = note_display[:50] + "..."
            
            values = [
                row['data'],
                row['codice'],
                row['categoria_desc'] if row['categoria_desc'] else '-',
                row['nome'],
                row['riferimento_desc'] if row['riferimento_desc'] else '-',
                note_display
            ]
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", tk.END, values=values, tags=(tag, f"id_{row['id']}"))
        
        self.counter_label.config(text=f"{len(self.original_data)} ricette visualizzate")
    
    def apri_categorie(self):
        """Apre una finestra con la pagina categorie"""
        try:
            from laboratorio_categorie_page import CategorieLaboratorioPage
            
            # Crea una finestra Toplevel per le categorie
            categorie_window = tk.Toplevel(self.winfo_toplevel())
            categorie_window.title("Categorie Laboratorio")
            categorie_window.geometry("1000x700")
            categorie_window.configure(bg=Style.BACKGROUND_COLOR)
            
            # Centra la finestra
            categorie_window.update_idletasks()
            x = (categorie_window.winfo_screenwidth() // 2) - (1000 // 2)
            y = (categorie_window.winfo_screenheight() // 2) - (700 // 2)
            categorie_window.geometry(f"1000x700+{x}+{y}")
            
            # Crea la pagina categorie nella finestra
            categorie_page = CategorieLaboratorioPage(categorie_window)
            categorie_page.pack(fill='both', expand=True)
            
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire la pagina categorie: {e}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nell'apertura della pagina categorie: {str(e)}")
    
    def nuova_ricetta(self):
        """Apre il dialog per creare una nuova ricetta"""
        RicettaLaboratorioDialog(self, self.db_path, on_success=self.load_data)
    
    def modifica_ricetta(self):
        """Apre il dialog per modificare la ricetta selezionata"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona una ricetta da modificare.")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Attenzione", "Seleziona una sola ricetta.")
            return
        
        # Recupera l'ID dalla ricetta selezionata
        tags = self.tree.item(selected[0], "tags")
        ricetta_id = None
        for tag in tags:
            if tag.startswith("id_"):
                ricetta_id = int(tag[3:])
                break
        
        if not ricetta_id:
            messagebox.showerror("Errore", "Impossibile identificare la ricetta.")
            return
        
        # Trova i dati della ricetta
        ricetta_data = None
        for row in self.original_data:
            if row['id'] == ricetta_id:
                ricetta_data = row
                break
        
        if ricetta_data:
            RicettaLaboratorioDialog(self, self.db_path, ricetta_data=ricetta_data, on_success=self.load_data)
    
    def visualizza_ricetta(self):
        """Apre un dialog per visualizzare e ricalcolare la ricetta"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona una ricetta da visualizzare.")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Attenzione", "Seleziona una sola ricetta.")
            return
        
        # Recupera l'ID dalla ricetta selezionata
        tags = self.tree.item(selected[0], "tags")
        ricetta_id = None
        for tag in tags:
            if tag.startswith("id_"):
                ricetta_id = int(tag[3:])
                break
        
        if not ricetta_id:
            messagebox.showerror("Errore", "Impossibile identificare la ricetta.")
            return
        
        # Trova i dati della ricetta
        ricetta_data = None
        for row in self.original_data:
            if row['id'] == ricetta_id:
                ricetta_data = row
                break
        
        if ricetta_data:
            VisualizzaRicettaDialog(self, self.db_path, ricetta_data)
    
    def cancella_ricetta(self):
        """Elimina la ricetta selezionata"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona una ricetta da eliminare.")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Attenzione", "Seleziona una sola ricetta.")
            return
        
        # Recupera l'ID
        tags = self.tree.item(selected[0], "tags")
        ricetta_id = None
        for tag in tags:
            if tag.startswith("id_"):
                ricetta_id = int(tag[3:])
                break
        
        if not ricetta_id:
            messagebox.showerror("Errore", "Impossibile identificare la ricetta.")
            return
        
        # Trova il nome della ricetta
        ricetta_nome = ""
        for row in self.original_data:
            if row['id'] == ricetta_id:
                ricetta_nome = row['nome']
                break
        
        # Conferma eliminazione
        if not messagebox.askyesno("Conferma", 
            f"Sei sicuro di voler eliminare la ricetta '{ricetta_nome}'?\n\n"
            "Questa operazione è irreversibile."):
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM colori_laboratorio WHERE id = ?", (ricetta_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Ricetta eliminata con successo!")
            self.load_data()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'eliminazione: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Ricette Laboratorio")
    root.geometry("1200x700")
    app = RicetteLaboratorioPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
