"""
Pagina Categorie Laboratorio - Gestione categorie del laboratorio
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import configparser
import os
from datetime import datetime
from PIL import Image, ImageTk

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style


class CategoriaLaboratorioDialog(tk.Toplevel):
    """Dialog per creare/modificare una categoria del laboratorio"""
    
    def __init__(self, parent, db_path, categoria_data=None, on_success=None):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.categoria_data = categoria_data
        self.on_success = on_success
        
        self.title("Nuova Categoria" if categoria_data is None else "Modifica Categoria")
        self.geometry("600x500")
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
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Descrizione
        tk.Label(main_frame, text="Descrizione*:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        self.descrizione_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.descrizione_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Codifica
        tk.Label(main_frame, text="Codifica:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="w").grid(row=1, column=0, sticky="w", pady=10)
        self.codifica_entry = tk.Entry(main_frame, font=("Arial", 10))
        self.codifica_entry.grid(row=1, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Informazioni
        tk.Label(main_frame, text="Informazioni:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10), width=15, anchor="nw").grid(row=2, column=0, sticky="nw", pady=10)
        self.informazioni_text = tk.Text(main_frame, font=("Arial", 10), height=10, wrap=tk.WORD)
        self.informazioni_text.grid(row=2, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Scrollbar per il campo informazioni
        scrollbar_info = ttk.Scrollbar(main_frame, orient="vertical", command=self.informazioni_text.yview)
        scrollbar_info.grid(row=2, column=2, sticky="ns", pady=10)
        self.informazioni_text.configure(yscrollcommand=scrollbar_info.set)
        
        # Bottoni
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20, sticky="e")
        
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
        
        self.descrizione_entry.focus()
    
    def populate_fields(self):
        """Popola i campi con i dati esistenti"""
        self.descrizione_entry.insert(0, self.categoria_data.get('descrizione', ''))
        self.codifica_entry.insert(0, self.categoria_data.get('codifica', ''))
        self.informazioni_text.insert('1.0', self.categoria_data.get('informazioni', ''))
    
    def salva_categoria(self):
        """Salva la categoria nel database"""
        descrizione = self.descrizione_entry.get().strip()
        
        if not descrizione:
            messagebox.showerror("Errore", "La descrizione è obbligatoria!")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            codifica = self.codifica_entry.get().strip()
            informazioni = self.informazioni_text.get('1.0', tk.END).strip()
            
            if self.categoria_data:
                # Modifica
                categoria_id = self.categoria_data['id']
                cursor.execute("""
                    UPDATE categorie_laboratorio 
                    SET descrizione = ?, codifica = ?, informazioni = ?
                    WHERE id = ?
                """, (descrizione, codifica, informazioni, categoria_id))
            else:
                # Nuova categoria
                cursor.execute("""
                    INSERT INTO categorie_laboratorio (descrizione, codifica, informazioni)
                    VALUES (?, ?, ?)
                """, (descrizione, codifica, informazioni))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Categoria salvata con successo!")
            if self.on_success:
                self.on_success()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare la categoria: {str(e)}")


class CategorieLaboratorioPage(tk.Frame):
    """Pagina per la gestione delle categorie del laboratorio"""
    
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
            ("nuovo", "Nuovo", self.nuova_categoria, "#4CAF50"),
            ("modifica", "Modifica", self.modifica_categoria, "#FF9800"),
            ("cancella", "Cancella", self.cancella_categoria, "#f44336")
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
        """Crea la tabella delle categorie"""
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        columns = ("ID", "DESCRIZIONE", "CODIFICA", "INFORMAZIONI")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("ID", width=80, anchor="center")
        self.tree.column("DESCRIZIONE", width=250, anchor="w")
        self.tree.column("CODIFICA", width=150, anchor="w")
        self.tree.column("INFORMAZIONI", width=400, anchor="w")
        
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
    
    def ensure_table_exists(self):
        """Verifica e crea la tabella se non esiste"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se la tabella esiste
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='categorie_laboratorio'
            """)
            
            if not cursor.fetchone():
                # Crea la tabella se non esiste
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categorie_laboratorio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        descrizione TEXT NOT NULL,
                        codifica TEXT,
                        informazioni TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_categorie_laboratorio_codifica ON categorie_laboratorio(codifica)")
                conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"Errore nella creazione della tabella: {e}")
            return False
    
    def load_data(self):
        """Carica i dati dal database"""
        # Assicurati che la tabella esista
        if not self.ensure_table_exists():
            messagebox.showerror("Errore", 
                "Impossibile creare la tabella categorie_laboratorio.\n"
                "Chiudi l'applicazione e riprova.")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, descrizione, codifica, informazioni
                FROM categorie_laboratorio
                ORDER BY id DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            self.original_data = []
            for row in rows:
                self.original_data.append({
                    'id': row['id'],
                    'descrizione': row['descrizione'],
                    'codifica': row['codifica'] or '',
                    'informazioni': row['informazioni'] or ''
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
            # Tronca le informazioni se troppo lunghe
            informazioni_display = row['informazioni']
            if len(informazioni_display) > 100:
                informazioni_display = informazioni_display[:100] + "..."
            
            values = [
                row['id'],
                row['descrizione'],
                row['codifica'] if row['codifica'] else '-',
                informazioni_display
            ]
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", tk.END, values=values, tags=(tag, f"id_{row['id']}"))
        
        self.counter_label.config(text=f"{len(self.original_data)} categorie visualizzate")
    
    def nuova_categoria(self):
        """Apre il dialog per creare una nuova categoria"""
        CategoriaLaboratorioDialog(self, self.db_path, on_success=self.load_data)
    
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
            CategoriaLaboratorioDialog(self, self.db_path, categoria_data=categoria_data, on_success=self.load_data)
    
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
        
        # Trova la descrizione della categoria
        categoria_descrizione = ""
        for row in self.original_data:
            if row['id'] == categoria_id:
                categoria_descrizione = row['descrizione']
                break
        
        # Conferma eliminazione
        if not messagebox.askyesno("Conferma", 
            f"Sei sicuro di voler eliminare la categoria '{categoria_descrizione}'?\n\n"
            "Questa operazione è irreversibile."):
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM categorie_laboratorio WHERE id = ?", (categoria_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Successo", "Categoria eliminata con successo!")
            self.load_data()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'eliminazione: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Categorie Laboratorio")
    root.geometry("1200x700")
    app = CategorieLaboratorioPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
