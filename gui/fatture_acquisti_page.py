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
import glob

# Aggiungi il percorso per importare lo stile
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'style'))
from styles import Style

# Aggiungi il percorso per importare i moduli
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'modules'))

from styles import Style
from config_utils import load_config, save_config
from icon_manager import IconManager

# Importa il parser XML dalla cartella scripts
try:
    # Aggiungi il percorso della cartella scripts (dalla root del progetto)
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

class AcquistiMensiliPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        self.parent = parent
        
        # Inizializza i manager
        self.config = load_config()
        self.current_html = None
        self.xsl_path = None
        self.selected_year = None
        self.selected_month = None
        
        # Inizializza il parser XML
        self.xml_parser = XMLParser()
        
        # Ottieni il percorso delle fatture acquisti dalla configurazione
        try:
            self.fatture_acquisti_path = self.config['Parametri']['cartellaricevute']
            if not os.path.exists(self.fatture_acquisti_path):
                messagebox.showerror("Errore", f"Cartella fatture acquisti non trovata: {self.fatture_acquisti_path}")
                return
        except KeyError:
            messagebox.showerror("Errore", "Parametro 'cartellastampa' non trovato nel file config.ini")
            return
        
        self.setup_ui()
        self.setup_xsl_path()
        self.load_years()

    def setup_xsl_path(self):
        """Configura il percorso del foglio di stile XSL."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.xsl_path = os.path.join(current_dir, '../documents/css_fatture', 'FoglioStileAssoSoftware.xsl')
            
            if not os.path.exists(self.xsl_path):
                messagebox.showwarning("Attenzione", f"Foglio di stile XSL non trovato: {self.xsl_path}")
                self.xsl_path = None
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del foglio di stile: {e}")
            self.xsl_path = None

    def extract_css_from_xsl(self):
        """Estrae il CSS dal file XSL per utilizzarlo anche nella stampa."""
        if not self.xsl_path or not os.path.exists(self.xsl_path):
            return self.get_default_print_css()
        
        try:
            with open(self.xsl_path, 'r', encoding='utf-8') as file:
                xsl_content = file.read()
            
            # Cerca e estrae il blocco CSS dal file XSL
            css_start = xsl_content.find('<style')
            css_end = xsl_content.find('</style>') + 8
            
            if css_start != -1 and css_end != -1:
                css_block = xsl_content[css_start:css_end]
                
                # Aggiungi regole specifiche per la stampa mantenendo lo stile esistente
                print_css_additions = """
                <style>
                    /* Regole aggiuntive per la stampa */
                    @media print {
                        body { 
                            margin: 0.5cm !important; 
                            padding: 0 !important; 
                        }
                        .no-print { 
                            display: none !important; 
                        }
                        /* Evita interruzioni di pagina all'interno di elementi importanti */
                        table, .invoice-section { 
                            page-break-inside: avoid; 
                        }
                        /* Assicura che le tabelle si adattino alla pagina */
                        table { 
                            max-width: 100% !important; 
                            font-size: inherit !important;
                        }
                    }
                    /* Regole generali che migliorano la leggibilità */
                    body { 
                        font-size: 14px !important; 
                        line-height: 1.4 !important; 
                    }
                    table { 
                        font-size: 13px !important; 
                    }
                    th, td { 
                        font-size: 12px !important; 
                        padding: 6px !important; 
                    }
                </style>
                """
                
                return css_block + print_css_additions
            else:
                return self.get_enhanced_default_css()
                
        except Exception as e:
            print(f"Errore nell'estrazione del CSS dal file XSL: {e}")
            return self.get_enhanced_default_css()

    def get_enhanced_default_css(self):
        """CSS di default migliorato per una migliore leggibilità."""
        return """
        <style>
            @media print {
                body { 
                    margin: 0.5cm; 
                    padding: 0; 
                }
                .no-print { 
                    display: none; 
                }
                table { 
                    page-break-inside: avoid; 
                    max-width: 100%;
                }
            }
            
            body { 
                font-family: 'Arial', 'Helvetica', sans-serif; 
                font-size: 14px; 
                line-height: 1.5; 
                color: #333; 
                margin: 15px; 
            }
            
            .header { 
                text-align: center; 
                margin-bottom: 25px; 
                padding: 15px; 
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
            }
            
            .header h1 { 
                font-size: 20px; 
                margin: 0 0 10px 0; 
                color: #2c3e50; 
            }
            
            .header h2 { 
                font-size: 16px; 
                margin: 5px 0; 
                color: #34495e; 
                font-weight: normal; 
            }
            
            table { 
                border-collapse: collapse; 
                width: 100%; 
                margin: 15px 0; 
                font-size: 13px; 
                background-color: #fff; 
            }
            
            th { 
                background-color: #3498db; 
                color: white; 
                font-weight: bold; 
                padding: 10px 8px; 
                text-align: left; 
                border: 1px solid #2980b9; 
                font-size: 13px; 
            }
            
            td { 
                padding: 8px; 
                border: 1px solid #bdc3c7; 
                font-size: 12px; 
                line-height: 1.4; 
            }
            
            tr:nth-child(even) { 
                background-color: #f8f9fa; 
            }
            
            tr:hover { 
                background-color: #e3f2fd; 
            }
            
            .invoice-section { 
                margin: 20px 0; 
                padding: 15px; 
                border: 1px solid #e0e0e0; 
                border-radius: 5px; 
            }
            
            .invoice-section h3 { 
                margin: 0 0 15px 0; 
                color: #2c3e50; 
                font-size: 16px; 
                border-bottom: 2px solid #3498db; 
                padding-bottom: 5px; 
            }
            
            .text-right { 
                text-align: right; 
            }
            
            .text-center { 
                text-align: center; 
            }
            
            .font-weight-bold { 
                font-weight: bold; 
            }
            
            .total-row { 
                background-color: #e8f4fd !important; 
                font-weight: bold; 
            }
            
            .total-row td { 
                border-top: 2px solid #3498db; 
                padding: 10px 8px; 
            }
        </style>
        """

    def get_default_print_css(self):
        """CSS di fallback semplice ma leggibile."""
        return """
        <style>
            @media print {
                body { margin: 1cm; padding: 0; }
                .no-print { display: none; }
                table { page-break-inside: avoid; }
            }
            body { 
                font-family: Arial, sans-serif; 
                font-size: 14px; 
                line-height: 1.4; 
                margin: 20px; 
            }
            table { 
                border-collapse: collapse; 
                width: 100%; 
                margin: 10px 0; 
                font-size: 13px; 
            }
            th, td { 
                border: 1px solid #333; 
                padding: 6px; 
                text-align: left; 
                font-size: 12px; 
            }
            th { 
                background-color: #f0f0f0; 
                font-weight: bold; 
            }
            .header { 
                text-align: center; 
                margin-bottom: 20px; 
                font-size: 16px; 
                font-weight: bold; 
            }
        </style>
        """

    def setup_ui(self):
        """Imposta l'interfaccia utente principale."""
        main_container = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=5, pady=5)
        main_container.pack(fill="both", expand=True)
        
        # Sezione superiore per la selezione di anno e mese
        self.create_selection_bar(main_container)
        
        # Container per le due sezioni con padding ridotto
        split_container = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
        split_container.pack(fill="both", expand=True, pady=3)
        
        # Configurazione colonne con proporzioni equilibrate
        split_container.grid_columnconfigure(0, weight=2)  # Sezione sinistra
        split_container.grid_columnconfigure(1, weight=5)  # Sezione destra
        split_container.grid_rowconfigure(0, weight=1)

        # Sezione sinistra - Lista fatture
        left_frame = tk.Frame(split_container, bg=Style.BACKGROUND_COLOR)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        self.create_invoice_list(left_frame)

        # Sezione destra - XML con stile e pulsante stampa
        right_frame = tk.Frame(split_container, bg=Style.BACKGROUND_COLOR)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self.create_html_viewer(right_frame)

    def create_selection_bar(self, parent):
        """Crea la barra di selezione per anno e mese."""
        selection_frame = tk.Frame(parent, bg=Style.WHITE, relief="solid", bd=1)
        selection_frame.pack(fill="x", pady=(0, 5))
        
        # Container interno con padding
        inner_frame = tk.Frame(selection_frame, bg=Style.WHITE)
        inner_frame.pack(fill="x", padx=10, pady=10)
        
        # Titolo
        title_label = tk.Label(inner_frame, text="Selezione Periodo", 
                              font=("Arial", 12, "bold"), 
                              bg=Style.WHITE,
                              fg=getattr(Style, 'TEXT_COLOR', 'black'))
        title_label.pack(side="left")
        
        # Frame per i controlli
        controls_frame = tk.Frame(inner_frame, bg=Style.WHITE)
        controls_frame.pack(side="right")
        
        # Selezione Anno
        tk.Label(controls_frame, text="Anno:", font=("Arial", 10), bg=Style.WHITE).pack(side="left", padx=(0, 5))
        self.year_combo = ttk.Combobox(controls_frame, width=8, state="readonly", font=("Arial", 10))
        self.year_combo.pack(side="left", padx=(0, 15))
        self.year_combo.bind('<<ComboboxSelected>>', self.on_year_selected)
        
        # Selezione Mese
        tk.Label(controls_frame, text="Mese:", font=("Arial", 10), bg=Style.WHITE).pack(side="left", padx=(0, 5))
        self.month_combo = ttk.Combobox(controls_frame, width=12, state="readonly", font=("Arial", 10))
        self.month_combo.pack(side="left", padx=(0, 15))
        self.month_combo.bind('<<ComboboxSelected>>', self.on_month_selected)
        
        # Pulsante Aggiorna
        self.update_button = tk.Button(
            controls_frame,
            text="Aggiorna",
            font=("Arial", 10),
            bg=getattr(Style, 'PRIMARY_COLOR', '#007ACC'),
            fg="white",
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.update_invoice_list,
            state="disabled"
        )
        self.update_button.pack(side="left", padx=(0, 5))
        
        # Inizializza i mesi (disabilitato inizialmente)
        self.months = [
            ("01", "Gennaio"), ("02", "Febbraio"), ("03", "Marzo"), ("04", "Aprile"),
            ("05", "Maggio"), ("06", "Giugno"), ("07", "Luglio"), ("08", "Agosto"),
            ("09", "Settembre"), ("10", "Ottobre"), ("11", "Novembre"), ("12", "Dicembre")
        ]
        self.month_combo.config(state="disabled")

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
        """Crea il visualizzatore HTML con pulsante stampa."""
        html_frame = tk.Frame(parent, bg=Style.WHITE, relief="solid", bd=1)
        html_frame.pack(fill="both", expand=True)
        
        # Barra superiore con pulsante stampa
        toolbar = tk.Frame(html_frame, bg=Style.WHITE, height=35)
        toolbar.pack(fill="x", padx=5, pady=(5, 0))
        toolbar.pack_propagate(False)
        
        # Pulsante stampa allineato a destra
        self.print_button = tk.Button(
            toolbar,
            text="Stampa (Ctrl + P)",
            font=("Arial", 9),
            bg=getattr(Style, 'PRIMARY_COLOR', '#007ACC'),
            fg="white",
            relief="flat",
            padx=15,
            pady=3,
            cursor="hand2",
            command=self.print_invoice_browser,
            state="disabled"
        )
        self.print_button.pack(side="right", pady=5)
        
        # Container principale per l'HTML viewer
        container = tk.Frame(html_frame, bg=Style.WHITE)
        container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # HTML viewer per la visualizzazione corretta delle fatture
        self.html_frame = HtmlFrame(container, messages_enabled=False)
        self.html_frame.pack(fill="both", expand=True)
        
        # Bind della scorciatoia Ctrl+P (Windows) per aprire la fattura nel browser
        # registrala a livello di toplevel; il gestore verificherà che sia selezionata una fattura
        top = self.winfo_toplevel()
        try:
            top.bind_all("<Control-p>", self._on_print_shortcut)
            top.bind_all("<Control-P>", self._on_print_shortcut)
        except Exception:
            # Fallback: ignora se non è possibile registrare la scorciatoia
            pass

    def load_years(self):
        """Carica gli anni disponibili nella cartella delle fatture acquisti."""
        try:
            years = []
            if os.path.exists(self.fatture_acquisti_path):
                # Cerca tutte le cartelle che rappresentano anni
                for item in os.listdir(self.fatture_acquisti_path):
                    item_path = os.path.join(self.fatture_acquisti_path, item)
                    if os.path.isdir(item_path) and item.isdigit() and len(item) == 4:
                        years.append(item)
                
                years.sort(reverse=True)  # Anni più recenti per primi
                self.year_combo['values'] = years
                
                if years:
                    # Seleziona l'anno corrente se disponibile, altrimenti il più recente
                    current_year = str(datetime.now().year)
                    if current_year in years:
                        self.year_combo.set(current_year)
                    else:
                        self.year_combo.set(years[0])
                    self.on_year_selected(None)
            else:
                messagebox.showwarning("Attenzione", "Cartella delle fatture acquisti non trovata.")
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento degli anni: {e}")

    def on_year_selected(self, event):
        """Gestisce la selezione dell'anno."""
        selected_year = self.year_combo.get()
        if selected_year:
            self.selected_year = selected_year
            self.load_months(selected_year)
            self.month_combo.config(state="readonly")
            
            # Seleziona il mese corrente se disponibile
            current_month = str(datetime.now().month).zfill(2)
            month_values = [month[0] for month in self.months]
            if current_month in month_values and datetime.now().year == int(selected_year):
                month_name = next(month[1] for month in self.months if month[0] == current_month)
                self.month_combo.set(month_name)
                self.selected_month = current_month
                self.update_button.config(state="normal")

    def load_months(self, year):
        """Carica i mesi disponibili per l'anno selezionato."""
        try:
            year_path = os.path.join(self.fatture_acquisti_path, year)
            available_months = []
            
            if os.path.exists(year_path):
                # Controlla quali mesi hanno fatture
                for month_num, month_name in self.months:
                    month_path = os.path.join(year_path, month_num)
                    if os.path.exists(month_path):
                        # Verifica se ci sono file XML nella cartella del mese
                        xml_files = glob.glob(os.path.join(month_path, '*.[xX][mM][lL]'))
                        if xml_files:
                            available_months.append(month_name)
                
                self.month_combo['values'] = available_months
                if available_months:
                    self.month_combo.set('')  # Reset selezione
                else:
                    messagebox.showinfo("Informazione", f"Nessuna fattura trovata per l'anno {year}")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento dei mesi: {e}")

    def on_month_selected(self, event):
        """Gestisce la selezione del mese."""
        selected_month_name = self.month_combo.get()
        if selected_month_name:
            # Trova il numero del mese selezionato
            self.selected_month = next(month[0] for month in self.months if month[1] == selected_month_name)
            self.update_button.config(state="normal")

    def update_invoice_list(self):
        """Aggiorna la lista delle fatture per il periodo selezionato."""
        if not self.selected_year or not self.selected_month:
            messagebox.showwarning("Attenzione", "Seleziona prima anno e mese.")
            return
        
        try:
            # Pulisci la lista corrente
            self.invoice_listbox.delete(0, tk.END)
            self.invoice_files.clear()
            
            # Costruisci il percorso della cartella
            folder_path = os.path.join(self.fatture_acquisti_path, self.selected_year, self.selected_month)
            
            if not os.path.exists(folder_path):
                messagebox.showinfo("Informazione", f"Cartella non trovata per {self.selected_year}/{self.selected_month}")
                return
            
            # Carica i file XML
            xml_files = glob.glob(os.path.join(folder_path, '*.[xX][mM][lL]'))
            
            if not xml_files:
                messagebox.showinfo("Informazione", f"Nessuna fattura trovata per {self.selected_year}/{self.selected_month}")
                return
            
            # Ordina i file per data di modifica (più recenti prima)
            xml_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Estrai dati di base dai file XML e popola la lista
            invoices_data = []
            for file_path in xml_files:
                try:
                    data = self.extract_basic_invoice_data(file_path)
                    if data:
                        invoices_data.append(data)
                except Exception as e:
                    print(f"Errore nell'elaborazione del file {file_path}: {e}")
                    continue
            
            # Ordina le fatture per numero crescente
            invoices_data.sort(key=lambda x: x['cliente'].lower())
            
            # Popola la listbox
            for i, data in enumerate(invoices_data):
                # Prima riga: Data e Numero
                line1 = f"{data['data']} - N. {data['numero']}"
                # Seconda riga: Cliente (con indentazione)
                line2 = f"   {data['cliente']}"
                
                # Inserisci entrambe le righe
                self.invoice_listbox.insert(tk.END, line1)
                self.invoice_listbox.insert(tk.END, line2)
                
                # Memorizza il percorso del file
                self.invoice_files.extend([data['file_path'], data['file_path']])
                
                # Aggiungi una riga vuota per separare le fatture
                if i < len(invoices_data) - 1:
                    self.invoice_listbox.insert(tk.END, "")
                    self.invoice_files.append(None)
                    
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'aggiornamento della lista: {e}")

    def extract_basic_invoice_data(self, file_path):
        """Estrae i dati base da un file XML di fattura usando il parser."""
        try:
            # Usa il parser XML per estrarre i dati
            data = self.xml_parser.extract_basic_data(file_path)
            
            if not data:
                return None
            
            # Formatta la data
            data_formatted = self.format_date(data['data'])
            
            # Estrai numero intero per ordinamento
            numero_int = self.extract_invoice_number(data['numero'])
            
            return {
                'data': data_formatted,
                'data_raw': data['data'],
                'numero': data['numero'],
                'numero_int': numero_int,
                'cliente': data['soggetto'],
                'file_path': file_path
            }
            
        except Exception as e:
            print(f"Errore nell'estrazione dati da {file_path}: {e}")
            return None

    def format_date(self, date_string):
        """Formatta la data da YYYY-MM-DD a DD/MM/YYYY."""
        try:
            if date_string == "N/A" or not date_string:
                return "N/D"
            
            # La data potrebbe essere in formato YYYY-MM-DD
            if len(date_string) >= 10 and '-' in date_string:
                parts = date_string[:10].split('-')
                if len(parts) == 3:
                    year, month, day = parts
                    return f"{day}/{month}/{year}"
            
            # Se non è nel formato atteso, restituisci così come è
            return date_string
            
        except Exception:
            return date_string

    def extract_invoice_number(self, numero_str):
        """Estrae il numero intero dalla stringa del numero fattura per l'ordinamento."""
        try:
            if numero_str == "N/A" or not numero_str:
                return 0
            
            # Estrai solo i numeri dalla stringa
            import re
            numbers = re.findall(r'\d+', numero_str)
            if numbers:
                return int(numbers[0])  # Prende il primo numero trovato
            return 0
            
        except Exception:
            return 0

    def on_invoice_select(self, event):
        """Mostra la fattura formattata quando viene selezionato un elemento."""
        selection = self.invoice_listbox.curselection()
        if not selection:
            return
            
        selected_index = selection[0]
        
        # Controlla che l'indice sia valido e che ci sia un file associato
        if selected_index < len(self.invoice_files) and self.invoice_files[selected_index]:
            file_path = self.invoice_files[selected_index]
            if file_path and os.path.exists(file_path):
                self.display_formatted_xml(file_path)
                # Abilita il pulsante stampa quando una fattura è selezionata
                self.print_button.config(state="normal")
            else:
                # Disabilita il bottone se file non valido
                self.print_button.config(state="disabled")

    def display_formatted_xml(self, file_path):
        """Visualizza il file XML formattato con il foglio di stile XSL."""
        try:
            if not self.xsl_path:
                # Usa il metodo del parser per ottenere il contenuto XML
                xml_content = self.xml_parser.get_full_xml_content(file_path)
                self.html_frame.load_html(f"<pre>{xml_content}</pre>")
                self.current_html = f"<pre>{xml_content}</pre>"
                return
                
            # Usa il parser per applicare lo stile XSL
            xml_content = self.xml_parser.get_full_xml_content(file_path)
            styled_html = self.xml_parser.apply_xsl_stylesheet(xml_content, self.xsl_path)
            
            self.html_frame.load_html(styled_html)
            self.current_html = styled_html
            
        except Exception as e:
            error_html = f"<html><body><h1>Errore</h1><p>{str(e)}</p></body></html>"
            self.html_frame.load_html(error_html)
            self.current_html = None

    def print_invoice(self):
        """Stampa direttamente la fattura corrente utilizzando lo stesso CSS della visualizzazione."""
        pass  # Rimosso metodo di stampa diretta; ora si usa print_invoice_browser

    def print_invoice_browser(self):
        """Metodo di fallback per stampa tramite browser utilizzando lo stesso CSS."""
        try:
            if not self.current_html:
                messagebox.showwarning("Attenzione", "Nessuna fattura selezionata per la stampa.")
                return

            # Crea un file HTML temporaneo
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                # Usa lo stesso CSS dell'XSL per la stampa
                print_css = self.extract_css_from_xsl()
                
                # Prepara l'HTML completo
                full_html = self.prepare_html_for_print(self.current_html, print_css)
                temp_file.write(full_html)
                temp_file_path = temp_file.name
            
            # Apri nel browser predefinito per la stampa
            webbrowser.open('file://' + temp_file_path.replace('\\', '/'))
            
            # Programma la rimozione del file temporaneo dopo un ritardo
            self.after(10000, lambda: self._cleanup_temp_file(temp_file_path))
        except Exception as e:
            # Messaggio di errore in caso di problemi
            messagebox.showerror("Errore", f"Errore durante la preparazione per la stampa: {e}")

    def _on_print_shortcut(self, event=None):
        """Gestisce la combinazione Ctrl+P per aprire la fattura nel browser."""
        # Se il bottone è abilitato e c'è HTML caricato, apri nel browser
        if getattr(self, 'print_button', None) and self.print_button.cget('state') == 'normal' and self.current_html:
            try:
                self.print_invoice_browser()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile aprire la fattura nel browser: {e}")
            # Previeni ulteriore propagazione dell'evento
            return "break"
        else:
            # Quando non c'è fattura selezionata, avvisa l'utente (ma non mostrare messaggi ripetuti)
            # Mostra solo se la finestra è attiva e il widget selezionato non è la listbox (evitiamo popup indesiderati)
            messagebox.showwarning("Attenzione", "Seleziona prima una fattura da stampare.")
            return "break"

    def prepare_html_for_print(self, html_content, print_css):
        """Prepara l'HTML per la stampa, incorporando il CSS necessario."""
        # Incapsula l'HTML e il CSS in una struttura di base
        full_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Fattura</title>
            {print_css}  <!-- Includi il CSS per la stampa -->
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        return full_html

    def _cleanup_temp_file(self, file_path):
        """Rimuove il file temporaneo dopo la stampa."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Errore nella rimozione del file temporaneo {file_path}: {e}")

