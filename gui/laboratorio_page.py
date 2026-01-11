"""
Pagina principale del modulo Laboratorio - Gestione ricette vernici
Contiene 4 tab: Home, Categorie, Ricette, Appunti
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import configparser
import os
from datetime import datetime

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style

# Importa le tab
from laboratorio_categorie_tab import CategorieTab


class LaboratorioApp(tk.Frame):
    """Applicazione principale per la gestione del laboratorio di vernici"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.db_path = self.get_db_path()

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        # Tab attiva
        self.current_tab = "home"  # "home", "categorie", "ricette", "appunti"
        
        # Componenti tab (verranno creati quando necessario)
        self.home_tab = None
        self.categorie_tab = None
        self.ricette_tab = None
        self.appunti_tab = None

        self.configure_style()
        self.configure(bg=Style.BACKGROUND_COLOR)
        
        # Crea il sistema di tab
        self.create_tab_system()

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
        
        # Tab Home
        self.tab_buttons['home'] = tk.Button(
            tab_header_frame, 
            text="🏠 HOME",
            command=lambda: self.switch_tab('home'),
            **tab_style
        )
        self.tab_buttons['home'].pack(side="left", padx=(0, 5))
        
        # Tab Categorie
        self.tab_buttons['categorie'] = tk.Button(
            tab_header_frame,
            text="📁 CATEGORIE",
            command=lambda: self.switch_tab('categorie'),
            **tab_style
        )
        self.tab_buttons['categorie'].pack(side="left", padx=(0, 5))
        
        # Tab Ricette
        self.tab_buttons['ricette'] = tk.Button(
            tab_header_frame,
            text="🧪 RICETTE",
            command=lambda: self.switch_tab('ricette'),
            **tab_style
        )
        self.tab_buttons['ricette'].pack(side="left", padx=(0, 5))
        
        # Tab Appunti
        self.tab_buttons['appunti'] = tk.Button(
            tab_header_frame,
            text="📝 APPUNTI",
            command=lambda: self.switch_tab('appunti'),
            **tab_style
        )
        self.tab_buttons['appunti'].pack(side="left")
        
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
        
        # Contenuto tab (tutto il resto)
        self.content_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        self.content_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        # Attiva la tab predefinita
        self.switch_tab('home')

    def switch_tab(self, tab_name):
        """Cambia la tab attiva"""
        self.current_tab = tab_name
        
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
        
        # Rimuovi tutti i widget dal content_frame e resetta i riferimenti
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Resetta i riferimenti alle tab
        self.home_tab = None
        self.categorie_tab = None
        self.ricette_tab = None
        self.appunti_tab = None
        
        # Crea il componente appropriato
        if tab_name == 'home':
            self.create_home_tab()
        elif tab_name == 'categorie':
            self.create_categorie_tab()
        elif tab_name == 'ricette':
            self.create_ricette_tab()
        elif tab_name == 'appunti':
            self.create_appunti_tab()

    def create_home_tab(self):
        """Crea la tab Home (Dashboard)"""
        home_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        home_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            home_frame,
            text="🏠 Dashboard Laboratorio",
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG,
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=20)
        
        # Frame per le statistiche
        stats_frame = tk.Frame(home_frame, bg=Style.BACKGROUND_COLOR)
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Statistiche
            cursor.execute("SELECT COUNT(*) FROM ricette WHERE attivo = 1")
            tot_ricette = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM categorie_ricette WHERE attivo = 1")
            tot_categorie = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ingredienti WHERE attivo = 1")
            tot_ingredienti = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM appunti_laboratorio")
            tot_appunti = cursor.fetchone()[0]
            
            conn.close()
            
            # Crea card statistiche
            stats = [
                ("Ricette Attive", tot_ricette, "🧪"),
                ("Categorie", tot_categorie, "📁"),
                ("Ingredienti", tot_ingredienti, "⚗️"),
                ("Appunti", tot_appunti, "📝")
            ]
            
            for i, (label, value, icon) in enumerate(stats):
                card = tk.Frame(stats_frame, bg="white", relief="raised", borderwidth=2)
                card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
                
                icon_label = tk.Label(card, text=icon, font=("Arial", 24), bg="white")
                icon_label.pack(pady=(10, 5))
                
                value_label = tk.Label(card, text=str(value), font=("Arial", 20, "bold"), bg="white", fg=Style.MENU_HEADER_BG)
                value_label.pack()
                
                label_label = tk.Label(card, text=label, font=("Arial", 10), bg="white", fg="#666666")
                label_label.pack(pady=(0, 10))
            
            stats_frame.grid_columnconfigure(0, weight=1)
            stats_frame.grid_columnconfigure(1, weight=1)
            stats_frame.grid_columnconfigure(2, weight=1)
            stats_frame.grid_columnconfigure(3, weight=1)
            
        except Exception as e:
            error_label = tk.Label(
                home_frame,
                text=f"Errore nel caricamento delle statistiche: {str(e)}",
                bg=Style.BACKGROUND_COLOR,
                fg="red",
                font=("Arial", 10)
            )
            error_label.pack(pady=20)
            
            # Verifica se le tabelle esistono
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ricette'")
                if not cursor.fetchone():
                    info_label = tk.Label(
                        home_frame,
                        text="⚠️ Le tabelle del laboratorio non sono state inizializzate.\nEsegui lo script init_laboratorio_database.py",
                        bg=Style.BACKGROUND_COLOR,
                        fg="orange",
                        font=("Arial", 10, "bold")
                    )
                    info_label.pack(pady=10)
                conn.close()
            except:
                pass

    def create_categorie_tab(self):
        """Crea la tab Categorie"""
        self.categorie_tab = CategorieTab(self.content_frame, self.db_path)
        self.categorie_tab.pack(fill="both", expand=True)

    def create_ricette_tab(self):
        """Crea la tab Ricette - Placeholder"""
        ricette_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        ricette_frame.pack(fill="both", expand=True)
        
        title_label = tk.Label(
            ricette_frame,
            text="🧪 Gestione Ricette",
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG,
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        info_label = tk.Label(
            ricette_frame,
            text="Gestione ricette - Da implementare",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)

    def create_appunti_tab(self):
        """Crea la tab Appunti - Placeholder"""
        appunti_frame = tk.Frame(self.content_frame, bg=Style.BACKGROUND_COLOR)
        appunti_frame.pack(fill="both", expand=True)
        
        title_label = tk.Label(
            appunti_frame,
            text="📝 Gestione Appunti",
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG,
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        info_label = tk.Label(
            appunti_frame,
            text="Gestione appunti - Da implementare",
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Laboratorio Vernici")
    root.geometry("1200x700")
    app = LaboratorioApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
