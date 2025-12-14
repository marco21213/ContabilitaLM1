import tkinter as tk
from tkinter import ttk, messagebox
from tkinterweb import HtmlFrame
from PIL import Image, ImageTk
import os
import sys
import subprocess
import tempfile
import webbrowser
from datetime import datetime
from lxml import etree
from download_rapido_gui import DownloadRapidoWindow
from download_periodo_gui import DownloadPeriodoWindow
from download_mensile_gui import DownloadMensileWindow

# Aggiungi il percorso per importare lo stile
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'style'))
from styles import Style

# Aggiungi il percorso per importare lo stile e i moduli
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'assets', 'style'))
sys.path.append(os.path.join(current_dir, 'modules'))

from styles import Style
from config_utils import load_config, save_config
from icon_manager import IconManager
from dialogs import PeriodDialog
from ui_components import TopBar, DataTable, HtmlViewer

# Importa il parser XML dalla cartella scripts
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(project_root, 'scripts')
    sys.path.append(scripts_dir)
    from xml_parser_acquisti import XMLParser
except ImportError as e:
    print(f"Errore nell'importazione di xml_parser_acquisti: {e}")
    # Crea una classe dummy per evitare errori
    class XMLParser:
        def __init__(self):
            pass
        def get_all_basic_data(self):
            return []
        def extract_basic_data(self, file_path):
            return None
        def get_xml_files(self):
            return []

class MonthlyDialog(tk.Toplevel):
    """Dialog per selezione mese e anno"""
    
    def __init__(self, parent, doc_type, callback):
        super().__init__(parent)
        self.title(f"Download Mensile {doc_type.capitalize()}")
        self.doc_type = doc_type
        self.callback = callback
        self.result = None
        
        self.geometry("300x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Anno
        ttk.Label(main_frame, text="Anno:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        self.year_combo = ttk.Combobox(main_frame, textvariable=self.year_var, width=10)
        self.year_combo['values'] = [str(year) for year in range(2020, datetime.now().year + 1)]
        self.year_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Mese
        ttk.Label(main_frame, text="Mese:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(main_frame, textvariable=self.month_var, width=15)
        months = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        self.month_combo['values'] = months
        self.month_combo.current(datetime.now().month - 1)
        self.month_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Download", command=self.on_confirm).pack(side=tk.RIGHT)
        
    def on_confirm(self):
        month_num = self.month_combo.current() + 1  # 0-based to 1-based
        year_num = int(self.year_var.get())
        
        self.callback(month_num, year_num, self.doc_type)
        self.destroy()

class DownloadPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        self.parent = parent
        
        # Inizializza i manager
        self.icon_manager = IconManager()
        self.config = load_config()
        self.xml_parser = XMLParser()
        self.current_html = None
        self.xsl_path = None
        self.current_xml_file = None  # Memorizza il file XML corrente
        self.xsl_files = []  # Lista dei file XSL disponibili
        
        # Carica i file XSL prima di creare l'UI per avere i valori disponibili nel combobox
        self.setup_xsl_path()
        self.setup_ui()
        self.populate_list()

    def setup_xsl_path(self):
        """Configura il percorso del foglio di stile XSL e carica tutti i file disponibili."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_folder = os.path.join(current_dir, '../documents/css_fatture')
            
            # Carica tutti i file .xsl dalla cartella
            if os.path.exists(css_folder):
                self.xsl_files = [f for f in os.listdir(css_folder) if f.endswith('.xsl')]
                self.xsl_files.sort()  # Ordina alfabeticamente
                
                if not self.xsl_files:
                    messagebox.showwarning("Attenzione", f"Nessun file XSL trovato nella cartella: {css_folder}")
                    self.xsl_path = None
                    return
                
                # Imposta il file di default (se esiste)
                default_file = 'FoglioStileConDatiTrasmissione.xsl'
                if default_file in self.xsl_files:
                    self.xsl_path = os.path.join(css_folder, default_file)
                else:
                    # Usa il primo file disponibile
                    self.xsl_path = os.path.join(css_folder, self.xsl_files[0])
                
                # Aggiorna il menu a tendina se esiste già
                if hasattr(self, 'xsl_combo'):
                    self.xsl_combo['values'] = self.xsl_files
                    # Imposta il valore corrente
                    current_file = os.path.basename(self.xsl_path) if self.xsl_path else ''
                    if current_file in self.xsl_files:
                        self.xsl_combo.set(current_file)
            else:
                messagebox.showwarning("Attenzione", f"Cartella CSS non trovata: {css_folder}")
                self.xsl_path = None
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del foglio di stile: {e}")
            self.xsl_path = None

    def setup_ui(self):
        """Imposta l'interfaccia utente principale."""
        main_container = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=5, pady=5)
        main_container.pack(fill="both", expand=True)
        
        # Crea la top bar con i comandi
        commands_config = {
            'fast_download': self.on_fast_download,
            'select_period': self.on_select_period,
            'monthly_purchases': self.on_monthly_purchases,
            'monthly_sales': self.on_monthly_sales
        }
        
        self.top_bar = TopBar(main_container, self.icon_manager, commands_config)
        
        # Container per le due sezioni con padding ridotto
        split_container = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
        split_container.pack(fill="both", expand=True, pady=3)
        
        # Configurazione colonne con proporzioni più equilibrate
        split_container.grid_columnconfigure(0, weight=2)  # Sezione sinistra più piccola
        split_container.grid_columnconfigure(1, weight=5)  # Sezione destra più grande
        split_container.grid_rowconfigure(0, weight=1)

        # Sezione sinistra - Lista fatture (con padding ridotto)
        left_frame = tk.Frame(split_container, bg=Style.BACKGROUND_COLOR)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        self.create_invoice_list(left_frame)

        # Sezione destra - XML con stile e pulsante stampa (con padding ridotto)
        right_frame = tk.Frame(split_container, bg=Style.BACKGROUND_COLOR)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self.create_html_viewer(right_frame)

    def create_invoice_list(self, parent):
        """Crea la lista delle fatture su due righe."""
        list_frame = tk.Frame(parent, bg=Style.WHITE, relief="solid", bd=1)
        list_frame.pack(fill="both", expand=True)
        
        # Container per la listbox con scrollbar
        container = tk.Frame(list_frame, bg=Style.WHITE)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Frame per la listbox
        listbox_frame = tk.Frame(container, bg=Style.WHITE)
        listbox_frame.pack(side="left", fill="both", expand=True)
        
        # Listbox per le fatture
        self.invoice_listbox = tk.Listbox(
            listbox_frame,
            bg=Style.WHITE,
            fg=getattr(Style, 'TEXT_COLOR', 'black'),
            selectbackground=getattr(Style, 'PRIMARY_COLOR', '#007ACC'),
            selectforeground="white",
            font=("Arial", 9),
            bd=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.invoice_listbox.pack(fill="both", expand=True)
        
        # Scrollbar verticale
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.invoice_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.invoice_listbox.config(yscrollcommand=scrollbar.set)
        
        # Bind per la selezione
        self.invoice_listbox.bind('<<ListboxSelect>>', self.on_invoice_select)
        
        # Lista per memorizzare i percorsi dei file
        self.invoice_files = []

    def create_html_viewer(self, parent):
        """Crea il visualizzatore HTML con pulsante stampa e scrolling migliorato."""
        html_frame = tk.Frame(parent, bg=Style.WHITE, relief="solid", bd=1)
        html_frame.pack(fill="both", expand=True)
        
        # Barra superiore con pulsante stampa e menu foglio di stile
        toolbar = tk.Frame(html_frame, bg=Style.WHITE, height=35)
        toolbar.pack(fill="x", padx=5, pady=(5, 0))
        toolbar.pack_propagate(False)
        
        # Frame per i controlli a sinistra (foglio di stile)
        left_controls = tk.Frame(toolbar, bg=Style.WHITE)
        left_controls.pack(side="left", pady=5)
        
        # Label e menu a tendina per il foglio di stile
        ttk.Label(left_controls, text="Foglio di stile:", font=("Arial", 9), background=Style.WHITE).pack(side="left", padx=(0, 5))
        self.xsl_combo = ttk.Combobox(
            left_controls,
            values=self.xsl_files,
            state="readonly",
            width=35,
            font=("Arial", 9)
        )
        self.xsl_combo.pack(side="left")
        self.xsl_combo.bind("<<ComboboxSelected>>", self.on_xsl_changed)
        
        # Imposta il valore corrente se disponibile
        if self.xsl_path:
            current_file = os.path.basename(self.xsl_path)
            if current_file in self.xsl_files:
                self.xsl_combo.set(current_file)
        
        # Pulsante stampa allineato a destra
        self.print_button = tk.Button(
            toolbar,
            text="🖨 Stampa",
            font=("Arial", 9),
            bg=getattr(Style, 'PRIMARY_COLOR', '#007ACC'),
            fg="white",
            relief="flat",
            padx=15,
            pady=3,
            cursor="hand2",
            command=self.print_invoice,
            state="disabled"  # Inizialmente disabilitato
        )
        self.print_button.pack(side="right", pady=5)
        
        # Container principale per l'HTML viewer
        container = tk.Frame(html_frame, bg=Style.WHITE)
        container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Usa HtmlFrame normale per la visualizzazione corretta delle fatture
        self.html_frame = HtmlFrame(container, messages_enabled=False)
        self.html_frame.pack(fill="both", expand=True)

    def populate_list(self):
        """Popola la lista con i dati estratti dai file XML."""
        try:
            self.invoice_listbox.delete(0, tk.END)
            self.invoice_files.clear()
            
            xml_data = self.xml_parser.get_all_basic_data()
            
            if not xml_data:
                messagebox.showinfo("Informazione", "Nessun file XML trovato nella cartella specificata.")
                return

            for i, data in enumerate(xml_data):
                # Prima riga: Data e Numero
                line1 = f"{data['data']} - N. {data['numero']}"
                # Seconda riga: Soggetto (con indentazione per distinguerla)
                line2 = f"   {data['soggetto']}"
                
                # Inserisci entrambe le rigas
                self.invoice_listbox.insert(tk.END, line1)
                self.invoice_listbox.insert(tk.END, line2)
                
                # Memorizza il percorso del file solo per le righe dispari (prima riga di ogni fattura)
                self.invoice_files.extend([data['file_path'], data['file_path']])
                
                # Aggiungi una riga vuota per separare le fatture (opzionale)
                if i < len(xml_data) - 1:
                    self.invoice_listbox.insert(tk.END, "")
                    self.invoice_files.append(None)

        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento dei dati: {e}")

    def on_invoice_select(self, event):
        """Mostra la fattura formattata quando viene selezionato un elemento."""
        selection = self.invoice_listbox.curselection()
        if not selection:
            return
            
        selected_index = selection[0]
        
        # Controlla che l'indice sia valido e que ci sia un file associato
        if selected_index < len(self.invoice_files) and self.invoice_files[selected_index]:
            file_path = self.invoice_files[selected_index]
            if file_path and os.path.exists(file_path):
                self.current_xml_file = file_path  # Memorizza il file corrente
                self.display_formatted_xml(file_path)
                # Abilita il pulsante stampa quando una fattura è selezionata
                self.print_button.config(state="normal")

    def display_formatted_xml(self, file_path):
        """Visualizza il file XML formattato con il foglio di stile XSL."""
        try:
            if not self.xsl_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    xml_content = file.read()
                self.html_frame.load_html(f"<pre>{xml_content}</pre>")
                self.current_html = f"<pre>{xml_content}</pre>"
                return
                
            xml_tree = etree.parse(file_path)
            xsl_tree = etree.parse(self.xsl_path)
            transform = etree.XSLT(xsl_tree)
            self.current_html = str(transform(xml_tree))
            
            self.html_frame.load_html(self.current_html)
            
        except Exception as e:
            error_html = f"<html><body><h1>Errore</h1><p>{str(e)}</p></body></html>"
            self.html_frame.load_html(error_html)
            self.current_html = None
    
    def on_xsl_changed(self, event=None):
        """Gestisce il cambio del foglio di stile XSL."""
        try:
            selected_file = self.xsl_combo.get()
            if not selected_file:
                return
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_folder = os.path.join(current_dir, '../documents/css_fatture')
            new_xsl_path = os.path.join(css_folder, selected_file)
            
            if os.path.exists(new_xsl_path):
                self.xsl_path = new_xsl_path
                
                # Ricarica la fattura corrente se c'è una selezione
                if self.current_xml_file and os.path.exists(self.current_xml_file):
                    self.display_formatted_xml(self.current_xml_file)
            else:
                messagebox.showerror("Errore", f"File XSL non trovato: {new_xsl_path}")
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il cambio del foglio di stile: {e}")

    def print_invoice(self):
        """Stampa la fattura corrente."""
        if not self.current_html:
            messagebox.showwarning("Attenzione", "Nessuna fattura selezionata per la stampa.")
            return
        
        try:
            # Crea un file HTML temporaneo
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                # Aggiungi CSS per la stampa
                print_css = """
                <style>
                    @media print {
                        body { margin: 0; padding: 10px; font-size: 12px; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #000; padding: 4px; text-align: left; }
                        .no-print { display: none; }
                    }
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                </style>
                """
                
                # Combina CSS e HTML
                full_html = f"<html><head>{print_css}</head><body>{self.current_html}</body></html>"
                temp_file.write(full_html)
                temp_file_path = temp_file.name
            
            # Apri nel browser predefinito per la stampa
            webbrowser.open('file://' + temp_file_path)
            
            # Programma la rimozione del file temporaneo dopo un ritardo
            self.after(10000, lambda: self._cleanup_temp_file(temp_file_path))
            
            messagebox.showinfo("Stampa", "La fattura è stata aperta nel browser per la stampa.")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la preparazione per la stampa: {e}")

    def _cleanup_temp_file(self, file_path):
        """Rimuove il file temporaneo."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except:
            pass  # Ignora errori di pulizia

    def on_fast_download(self):

        try:
         # Apri la finestra di download rapido con log
         download_window = DownloadRapidoWindow(self)
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'apertura della finestra di download: {e}")

    def on_select_period(self):

        try:
            # Apri la finestra di download periodo con parametri
            periodo_window = DownloadPeriodoWindow(self)
        
        except Exception as e:
         messagebox.showerror("Errore", f"Errore durante l'apertura della finestra: {e}")

    def on_select_period(self):
        try:
            # Apri la finestra di download periodo con parametri
            periodo_window = DownloadPeriodoWindow(self)
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'apertura della finestra: {e}")

    def on_monthly_purchases(self):
        try:
            # Apri la finestra di download mensile per acquisti
            mensile_window = DownloadMensileWindow(self, "acquisti")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'apertura della finestra: {e}")
    
    def on_monthly_sales(self):
        try:
            # Apri la finestra di download mensile per vendite
            mensile_window = DownloadMensileWindow(self, "vendite")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'apertura della finestra: {e}")

    def execute_monthly_download(self, month, year, doc_type):
        """Esegue il download mensile utilizzando scarica_mensile.py"""
        try:
            # Ottieni il percorso dello script scarica_mensile.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(current_dir)
            script_path = os.path.join(project_dir, 'scripts', 'scarica_mensile.py')
            
            # Verifica che lo script esista
            if not os.path.exists(script_path):
                messagebox.showerror("Errore", f"Script non trovato: {script_path}")
                return
            
            # Esegui lo script scarica_mensile.py con i parametri appropriati
            subprocess.Popen([
                sys.executable, 
                script_path, 
                str(month), 
                str(year), 
                doc_type
            ])
            
            # Messaggio di conferma
            months = [
                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
            ]
            month_name = months[month - 1]
            
            messagebox.showinfo("Download Avviato", 
                              f"Download mensile {doc_type} avviato per {month_name} {year}")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'avvio del download: {e}")

    def execute_period_script(self):
        """Esegue lo script per il download del periodo."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(current_dir)
            script_path = os.path.join(project_dir, 'scripts', 'scarica_periodo.py')
            subprocess.Popen(['python', script_path])
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'esecuzione dello script: {e}")

    def save_config(self, start_date, end_date, date_option, venoacq):
        """Aggiorna i parametri nel file config.ini."""
        try:
            save_config(self.config, start_date, end_date, date_option, venoacq)
        except Exception as e:
            messagebox.showerror("Errore", str(e))

# Esegui l'app solo per test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Download Page")
    root.geometry("1200x700")
    app = DownloadPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()