import tkinter as tk
from tkinter import ttk
from datetime import datetime

class PeriodDialog:
    def __init__(self, parent, config, save_callback, execute_callback):
        self.parent = parent
        self.config = config
        self.save_callback = save_callback
        self.execute_callback = execute_callback
        self.create_dialog()
    
    def create_dialog(self):
        self.period_window = tk.Toplevel(self.parent)
        self.period_window.title("Seleziona Periodo")
        self.period_window.configure(bg=self.parent.cget('bg'))
        self.period_window.geometry("250x400")
        
        main_frame = tk.Frame(self.period_window, bg=self.parent.cget('bg'), padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Implementazione completa della finestra di dialogo
        tk.Label(main_frame, text="Data Inizio (dd/mm/yyyy):", 
                bg=self.parent.cget('bg')).pack(pady=5)
        self.start_date_entry = tk.Entry(main_frame, font=("Arial", 11))
        self.start_date_entry.pack(pady=5, fill="x")
        
        tk.Label(main_frame, text="Data Fine (dd/mm/yyyy):", 
                bg=self.parent.cget('bg')).pack(pady=5)
        self.end_date_entry = tk.Entry(main_frame, font=("Arial", 11))
        self.end_date_entry.pack(pady=5, fill="x")
        
        tk.Label(main_frame, text="Seleziona Opzione Data:", 
                bg=self.parent.cget('bg')).pack(pady=5)
        self.date_option_var = tk.StringVar(value="")
        date_option_menu = ttk.Combobox(main_frame, textvariable=self.date_option_var, state="readonly")
        date_option_menu['values'] = ["Data di Emissione", "Data di Ricezione"]
        date_option_menu.pack(pady=5, fill="x")
        
        tk.Label(main_frame, text="Seleziona Tipo Documento:", 
                bg=self.parent.cget('bg')).pack(pady=5)
        self.venoacq_var = tk.StringVar(value="")
        venoacq_menu = ttk.Combobox(main_frame, textvariable=self.venoacq_var, state="readonly")
        venoacq_menu['values'] = ["Acquisti", "Vendite"]
        venoacq_menu.pack(pady=5, fill="x")
        
        btn_frame = tk.Frame(main_frame, bg=self.parent.cget('bg'))
        btn_frame.pack(pady=20)
        
        download_btn = tk.Button(btn_frame, text="Scarica", command=self.execute,
                               bg="blue", fg="white", font=("Arial", 12, "bold"),
                               cursor="hand2", padx=20, pady=10)
        download_btn.pack()
    
    def execute(self):
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        date_option = self.date_option_var.get()
        venoacq = self.venoacq_var.get()
        
        if not all([start_date, end_date, date_option, venoacq]):
            tk.messagebox.showerror("Errore", "Compila tutti i campi prima di procedere.")
            return
        
        try:
            self.save_callback(start_date, end_date, date_option, venoacq)
            self.execute_callback()
            self.period_window.destroy()
        except Exception as e:
            tk.messagebox.showerror("Errore", f"Errore durante l'esecuzione: {e}")

class MonthlyDialog:
    def __init__(self, parent, tipo_documento, execute_callback):
        self.parent = parent
        self.tipo_documento = tipo_documento
        self.execute_callback = execute_callback
        self.create_dialog()
    
    def create_dialog(self):
        # Implementazione simile a PeriodDialog per il mensile
        pass