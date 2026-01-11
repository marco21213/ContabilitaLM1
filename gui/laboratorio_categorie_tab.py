"""
Tab Categorie - Gestione categorie ricette per il laboratorio
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style


class CategoriaDialog(tk.Toplevel):
    """Dialog per creare/modificare una categoria"""
    
    def __init__(self, parent, db_path, categoria_data=None, on_success=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.categoria_data = categoria_data
        self.on_success = on_success
        
        self.title("Nuova Categoria" if categoria_data is None else "Modifica Categoria")
        self.geometry("500x400")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        self.center_window()
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        if categoria_data:
            self.populate_fields()
    
    def center_window(self):
        """Centra la finestra rispetto al parent"""
        self.update_idletasks()
        width = 500
        height = 400
        
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
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Nome
        tk.Label(main_frame, text="Nome*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        self.nome_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.nome_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Descrizione
        tk.Label(main_frame, text="Descrizione:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=1, column=0, sticky="nw", pady=10)
        self.descrizione_text = tk.Text(main_frame, font=("Arial", 10), height=5, wrap=tk.WORD)
        self.descrizione_text.grid(row=1, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Colore (per visualizzazione)
        tk.Label(main_frame, text="Colore:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=2, column=0, sticky="w", pady=10)
        self.colore_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.colore_entry.grid(row=2, column=1, sticky="ew", pady=10, padx=(10, 0))
        tk.Label(main_frame, text="(es. #FF5733 o nome colore)", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 8), fg="#666666").grid(row=3, column=1, sticky="w", padx=(10, 0))
        
        # Attivo
        self.attivo_var = tk.BooleanVar(value=True)
        tk.Checkbutton(main_frame, text="Attiva", variable=self.attivo_var,
                      bg=Style.BACKGROUND_COLOR, font=("Arial", 10)).grid(row=4, column=1, sticky="w", pady=10, padx=(10, 0))
        
        # Bottoni
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20, sticky="e")
        
        btn_annulla = tk.Button(button_frame, text="Annulla", 
                               command=self.destroy,
                               bg="#666666", fg="white",
                               font=("Arial", 10, "bold"),
                               padx=20, pady=5, cursor="hand2")
        btn_annulla.pack(side="right", padx=5)
        
        btn_salva = tk.Button(button_frame, text="Salva", 
                             command=self.salva_categoria,
                             bg="#4CAF50", fg="white",
                             font=("Arial", 10, "bold"),
                             padx=20, pady=5, cursor="hand2")
        btn_salva.pack(side="right", padx=5)
        
        self.nome_entry.focus()
    
    def populate_fields(self):
        """Popola i campi con i dati esistenti"""
        self.nome_entry.insert(0, self.categoria_data.get('nome', ''))
        self.descrizione_text.insert('1.0', self.categoria_data.get('descrizione', ''))
        self.colore_entry.insert(0, self.categoria_data.get('colore', ''))
        self.attivo_var.set(self.categoria_data.get('attivo', True))
    
    def salva_categoria(self):
        """Salva la categoria nel database"""
        nome = self.nome_entry.get().strip()
        
        if not nome:
            messagebox.showerror("Errore", "Il nome è obbligatorio!")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            descrizione = self.descrizione_text.get('1.0', tk.END).strip()
            colore = self.colore_entry.get().strip()
            attivo = 1 if self.attivo_var.get() else 0
            
            if self.categoria_data:
                # Modifica
                categoria_id = self.categoria_data['id']
                cursor.execute("""
                    UPDATE categorie_ricette 
                    SET nome = ?, descrizione = ?, colore = ?, attivo = ?, data_modifica = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (nome, descrizione, colore, attivo, categoria_id))
            else:
                # Nuova categoria
                cursor.execute("""
                    INSERT INTO categorie_ricette (nome, descrizione, colore, attivo)
                    VALUES (?, ?, ?, ?)
                """, (nome, descrizione, colore, attivo))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Categoria salvata con successo!")
            if self.on_success:
                self.on_success()
            self.destroy()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Errore", "Una categoria con questo nome esiste già!")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la categoria: {str(e)}")


class CategorieTab(tk.Frame):
    """Tab per la gestione delle categorie"""
    
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        
        self.original_data = []
        self.active_filters = {
            'nome': '',
            'attivo': ''
        }
        
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.create_ui()
        self.load_data()
    
    def create_ui(self):
        """Crea l'interfaccia utente"""
        # Barra pulsanti
        button_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(10, 10))
        
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
            ("nuovo", "Nuovo", self.nuova_categoria, "#4CAF50"),
            ("modifica", "Modifica", self.modifica_categoria, "#FF9800"),
            ("cancella", "Cancella", self.cancella_categoria, "#f44336"),
            ("filtri", "Cancella Filtri", self.clear_filters, "#607D8B")
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
        
        # Tabella
        self.create_table()
    
    def create_table(self):
        """Crea la tabella delle categorie"""
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        columns = ("NOME", "DESCRIZIONE", "COLORE", "STATO")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("NOME", width=200, anchor="w")
        self.tree.column("DESCRIZIONE", width=300, anchor="w")
        self.tree.column("COLORE", width=100, anchor="center")
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
    
    def load_data(self):
        """Carica i dati dal database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, nome, descrizione, colore, attivo, 
                       data_creazione, data_modifica
                FROM categorie_ricette
                ORDER BY nome
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            self.original_data = []
            for row in rows:
                self.original_data.append({
                    'id': row['id'],
                    'nome': row['nome'],
                    'descrizione': row['descrizione'] or '',
                    'colore': row['colore'] or '',
                    'attivo': bool(row['attivo']),
                    'data_creazione': row['data_creazione'],
                    'data_modifica': row['data_modifica']
                })
            
            self.apply_filters()
            
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                messagebox.showwarning("Attenzione", 
                    "Le tabelle del laboratorio non sono state inizializzate.\n"
                    "Esegui lo script: scripts/init_laboratorio_database.py")
            else:
                messagebox.showerror("Errore", f"Errore nel caricamento dei dati: {str(e)}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei dati: {str(e)}")
    
    def apply_filters(self):
        """Applica i filtri ai dati"""
        filtered_data = []
        
        for row in self.original_data:
            match = True
            
            # Filtro nome
            if self.active_filters['nome']:
                if self.active_filters['nome'].lower() not in row['nome'].lower():
                    match = False
            
            # Filtro attivo
            if self.active_filters['attivo']:
                if self.active_filters['attivo'] == 'Attive' and not row['attivo']:
                    match = False
                elif self.active_filters['attivo'] == 'Disattive' and row['attivo']:
                    match = False
            
            if match:
                filtered_data.append(row)
        
        self.update_table_display(filtered_data)
    
    def update_table_display(self, data):
        """Aggiorna la visualizzazione della tabella"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for i, row in enumerate(data):
            stato = "Attiva" if row['attivo'] else "Disattiva"
            colore_display = row['colore'] if row['colore'] else "-"
            descrizione_display = row['descrizione'][:50] + "..." if len(row['descrizione']) > 50 else row['descrizione']
            
            values = [row['nome'], descrizione_display, colore_display, stato]
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", tk.END, values=values, tags=(tag, f"id_{row['id']}"))
        
        self.counter_label.config(text=f"{len(data)} categorie visualizzate")
    
    def nuova_categoria(self):
        """Apre il dialog per creare una nuova categoria"""
        CategoriaDialog(self, self.db_path, on_success=self.load_data)
    
    def modifica_categoria(self):
        """Apre il dialog per modificare la categoria selezionata"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona una categoria da modificare.")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Attenzione", "Seleziona una sola categoria.")
            return
        
        # Recupera l'ID dalla categoria selezionata
        tags = self.tree.item(selected[0], "tags")
        categoria_id = None
        for tag in tags:
            if tag.startswith("id_"):
                categoria_id = int(tag[3:])
                break
        
        if not categoria_id:
            messagebox.showerror("Errore", "Impossibile identificare la categoria.")
            return
        
        # Trova i dati della categoria
        categoria_data = None
        for row in self.original_data:
            if row['id'] == categoria_id:
                categoria_data = row
                break
        
        if categoria_data:
            CategoriaDialog(self, self.db_path, categoria_data=categoria_data, on_success=self.load_data)
    
    def cancella_categoria(self):
        """Elimina la categoria selezionata"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona una categoria da eliminare.")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Attenzione", "Seleziona una sola categoria.")
            return
        
        # Recupera l'ID
        tags = self.tree.item(selected[0], "tags")
        categoria_id = None
        for tag in tags:
            if tag.startswith("id_"):
                categoria_id = int(tag[3:])
                break
        
        if not categoria_id:
            messagebox.showerror("Errore", "Impossibile identificare la categoria.")
            return
        
        # Trova il nome della categoria
        categoria_nome = ""
        for row in self.original_data:
            if row['id'] == categoria_id:
                categoria_nome = row['nome']
                break
        
        # Conferma eliminazione
        if not messagebox.askyesno("Conferma", 
            f"Sei sicuro di voler eliminare la categoria '{categoria_nome}'?\n\n"
            "Questa operazione è irreversibile."):
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se ci sono ricette associate
            cursor.execute("SELECT COUNT(*) FROM ricette WHERE categoria_id = ?", (categoria_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                if not messagebox.askyesno("Attenzione",
                    f"Ci sono {count} ricetta/e associate a questa categoria.\n"
                    "Vuoi comunque eliminarla? (Le ricette non verranno eliminate, ma perderanno la categoria)"):
                    conn.close()
                    return
            
            cursor.execute("DELETE FROM categorie_ricette WHERE id = ?", (categoria_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Categoria eliminata con successo!")
            self.load_data()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'eliminazione: {str(e)}")
    
    def clear_filters(self):
        """Cancella tutti i filtri"""
        self.active_filters = {'nome': '', 'attivo': ''}
        self.apply_filters()
        messagebox.showinfo("Filtri", "Tutti i filtri sono stati rimossi.")
