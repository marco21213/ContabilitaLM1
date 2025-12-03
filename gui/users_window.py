import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any
import sqlite3
import configparser
import logging
import hashlib
import os

logger = logging.getLogger(__name__)

class UsersWindow:
    """Finestra di gestione utenti e password con database SQLite"""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Gestione Utenti")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centra la finestra
        self.center_window()
        
        # Configurazione database
        self.config_file = "config.ini"
        self.db_path = self.get_database_path()
        
        # Inizializza variabili
        self.users = []
        self.selected_user = None
        self.conn = None
        
        self.create_widgets()
        self.connect_database()
        self.load_users()
        self.refresh_users_list()
        
    def center_window(self) -> None:
        """Centra la finestra rispetto alla finestra principale"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def get_database_path(self) -> str:
        """Ottiene il percorso del database dal file config.ini"""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            return config.get('Autenticazione', 'percorso_database', fallback='contabilita.db')
        except Exception as e:
            logger.error(f"Errore nella lettura del config.ini: {e}")
            return 'contabilita.db'
    
    def connect_database(self) -> None:
        """Connette al database SQLite"""
        try:
            # Crea la cartella se non esiste
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()
            
        except Exception as e:
            logger.error(f"Errore nella connessione al database: {e}")
            messagebox.showerror("Errore Database", f"Impossibile connettere al database: {e}")
            self.window.destroy()
    
    def create_tables(self) -> None:
        """Crea le tabelle necessarie se non esistono"""
        try:
            cursor = self.conn.cursor()
            
            # Tabella utenti
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS utenti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    ruolo TEXT NOT NULL CHECK(ruolo IN ('Amministratore', 'Utente', 'Sola Lettura')),
                    attivo BOOLEAN DEFAULT 1,
                    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inserisce l'utente admin predefinito se non esiste
            cursor.execute('SELECT COUNT(*) FROM utenti WHERE username = "admin"')
            if cursor.fetchone()[0] == 0:
                admin_password = self.hash_password("admin123")
                cursor.execute('''
                    INSERT INTO utenti (username, password_hash, ruolo, attivo)
                    VALUES (?, ?, ?, 1)
                ''', ('admin', admin_password, 'Amministratore'))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Errore nella creazione delle tabelle: {e}")
            self.conn.rollback()
    
    def hash_password(self, password: str) -> str:
        """Hash della password usando SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self) -> None:
        """Carica la lista utenti dal database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, username, ruolo, attivo 
                FROM utenti 
                ORDER BY username
            ''')
            
            self.users = []
            for row in cursor.fetchall():
                self.users.append({
                    'id': row[0],
                    'username': row[1],
                    'ruolo': row[2],
                    'attivo': bool(row[3])
                })
                
        except Exception as e:
            logger.error(f"Errore nel caricamento utenti: {e}")
            messagebox.showerror("Errore", f"Errore nel caricamento utenti: {e}")
    
    def create_widgets(self) -> None:
        """Crea i widget della finestra utenti"""
        # Frame principale
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Titolo
        ttk.Label(
            main_frame, 
            text="Gestione Utenti e Password", 
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 15))
        
        # Info database
        db_info = ttk.Label(
            main_frame, 
            text=f"Database: {self.db_path}",
            font=("Arial", 9),
            foreground="gray"
        )
        db_info.pack(pady=(0, 10))
        
        # Frame per lista utenti
        list_frame = ttk.LabelFrame(main_frame, text="Utenti Esistenti", padding="10")
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Treeview per lista utenti
        columns = ('id', 'username', 'ruolo', 'stato')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # Definizione colonne
        self.tree.heading('id', text='ID')
        self.tree.heading('username', text='Username')
        self.tree.heading('ruolo', text='Ruolo')
        self.tree.heading('stato', text='Stato')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('username', width=150, anchor='w')
        self.tree.column('ruolo', width=150, anchor='w')
        self.tree.column('stato', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind selezione
        self.tree.bind('<<TreeviewSelect>>', self.on_user_select)
        
        # Frame per dettagli utente
        detail_frame = ttk.LabelFrame(main_frame, text="Dettagli Utente", padding="10")
        detail_frame.pack(fill='x', pady=(0, 15))
        
        # Form dettagli utente
        ttk.Label(detail_frame, text="Username:").grid(row=0, column=0, sticky='w', pady=5)
        self.username_entry = ttk.Entry(detail_frame, width=25)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(detail_frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        self.password_entry = ttk.Entry(detail_frame, width=25, show='*')
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(detail_frame, text="Conferma Password:").grid(row=2, column=0, sticky='w', pady=5)
        self.confirm_entry = ttk.Entry(detail_frame, width=25, show='*')
        self.confirm_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(detail_frame, text="Ruolo:").grid(row=3, column=0, sticky='w', pady=5)
        self.ruolo_combo = ttk.Combobox(
            detail_frame, 
            values=["Amministratore", "Utente", "Sola Lettura"],
            state="readonly",
            width=22
        )
        self.ruolo_combo.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        self.attivo_var = tk.BooleanVar()
        ttk.Checkbutton(
            detail_frame, 
            text="Utente Attivo", 
            variable=self.attivo_var
        ).grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        
        detail_frame.columnconfigure(1, weight=1)
        
        # Frame pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        # Pulsanti sinistra
        left_btn_frame = ttk.Frame(button_frame)
        left_btn_frame.pack(side='left')
        
        ttk.Button(
            left_btn_frame, 
            text="Nuovo Utente", 
            command=self.new_user
        ).pack(side='left', padx=5)
        
        ttk.Button(
            left_btn_frame, 
            text="Aggiorna Lista", 
            command=self.refresh_data
        ).pack(side='left', padx=5)
        
        # Pulsanti destra
        right_btn_frame = ttk.Frame(button_frame)
        right_btn_frame.pack(side='right')
        
        ttk.Button(
            right_btn_frame, 
            text="Salva", 
            command=self.save_user,
            style='Accent.TButton'
        ).pack(side='right', padx=5)
        
        ttk.Button(
            right_btn_frame, 
            text="Elimina", 
            command=self.delete_user
        ).pack(side='right', padx=5)
        
        ttk.Button(
            right_btn_frame, 
            text="Annulla", 
            command=self.window.destroy
        ).pack(side='right', padx=5)
        
        # Stile per pulsante Salva
        style = ttk.Style()
        style.configure('Accent.TButton', foreground='white', background='#007acc')
    
    def refresh_data(self) -> None:
        """Aggiorna i dati dal database"""
        self.load_users()
        self.refresh_users_list()
        self.clear_form()
        messagebox.showinfo("Aggiornamento", "Lista utenti aggiornata!")
    
    def refresh_users_list(self) -> None:
        """Aggiorna la lista utenti nella treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for user in self.users:
            stato = "Attivo" if user['attivo'] else "Disattivato"
            self.tree.insert('', 'end', values=(
                user['id'], 
                user['username'], 
                user['ruolo'], 
                stato
            ))
    
    def on_user_select(self, event) -> None:
        """Gestisce la selezione di un utente dalla lista"""
        selection = self.tree.selection()
        if not selection:
            return
            
        item = self.tree.item(selection[0])
        user_id = item['values'][0]
        
        # Trova l'utente selezionato
        self.selected_user = next((u for u in self.users if u['id'] == user_id), None)
        
        if self.selected_user:
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, self.selected_user['username'])
            self.password_entry.delete(0, tk.END)
            self.confirm_entry.delete(0, tk.END)
            self.ruolo_combo.set(self.selected_user['ruolo'])
            self.attivo_var.set(self.selected_user['attivo'])
    
    def new_user(self) -> None:
        """Prepara il form per un nuovo utente"""
        self.selected_user = None
        self.clear_form()
        self.username_entry.focus()
    
    def clear_form(self) -> None:
        """Pulisce il form"""
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.confirm_entry.delete(0, tk.END)
        self.ruolo_combo.set('')
        self.attivo_var.set(True)
        self.tree.selection_remove(self.tree.selection())
    
    def save_user(self) -> None:
        """Salva le modifiche all'utente nel database"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        ruolo = self.ruolo_combo.get()
        attivo = self.attivo_var.get()
        
        # Validazione
        if not username:
            messagebox.showerror("Errore", "Inserire un username valido!")
            return
            
        if password and password != confirm:
            messagebox.showerror("Errore", "Le password non coincidono!")
            return
            
        if not ruolo:
            messagebox.showerror("Errore", "Selezionare un ruolo!")
            return
        
        try:
            cursor = self.conn.cursor()
            
            if self.selected_user:
                # Modifica utente esistente
                if password:
                    # Aggiorna anche la password
                    password_hash = self.hash_password(password)
                    cursor.execute('''
                        UPDATE utenti 
                        SET username = ?, password_hash = ?, ruolo = ?, attivo = ?, data_modifica = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (username, password_hash, ruolo, attivo, self.selected_user['id']))
                else:
                    # Aggiorna senza modificare la password
                    cursor.execute('''
                        UPDATE utenti 
                        SET username = ?, ruolo = ?, attivo = ?, data_modifica = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (username, ruolo, attivo, self.selected_user['id']))
                
                messagebox.showinfo("Successo", "Utente aggiornato correttamente!")
            else:
                # Nuovo utente
                if not password:
                    messagebox.showerror("Errore", "Inserire una password per il nuovo utente!")
                    return
                    
                password_hash = self.hash_password(password)
                cursor.execute('''
                    INSERT INTO utenti (username, password_hash, ruolo, attivo)
                    VALUES (?, ?, ?, ?)
                ''', (username, password_hash, ruolo, attivo))
                
                messagebox.showinfo("Successo", "Utente creato correttamente!")
            
            self.conn.commit()
            self.refresh_data()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Errore", "Username già esistente!")
        except Exception as e:
            logger.error(f"Errore nel salvataggio utente: {e}")
            self.conn.rollback()
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")
    
    def delete_user(self) -> None:
        """Elimina l'utente selezionato dal database"""
        if not self.selected_user:
            messagebox.showwarning("Attenzione", "Selezionare un utente da eliminare!")
            return
            
        if self.selected_user['username'] == 'admin':
            messagebox.showerror("Errore", "Non è possibile eliminare l'utente admin!")
            return
            
        if messagebox.askyesno("Conferma", f"Eliminare definitivamente l'utente {self.selected_user['username']}?"):
            try:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM utenti WHERE id = ?', (self.selected_user['id'],))
                self.conn.commit()
                
                messagebox.showinfo("Successo", "Utente eliminato correttamente!")
                self.refresh_data()
                
            except Exception as e:
                logger.error(f"Errore nell'eliminazione utente: {e}")
                self.conn.rollback()
                messagebox.showerror("Errore", f"Errore nell'eliminazione: {e}")
    
    def __del__(self):
        """Chiude la connessione al database quando la finestra viene chiusa"""
        if self.conn:
            self.conn.close()