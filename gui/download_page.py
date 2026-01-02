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
            'monthly_sales': self.on_monthly_sales,
            'show_history': self.show_download_history
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
        # Bind per le frecce per gestire la navigazione intelligente
        self.invoice_listbox.bind('<Up>', self.on_key_navigation)
        self.invoice_listbox.bind('<Down>', self.on_key_navigation)
        self.invoice_listbox.bind('<Button-1>', self.on_mouse_click)
        
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
        
        # Frame per i pulsanti a destra
        right_buttons = tk.Frame(toolbar, bg=Style.WHITE)
        right_buttons.pack(side="right", pady=5)
        
        # Pulsante stampa
        self.print_button = tk.Button(
            right_buttons,
            text="🖨 Stampa (Ctrl+P)",
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
        self.print_button.pack(side="right")
        
        # Bind per la combinazione di tasti CTRL+P
        self.bind_all('<Control-p>', lambda event: self.print_invoice())
        self.bind_all('<Control-P>', lambda event: self.print_invoice())
        
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
                # Prima riga: Data e Numero (selezionabile)
                line1 = f"{data['data']} - N. {data['numero']}"
                # Seconda riga: Soggetto (non selezionabile, solo visualizzazione)
                line2 = f"   {data['soggetto']}"
                
                # Inserisci entrambe le righe
                self.invoice_listbox.insert(tk.END, line1)
                self.invoice_listbox.insert(tk.END, line2)
                
                # Memorizza il percorso del file per entrambe le righe
                self.invoice_files.extend([data['file_path'], data['file_path']])
                
                # Aggiungi una riga vuota per separare le fatture (opzionale)
                if i < len(xml_data) - 1:
                    self.invoice_listbox.insert(tk.END, "")
                    self.invoice_files.append(None)

        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento dei dati: {e}")

    def is_selectable_row(self, index):
        """Verifica se una riga è selezionabile (solo le righe con data/numero)."""
        if index < 0 or index >= len(self.invoice_files):
            return False
        # Le righe selezionabili sono quelle con un file_path (non None)
        # e che corrispondono alla prima riga di ogni fattura (indici pari: 0, 2, 4, ...)
        # Escludiamo anche le righe vuote (None)
        if self.invoice_files[index] is None:
            return False
        # Controlla se è la prima riga di una fattura (indice pari o dopo una riga vuota)
        # Per semplicità, consideriamo selezionabili solo le righe con file_path
        return self.invoice_files[index] is not None
    
    def find_previous_selectable(self, current_index):
        """Trova la riga selezionabile precedente."""
        for i in range(current_index - 1, -1, -1):
            if self.is_selectable_row(i):
                return i
        return None
    
    def find_next_selectable(self, current_index):
        """Trova la riga selezionabile successiva."""
        for i in range(current_index + 1, len(self.invoice_files)):
            if self.is_selectable_row(i):
                return i
        return None
    
    def on_key_navigation(self, event):
        """Gestisce la navigazione con le frecce per saltare le righe non selezionabili."""
        selection = self.invoice_listbox.curselection()
        if not selection:
            return
        
        current_index = selection[0]
        
        # Se la riga corrente non è selezionabile, trova quella corretta
        if not self.is_selectable_row(current_index):
            if event.keysym == 'Up':
                target_index = self.find_previous_selectable(current_index)
            else:  # Down
                target_index = self.find_next_selectable(current_index)
            
            if target_index is not None:
                # Seleziona la riga corretta dopo un breve ritardo
                self.after_idle(lambda: self.invoice_listbox.selection_clear(0, tk.END))
                self.after_idle(lambda idx=target_index: self.invoice_listbox.selection_set(idx))
                self.after_idle(lambda idx=target_index: self.invoice_listbox.see(idx))
                # Triggera l'evento di selezione
                self.after_idle(lambda: self.on_invoice_select(None))
                return "break"
        
        # Se la riga è selezionabile, controlla se la prossima riga è selezionabile
        # Se non lo è, salta direttamente alla prossima fattura
        if event.keysym == 'Down':
            next_index = current_index + 1
            if next_index < len(self.invoice_files) and not self.is_selectable_row(next_index):
                # Salta alla prossima riga selezionabile
                target_index = self.find_next_selectable(next_index)
                if target_index is not None:
                    self.after_idle(lambda: self.invoice_listbox.selection_clear(0, tk.END))
                    self.after_idle(lambda idx=target_index: self.invoice_listbox.selection_set(idx))
                    self.after_idle(lambda idx=target_index: self.invoice_listbox.see(idx))
                    self.after_idle(lambda: self.on_invoice_select(None))
                    return "break"
        elif event.keysym == 'Up':
            prev_index = current_index - 1
            if prev_index >= 0 and not self.is_selectable_row(prev_index):
                # Salta alla riga selezionabile precedente
                target_index = self.find_previous_selectable(prev_index)
                if target_index is not None:
                    self.after_idle(lambda: self.invoice_listbox.selection_clear(0, tk.END))
                    self.after_idle(lambda idx=target_index: self.invoice_listbox.selection_set(idx))
                    self.after_idle(lambda idx=target_index: self.invoice_listbox.see(idx))
                    self.after_idle(lambda: self.on_invoice_select(None))
                    return "break"
    
    def on_mouse_click(self, event):
        """Gestisce il click del mouse per selezionare solo le righe selezionabili."""
        # Trova quale riga è stata cliccata
        clicked_index = self.invoice_listbox.nearest(event.y)
        
        # Se la riga cliccata non è selezionabile, trova la riga selezionabile più vicina
        if not self.is_selectable_row(clicked_index):
            # Cerca la riga selezionabile più vicina (preferibilmente quella sopra)
            target_index = self.find_previous_selectable(clicked_index)
            if target_index is None:
                target_index = self.find_next_selectable(clicked_index)
            
            if target_index is not None:
                self.invoice_listbox.selection_clear(0, tk.END)
                self.invoice_listbox.selection_set(target_index)
                self.invoice_listbox.see(target_index)
                self.on_invoice_select(None)
                return "break"
    
    def on_invoice_select(self, event):
        """Mostra la fattura formattata quando viene selezionato un elemento."""
        selection = self.invoice_listbox.curselection()
        if not selection:
            return
            
        selected_index = selection[0]
        
        # Se la riga selezionata non è selezionabile, trova quella corretta
        if not self.is_selectable_row(selected_index):
            target_index = self.find_previous_selectable(selected_index)
            if target_index is None:
                target_index = self.find_next_selectable(selected_index)
            if target_index is not None:
                self.invoice_listbox.selection_clear(0, tk.END)
                self.invoice_listbox.selection_set(target_index)
                selected_index = target_index
        
        # Controlla che l'indice sia valido e che ci sia un file associato
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
                # Usa direttamente l'HTML generato dal foglio di stile XSL,
                # lasciando la gestione degli stili alla trasformazione XSL scelta dall'utente
                full_html = self.current_html
                temp_file.write(full_html)
                temp_file_path = temp_file.name
            
            # Apri nel browser predefinito per la stampa
            webbrowser.open('file://' + temp_file_path)
            
            # Programma la rimozione del file temporaneo dopo un ritardo
            self.after(10000, lambda: self._cleanup_temp_file(temp_file_path))
            
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
        """Gestisce il click sul pulsante download rapido con conferma."""
        # Chiedi conferma all'utente
        if not messagebox.askyesno("Conferma Download Rapido", 
                                   "Sei sicuro di voler procedere con il download rapido?"):
            return
        
        try:
            # Apri la finestra di download rapido con log
            download_window = DownloadRapidoWindow(self)
            
            # Intercetta la chiusura della finestra per aggiornare la lista
            def on_close():
                download_window.destroy()
                # Aggiorna la lista delle fatture dopo il download
                self.populate_list()
            
            # Sostituisci il metodo destroy per intercettare la chiusura
            original_destroy = download_window.destroy
            def destroy_with_callback():
                original_destroy()
                # Aggiorna la lista dopo un breve ritardo per assicurarsi che la finestra sia chiusa
                self.after(100, self.populate_list)
            
            download_window.destroy = destroy_with_callback
            download_window.protocol("WM_DELETE_WINDOW", destroy_with_callback)
        
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
    
    def show_download_history(self):
        """Mostra la finestra con lo storico dei download rapidi."""
        try:
            # Importa il modulo download_history
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            scripts_dir = os.path.join(project_root, 'scripts')
            
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            
            from download_history import DownloadHistory
            
            # Crea il percorso del file storico
            history_file = os.path.join(project_root, "download_history.json")
            history = DownloadHistory(history_file)
            
            # Carica lo storico
            downloads = history.get_recent_downloads()
            
            # Crea la finestra
            history_window = DownloadHistoryWindow(self, downloads)
            
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile importare il modulo download_history: {e}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento dello storico: {e}")


class DownloadHistoryWindow(tk.Toplevel):
    """Finestra per visualizzare lo storico dei download rapidi."""
    
    def __init__(self, parent, downloads):
        super().__init__(parent)
        
        self.parent = parent
        self.downloads = downloads
        
        self.title("📋 Storico Download Rapidi")
        self.geometry("900x600")
        self.resizable(True, True)
        self.transient(parent)
        
        self.create_widgets()
        self.center_window()
    
    def center_window(self):
        """Centra la finestra sullo schermo."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Crea i widget della finestra."""
        # Frame principale
        main_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="📋 Storico Download Rapidi",
            font=('Arial', 14, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 15))
        
        # Info se non ci sono download
        if not self.downloads:
            no_data_label = tk.Label(
                main_frame,
                text="Nessun download registrato nello storico.",
                font=('Arial', 11),
                bg="#FFFFFF",
                fg="#666666"
            )
            no_data_label.pack(pady=50)
            
            # Pulsante chiudi
            btn_chiudi = tk.Button(
                main_frame,
                text="Chiudi",
                command=self.destroy,
                bg="#607D8B",
                fg="white",
                font=('Arial', 10, 'bold'),
                cursor="hand2",
                padx=20,
                pady=5
            )
            btn_chiudi.pack(pady=20)
            return
        
        # Frame per la lista con scrollbar
        list_frame = tk.Frame(main_frame, bg="#FFFFFF")
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Treeview per mostrare i download
        columns = ('data', 'ora', 'fatture_count')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='tree headings',
            height=15
        )
        
        # Configura le colonne
        self.tree.heading('#0', text='Download', anchor='w')
        self.tree.heading('data', text='Data', anchor='center')
        self.tree.heading('ora', text='Ora', anchor='center')
        self.tree.heading('fatture_count', text='N. Fatture', anchor='center')
        
        self.tree.column('#0', width=300, minwidth=200)
        self.tree.column('data', width=120, minwidth=100, anchor='center')
        self.tree.column('ora', width=100, minwidth=80, anchor='center')
        self.tree.column('fatture_count', width=100, minwidth=80, anchor='center')
        
        # Scrollbar verticale
        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        
        # Scrollbar orizzontale
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=scrollbar_x.set)
        
        # Pack del treeview e scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Popola il treeview
        self.populate_tree()
        
        # Bind per espandere/contrarre i nodi
        self.tree.bind('<Double-Button-1>', self.on_item_double_click)
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg="#FFFFFF")
        button_frame.pack(fill="x")
        
        # Pulsante chiudi
        btn_chiudi = tk.Button(
            button_frame,
            text="Chiudi",
            command=self.destroy,
            bg="#607D8B",
            fg="white",
            font=('Arial', 10, 'bold'),
            cursor="hand2",
            padx=20,
            pady=5
        )
        btn_chiudi.pack(side="right")
    
    def populate_tree(self):
        """Popola il treeview con i dati dello storico."""
        for i, download in enumerate(self.downloads):
            # Formatta la data in formato italiano
            try:
                data_obj = datetime.strptime(download['data'], '%Y-%m-%d')
                data_formattata = data_obj.strftime('%d/%m/%Y')
            except:
                data_formattata = download['data']
            
            # Crea il nodo principale
            num_fatture = len(download.get('fatture', []))
            download_id = self.tree.insert(
                '',
                'end',
                text=f"Download #{i+1}",
                values=(data_formattata, download['ora'], num_fatture),
                tags=('download',)
            )
            
            # Aggiungi le fatture come nodi figli
            for fattura in download.get('fatture', []):
                self.tree.insert(
                    download_id,
                    'end',
                    text=f"N. {fattura['numero']} - {fattura['soggetto']}",
                    values=('', '', fattura['data']),
                    tags=('fattura',)
                )
        
        # Configura i tag per lo stile
        self.tree.tag_configure('download', background='#E3F2FD')
        self.tree.tag_configure('fattura', background='#FFFFFF')
    
    def on_item_double_click(self, event):
        """Gestisce il doppio click su un elemento per espandere/contrarre."""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            # Espandi o contrai il nodo
            if self.tree.get_children(item):
                if self.tree.item(item, 'open'):
                    self.tree.item(item, open=False)
                else:
                    self.tree.item(item, open=True)

# Esegui l'app solo per test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Download Page")
    root.geometry("1200x700")
    app = DownloadPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()