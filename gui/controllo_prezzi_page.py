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

# Import per l'header con icone
sys.path.append(os.path.join(current_dir, 'modules'))
from icon_manager import IconManager
from ui_components import TopBar


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
        
        # Inizializza icon manager
        self.icon_manager = IconManager()

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Crea l'interfaccia utente."""
        
        # ==================== HEADER CON ICONE ====================
        main_container = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=5, pady=5)
        main_container.pack(fill="both", expand=True)
        
        # Crea la top bar con i comandi
        commands_config = {
            'show_info': self.mostra_info_controlli
        }
        
        self.top_bar = TopBar(main_container, self.icon_manager, commands_config)

        # ==================== SELEZIONE CARTELLA ====================
        folder_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
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
        info_frame = tk.Frame(main_container, bg="#e8f4f8", relief="solid", borderwidth=1)
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
        action_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
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
        table_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
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
        status_frame = tk.Frame(main_container, bg="#f5f5f5", relief="sunken", borderwidth=1)
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

        # Operazione preventiva: rinomina i file XML con il numero di fattura
        self.update_status("Rinomina file XML in corso...")
        self.rinomina_file_xml()

        # Ricarica i file XML dopo la rinomina
        folder_path = self.selected_folder.get()
        if folder_path:
            self.load_xml_files(folder_path)

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.controlli_results = []

        self.update_status("Esecuzione controlli in corso...")
        for xml_file in self.xml_files:
            risultato = self.analizza_file_xml(xml_file)
            self.controlli_results.append(risultato)
            self.add_row_to_tree(risultato)

        messagebox.showinfo("Completato", "Controllo completato!")
        self.update_status("Controllo completato")

    def rinomina_file_xml(self):
        """
        Rinomina tutti i file XML nella cartella selezionata con il numero di fattura.
        Rimuove i caratteri '/' e '\' dal numero di fattura.
        Esempio: 1040/A diventa 1040A.xml
        """
        folder_path = self.selected_folder.get()
        if not folder_path:
            return

        try:
            xml_files = list(Path(folder_path).glob("*.xml"))
            rinomine_effettuati = 0
            errori = []

            for xml_file in xml_files:
                try:
                    # Estrai il numero di fattura dall'XML
                    numero_fattura = self.estrai_numero_fattura(xml_file)
                    
                    if not numero_fattura:
                        errori.append(f"{xml_file.name}: Numero fattura non trovato")
                        continue

                    # Pulisci il numero di fattura rimuovendo '/' e '\'
                    numero_pulito = self.pulisci_numero_fattura(numero_fattura)
                    
                    # Crea il nuovo nome file
                    nuovo_nome = f"{numero_pulito}.xml"
                    nuovo_path = xml_file.parent / nuovo_nome

                    # Se il nuovo nome è diverso dal vecchio, rinomina
                    if nuovo_nome != xml_file.name:
                        # Se esiste già un file con lo stesso nome, aggiungi un suffisso
                        if nuovo_path.exists() and nuovo_path != xml_file:
                            counter = 1
                            while nuovo_path.exists():
                                nuovo_nome = f"{numero_pulito}_{counter}.xml"
                                nuovo_path = xml_file.parent / nuovo_nome
                                counter += 1
                        
                        # Rinomina il file
                        xml_file.rename(nuovo_path)
                        rinomine_effettuati += 1

                except Exception as e:
                    errori.append(f"{xml_file.name}: {str(e)}")

            # Mostra un messaggio con i risultati
            if rinomine_effettuati > 0 or errori:
                messaggio = f"Rinomina completata:\n"
                if rinomine_effettuati > 0:
                    messaggio += f"✅ {rinomine_effettuati} file rinominati\n"
                if errori:
                    messaggio += f"⚠️ {len(errori)} errori\n"
                    if len(errori) <= 5:
                        messaggio += "\n".join(errori)
                    else:
                        messaggio += "\n".join(errori[:5]) + f"\n... e altri {len(errori) - 5} errori"
                
                if rinomine_effettuati > 0:
                    messagebox.showinfo("Rinomina completata", messaggio)

        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la rinomina: {str(e)}")

    def estrai_numero_fattura(self, xml_file: Path) -> str:
        """
        Estrae il numero di fattura da un file XML.
        
        Args:
            xml_file: Percorso del file XML
            
        Returns:
            Numero di fattura come stringa, o stringa vuota se non trovato
        """
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Gestione namespace se presente
            ns = {}
            if '}' in root.tag:
                ns_prefix = root.tag.split('}')[0].strip('{')
                ns = {'ns': ns_prefix}
            
            # Cerca il numero con e senza namespace
            numero = None
            if ns:
                numero = root.findtext(".//ns:DatiGenerali/ns:DatiGeneraliDocumento/ns:Numero", namespaces=ns, default="")
            
            if not numero:
                numero = root.findtext(".//DatiGenerali/DatiGeneraliDocumento/Numero", default="")
            
            return numero.strip() if numero else ""
            
        except Exception as e:
            return ""

    def pulisci_numero_fattura(self, numero: str) -> str:
        """
        Pulisce il numero di fattura rimuovendo i caratteri '/' e '\'.
        Esempio: '1040/A' diventa '1040A'
        
        Args:
            numero: Numero di fattura da pulire
            
        Returns:
            Numero di fattura pulito
        """
        if not numero:
            return numero
        
        # Rimuovi '/' e '\'
        numero_pulito = numero.replace('/', '').replace('\\', '')
        
        return numero_pulito

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

    def mostra_info_controlli(self):
        """Mostra una finestra con il promemoria dei controlli implementati."""
        info_window = tk.Toplevel(self)
        info_window.title("ℹ️ Informazioni Controlli")
        info_window.geometry("500x400")
        info_window.resizable(False, False)
        info_window.transient(self)
        info_window.grab_set()

        # Frame principale
        main_frame = tk.Frame(info_window, bg=Style.BACKGROUND_COLOR)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Titolo
        title_label = tk.Label(
            main_frame,
            text="📋 Controlli Implementati",
            font=("Arial", 16, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG,
        )
        title_label.pack(pady=(0, 20))

        # Testo informativo
        info_text = """I seguenti controlli vengono eseguiti automaticamente 
su tutti i file XML selezionati:

1️⃣  CONTROLLO PREZZI MANCANTI
    Verifica l'assenza di quantità o prezzi zero/negativi
    nelle righe articolo delle fatture.

2️⃣  CONTROLLO CORRISPONDENZA FATTURA CON DATABASE
    Verifica che il TipoDocumento (TD01 - TD24) nell'XML
    corrisponda al tipo_fattura salvato nel database
    per il soggetto (fornitore o cliente).

3️⃣  CONTROLLO SPESE BANCARIE
    Verifica la presenza di spese bancarie nell'XML
    (TipoCessionePrestazione = "AC" e 
     Descrizione = "Spese Bancarie").

4️⃣  CONTROLLO DICHIARAZIONE D'INTENTO
    Per i clienti con dichiarazione d'intento valida:
    - Verifica che tutte le righe abbiano IVA a 0 e codice N3.5
    - Verifica che l'imponibile N3.5 non superi il plafond residuo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I risultati di tutti i controlli vengono visualizzati
nella tabella sottostante con i relativi dettagli."""

        text_widget = tk.Text(
            main_frame,
            wrap="word",
            font=("Arial", 10),
            bg="white",
            fg="#333",
            padx=15,
            pady=15,
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#ccc",
        )
        text_widget.pack(fill="both", expand=True, pady=(0, 15))
        text_widget.insert("1.0", info_text)
        text_widget.config(state="disabled")

        # Bottone Chiudi
        close_btn = tk.Button(
            main_frame,
            text="Chiudi",
            command=info_window.destroy,
            bg=Style.MENU_HEADER_BG,
            fg="white",
            font=("Arial", 10, "bold"),
            padx=30,
            pady=8,
            cursor="hand2",
        )
        close_btn.pack()

        # Centra la finestra
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (info_window.winfo_width() // 2)
        y = (info_window.winfo_screenheight() // 2) - (info_window.winfo_height() // 2)
        info_window.geometry(f"+{x}+{y}")
