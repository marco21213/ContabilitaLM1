"""
Pagina GUI per il controllo prezzi con analisi di file XML.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# Aggiunge il percorso per gli import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, "assets", "style"))
sys.path.append(os.path.join(project_root, "scripts"))   # <— IMPORTANTE

from styles import Style
from controller_manager import ControllerManager        # <— MANAGER ESTERNO


class ControlloPrezziPage(tk.Frame):
    """Pagina per il controllo prezzi da file XML."""

    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        self.parent = parent

        # Variabili di stato
        self.selected_folder = tk.StringVar(value="")
        self.xml_files = []
        self.controlli_results = []
        self.manager = ControllerManager()   # <— MANAGER CONTROLLI

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Crea l'interfaccia utente."""

        # ==================== HEADER ====================
        header_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        header_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=Style.CONTENT_PADDING)

        title_label = tk.Label(
            header_frame,
            text="📋 Controllo Prezzi da File XML",
            font=("Arial", 18, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG,
        )
        title_label.pack(side="left")

        # ==================== SELEZIONE CARTELLA ====================
        folder_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        folder_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))

        tk.Label(
            folder_frame,
            text="Cartella selezionata:",
            bg=Style.BACKGROUND_COLOR,
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")

        path_frame = tk.Frame(folder_frame, bg=Style.BACKGROUND_COLOR)
        path_frame.pack(fill="x", pady=(5, 0))

        self.folder_entry = tk.Entry(
            path_frame,
            textvariable=self.selected_folder,
            state="readonly",
            font=("Arial", 10),
            bg="#f5f5f5",
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            path_frame,
            text="📁 Sfoglia",
            command=self.select_folder,
            bg=Style.MENU_HEADER_BG,
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5,
            cursor="hand2",
        )
        browse_btn.pack(side="left")

        # ==================== INFO FILE ====================
        info_frame = tk.Frame(self, bg="#e8f4f8", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))

        self.info_label = tk.Label(
            info_frame,
            text="Nessuna cartella selezionata",
            bg="#e8f4f8",
            fg="#0c5460",
            font=("Arial", 9),
            padx=10,
            pady=5,
            wraplength=800,
            justify="left",
        )
        self.info_label.pack(fill="x")

        # ==================== PULSANTI ====================
        action_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        action_frame.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))

        self.start_btn = tk.Button(
            action_frame,
            text="▶️  Avvia Controllo",
            command=self.avvia_controllo,
            bg="#28a745",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=8,
            state="disabled",
            cursor="hand2",
        )
        self.start_btn.pack(side="left", padx=5)

        self.clear_btn = tk.Button(
            action_frame,
            text="🗑️  Pulisci Risultati",
            command=self.pulisci_risultati,
            bg="#6c757d",
            fg="white",
            font=("Arial", 11),
            padx=20,
            pady=8,
            cursor="hand2",
        )
        self.clear_btn.pack(side="left", padx=5)

        # ==================== TABELLA RISULTATI ====================
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))

        table_header = tk.Frame(table_frame, bg=Style.MENU_HEADER_BG)
        table_header.pack(fill="x", pady=(0, 5))

        tk.Label(
            table_header,
            text="Risultati Controllo",
            bg=Style.MENU_HEADER_BG,
            fg="white",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=5,
        ).pack(anchor="w")

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        columns = ("file", "tipo_controllo", "articoli", "stato", "dettagli")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar.set,
            height=15,
        )
        scrollbar.config(command=self.tree.yview)

        self.tree.heading("file", text="File XML")
        self.tree.heading("tipo_controllo", text="Tipo Controllo")
        self.tree.heading("articoli", text="Problemi")
        self.tree.heading("stato", text="Stato")
        self.tree.heading("dettagli", text="Dettagli")

        self.tree.column("file", width=200)
        self.tree.column("tipo_controllo", width=150)
        self.tree.column("articoli", width=100)
        self.tree.column("stato", width=100)
        self.tree.column("dettagli", width=350)

        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure("ok", background="#d4edda")
        self.tree.tag_configure("warning", background="#fff3cd")
        self.tree.tag_configure("error", background="#f8d7da")

        self.tree.bind("<Double-1>", self.on_row_double_click)

        # ==================== STATUS ====================
        status_frame = tk.Frame(self, bg="#f5f5f5", relief="sunken", borderwidth=1)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            status_frame,
            text="Pronto",
            bg="#f5f5f5",
            fg="#666",
            font=("Arial", 9),
            padx=10,
            pady=5,
            anchor="w",
        )
        self.status_label.pack(fill="x")

    # ==================== SELEZIONE CARTELLA ====================

    def select_folder(self):
        folder = filedialog.askdirectory(
            title="Seleziona cartella con file XML",
            initialdir=os.path.expanduser("~"),
        )

        if folder:
            self.selected_folder.set(folder)
            self.load_xml_files(folder)

    def load_xml_files(self, folder_path):
        self.xml_files = list(Path(folder_path).glob("*.xml"))

        if not self.xml_files:
            self.info_label.config(
                text=f"⚠️  Nessun file XML trovato in: {folder_path}",
                fg="#856404",
            )
            self.start_btn.config(state="disabled")
            return

        file_count = len(self.xml_files)
        file_list = ", ".join([f.name for f in self.xml_files[:5]])
        if file_count > 5:
            file_list += f", ... e altri {file_count - 5}"

        self.info_label.config(
            text=f"✅ Trovati {file_count} file XML:\n{file_list}",
            fg="#0c5460",
        )

        self.start_btn.config(state="normal")

    # ==================== CONTROLLO FILE ====================

    def avvia_controllo(self):
        if not self.xml_files:
            messagebox.showwarning("Attenzione", "Nessun file XML selezionato.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.controlli_results = []

        for xml_file in self.xml_files:
            risultato = self.analizza_file_xml(xml_file)
            self.controlli_results.append(risultato)
            self.add_row_to_tree(risultato)

        messagebox.showinfo("Completato", "Controllo completato!")
        self.update_status("Controllo completato")

    def analizza_file_xml(self, xml_file: Path) -> dict:
        """
        Usa i controlli esterni definiti in scripts/controller_manager.py
        """

        try:
            risultati = self.manager.esegui_controlli(xml_file)

            # Aggrega problemi
            problemi = []
            for controllo in risultati:
                for p in controllo["problemi"]:
                    problemi.append(f"{controllo['nome_controllo']}: {p['messaggio']}")

            if problemi:
                stato = "❌ ERRORI"
                tag = "error"
                dettagli = "\n".join(problemi)
            else:
                stato = "OK"
                tag = "ok"
                dettagli = "Nessun problema rilevato"

            return {
                "file_name": xml_file.name,
                "file_path": str(xml_file),
                "tipo_controllo": "Controlli Fattura",
                "num_articoli": len(problemi),
                "stato": stato,
                "dettagli": dettagli,
                "tag": tag,
                "data_elaborazione": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            return {
                "file_name": xml_file.name,
                "file_path": str(xml_file),
                "tipo_controllo": "Errore",
                "num_articoli": 0,
                "stato": "❌ ERRORE",
                "dettagli": str(e),
                "tag": "error",
            }

    # ==================== TABELLARE ====================

    def add_row_to_tree(self, risultato: dict):
        self.tree.insert(
            "",
            "end",
            values=(
                risultato["file_name"],
                risultato["tipo_controllo"],
                risultato["num_articoli"],
                risultato["stato"],
                risultato["dettagli"],
            ),
            tags=(risultato["tag"],),
        )

    def on_row_double_click(self, event):
        selection = self.tree.selection()
        if selection:
            self.mostra_dettagli(selection[0])

    def mostra_dettagli(self, item_id):
        values = self.tree.item(item_id, "values")
        if not values:
            return

        file_name = values[0]
        risultato = next((r for r in self.controlli_results if r["file_name"] == file_name), None)

        if not risultato:
            return

        details_window = tk.Toplevel(self)
        details_window.title(f"Dettagli: {file_name}")
        details_window.geometry("650x500")

        text = tk.Text(details_window, wrap="word", padx=10, pady=10, font=("Arial", 10))
        text.pack(fill="both", expand=True)

        details_text = f"""
FILE: {risultato['file_name']}
PERCORSO: {risultato['file_path']}

TIPO CONTROLLO: {risultato['tipo_controllo']}
STATO: {risultato['stato']}
DATA ELABORAZIONE: {risultato['data_elaborazione']}

PROBLEMI RISCONTRATI: {risultato['num_articoli']}

DETTAGLI:
{risultato['dettagli']}
"""

        text.insert("1.0", details_text)
        text.config(state="disabled")

        tk.Button(
            details_window,
            text="Chiudi",
            command=details_window.destroy,
            bg=Style.MENU_HEADER_BG,
            fg="white",
            padx=20,
            pady=5,
        ).pack(pady=10)

    # ==================== UTILITY ====================

    def pulisci_risultati(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.controlli_results = []
        self.update_status("Risultati puliti")

    def update_status(self, message: str):
        self.status_label.config(text=message)
        self.update_idletasks()
