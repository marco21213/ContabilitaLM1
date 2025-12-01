"""
Finestra principale dell'applicazione
"""
import tkinter as tk
from tkinter import ttk


class MainWindow:
    """Finestra principale dell'applicazione"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.init_ui()
    
    def init_ui(self):
        """Inizializza l'interfaccia utente"""
        self.root.title("La Mia Applicazione")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configura il grid per essere responsive
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Titolo
        title_label = ttk.Label(
            main_frame, 
            text="Benvenuto!", 
            font=("Arial", 24, "bold")
        )
        title_label.grid(row=0, column=0, pady=20)
        
        # Campo di input
        self.input_field = ttk.Entry(main_frame, width=40)
        self.input_field.grid(row=1, column=0, pady=10)
        self.input_field.insert(0, "Inserisci del testo...")
        
        # Pulsante
        self.button = ttk.Button(
            main_frame, 
            text="Clicca qui", 
            command=self.on_button_click
        )
        self.button.grid(row=2, column=0, pady=10)
        
        # Label risultato
        self.result_label = ttk.Label(
            main_frame, 
            text="", 
            font=("Arial", 12),
            foreground="#0066cc"
        )
        self.result_label.grid(row=3, column=0, pady=20)
        
        # Centra tutti i widget
        for child in main_frame.winfo_children():
            child.grid_configure(padx=5)
    
    def on_button_click(self):
        """Gestisce il click del pulsante"""
        text = self.input_field.get()
        if text and text != "Inserisci del testo...":
            self.result_label.config(text=f"Hai scritto: {text}")
        else:
            self.result_label.config(text="Inserisci del testo prima di cliccare!")
    
    def run(self):
        """Avvia il loop principale dell'applicazione"""
        self.root.mainloop()