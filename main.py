import sys
import os
import sqlite3
import configparser
import hashlib
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, simpledialog

sys.path.append(os.path.join(os.path.dirname(__file__), 'gui'))

from gui.main_window import MainWindow

class AuthenticationSystem:
    def __init__(self):
        pass

    def authenticate(self, username, password):
        """Autenticazione semplificata - sempre successo"""
        return True, "Accesso diretto abilitato"

def show_login_window():
    """Mostra una finestra di benvenuto semplificata"""
    root = tk.Tk()
    root.title("Contabilità 3b")
    root.geometry("300x200")
    root.resizable(False, False)
    
    # Centra la finestra
    root.eval('tk::PlaceWindow . center')
    
    # Frame principale
    main_frame = tk.Frame(root)
    main_frame.pack(expand=True, fill='both', padx=20, pady=20)
    
    # Titolo
    title_label = tk.Label(main_frame, text="Benvenuto", font=("Arial", 16, "bold"))
    title_label.pack(pady=(20, 30))
    
    # Messaggio di benvenuto
    welcome_label = tk.Label(main_frame, text="Accesso diretto al sistema", 
                           font=("Arial", 10), fg="green")
    welcome_label.pack(pady=(0, 30))
    
    def start_app():
        root.destroy()
        start_main_application()
    
    def exit_application():
        if messagebox.askyesno("Conferma", "Sei sicuro di voler uscire?"):
            root.destroy()
    
    # Frame per i pulsanti
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill='x', pady=(20, 0))
    
    # Pulsante di accesso
    access_btn = tk.Button(button_frame, text="Accedi", command=start_app, 
                         bg="#007acc", fg="white", font=("Arial", 10, "bold"),
                         width=12, height=1)
    access_btn.pack(side='left', padx=(0, 10))
    
    # Pulsante Esci
    exit_btn = tk.Button(button_frame, text="Esci", command=exit_application,
                        bg="#dc3545", fg="white", font=("Arial", 10),
                        width=8, height=1)
    exit_btn.pack(side='right')
    
    # Info versione
    version_label = tk.Label(main_frame, text="Contabilità 3B v1.0", 
                            font=("Arial", 8), fg="gray")
    version_label.pack(side='bottom', pady=(20, 0))
    
    # Avvia automaticamente dopo breve attesa
    root.after(1000, start_app)
    
    root.mainloop()

def start_main_application():
    """Avvia l'applicazione principale"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    show_login_window()