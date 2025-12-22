import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
import sys
import configparser
import json
from pathlib import Path
from typing import Optional, Callable

# Aggiungi il percorso per importare lo stile
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'style'))
from styles import Style


class IconButton:
    """Classe per gestire i pulsanti delle icone"""
    def __init__(self, parent, icon_path: str, size: tuple, command: Callable, bg_color: str):
        self.parent = parent
        self.icon_path = icon_path
        self.size = size
        self.command = command
        self.bg_color = bg_color
        
    def create(self) -> Optional[tk.Button]:
        try:
            icon_img = Image.open(self.icon_path).resize(self.size)
            icon_photo = ImageTk.PhotoImage(icon_img)
            button = tk.Button(
                self.parent,
                image=icon_photo,
                bg=self.bg_color,
                bd=0,
                activebackground=self.bg_color,
                command=self.command
            )
            button.image = icon_photo
            return button
        except Exception as e:
            print(f"Errore nel caricamento dell'icona {self.icon_path}: {e}")
            return None


class CaricaListaWindow(tk.Toplevel):
    """Finestra per caricare una lista di fatture"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.selected_file = None
        self.selected_file_estero = None
        self.caricamento_completato = False  # Flag per indicare se il caricamento è stato completato
        
        self.title("Carica Lista")
        self.geometry("500x400")
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.resizable(False, False)
        
        # Centra la finestra
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Imposta l'interfaccia della finestra"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        # Frame per il pulsante Sfoglia - File Italia
        file_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        file_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            file_frame,
            text="File Italia:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.file_label = tk.Label(
            file_frame,
            text="Nessun file selezionato",
            font=("Arial", 9),
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            anchor="w"
        )
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_sfoglia = tk.Button(
            file_frame,
            text="Sfoglia",
            font=("Arial", 10),
            bg="#4b6cb7",
            fg="white",
            activebackground="#3a5a9f",
            activeforeground="white",
            cursor="hand2",
            padx=15,
            pady=5,
            command=self.browse_file
        )
        btn_sfoglia.pack(side="right")
        
        # Frame per il pulsante Sfoglia - File Estero (facoltativo)
        file_estero_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        file_estero_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            file_estero_frame,
            text="File Estero:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.file_estero_label = tk.Label(
            file_estero_frame,
            text="Nessun file selezionato (facoltativo)",
            font=("Arial", 9),
            bg=Style.BACKGROUND_COLOR,
            fg="#666666",
            anchor="w"
        )
        self.file_estero_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_sfoglia_estero = tk.Button(
            file_estero_frame,
            text="Sfoglia",
            font=("Arial", 10),
            bg="#4b6cb7",
            fg="white",
            activebackground="#3a5a9f",
            activeforeground="white",
            cursor="hand2",
            padx=15,
            pady=5,
            command=self.browse_file_estero
        )
        btn_sfoglia_estero.pack(side="right")
        
        # Frame per la selezione anno
        year_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        year_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            year_frame,
            text="Anno:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(
            year_frame,
            textvariable=self.year_var,
            width=20,
            state="readonly",
            font=("Arial", 10)
        )
        self.year_combo.pack(side="left", fill="x", expand=True)
        
        # Popola gli anni (dal 2020 al 2030)
        years = [str(year) for year in range(2020, 2031)]
        self.year_combo['values'] = years
        
        # Frame per la selezione mese
        month_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        month_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            month_frame,
            text="Mese:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(
            month_frame,
            textvariable=self.month_var,
            width=20,
            state="readonly",
            font=("Arial", 10)
        )
        self.month_combo.pack(side="left", fill="x", expand=True)
        
        # Popola i mesi
        mesi = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        self.month_combo['values'] = mesi
        
        # Bottone CARICA
        btn_carica = tk.Button(
            main_frame,
            text="CARICA",
            font=("Arial", 11, "bold"),
            bg="#4b6cb7",
            fg="white",
            activebackground="#3a5a9f",
            activeforeground="white",
            cursor="hand2",
            padx=30,
            pady=10,
            command=self.on_carica_click
        )
        btn_carica.pack(pady=(10, 0))
    
    def browse_file(self):
        """Apre il dialog per selezionare un file Italia"""
        file_path = filedialog.askopenfilename(
            title="Seleziona file acquisti Italia",
            filetypes=[
                ("Tutti i file", "*.*"),
                ("File Excel", "*.xlsx;*.xls"),
                ("File CSV", "*.csv"),
                ("File di testo", "*.txt")
            ]
        )
        
        if file_path:
            self.selected_file = file_path
            # Mostra solo il nome del file (non il percorso completo)
            file_name = os.path.basename(file_path)
            self.file_label.config(text=file_name, fg="black")
    
    def browse_file_estero(self):
        """Apre il dialog per selezionare un file Estero"""
        file_path = filedialog.askopenfilename(
            title="Seleziona file acquisti Estero",
            filetypes=[
                ("Tutti i file", "*.*"),
                ("File Excel", "*.xlsx;*.xls"),
                ("File CSV", "*.csv"),
                ("File di testo", "*.txt")
            ]
        )
        
        if file_path:
            self.selected_file_estero = file_path
            # Mostra solo il nome del file (non il percorso completo)
            file_name = os.path.basename(file_path)
            self.file_estero_label.config(text=file_name, fg="black")
    
    def on_carica_click(self):
        """Gestisce il click sul bottone CARICA"""
        if not self.selected_file:
            messagebox.showwarning("Attenzione", "Seleziona un file prima di procedere")
            return
        
        year = self.year_var.get()
        month = self.month_var.get()
        
        if not year:
            messagebox.showwarning("Attenzione", "Seleziona un anno")
            return
        
        if not month:
            messagebox.showwarning("Attenzione", "Seleziona un mese")
            return
        
        try:
            # Converti l'anno in intero
            anno = int(year)
            
            # Converti il nome del mese in numero (1-12)
            mesi_nomi = {
                "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
                "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
                "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
            }
            mese = mesi_nomi.get(month)
            if not mese:
                messagebox.showerror("Errore", f"Mese non valido: {month}")
                return
            
            # Importa lo script per processare il CSV
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            scripts_dir = os.path.join(project_root, 'scripts')
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            
            from carica_lista_csv import processa_carica_lista
            
            # Se il file estero non è selezionato, chiedi conferma
            if not self.selected_file_estero:
                risposta = messagebox.askyesno(
                    "Conferma",
                    "SEI SICURO CHE NON CI SONO FATTURE DI ACQUISTO ESTERO IN QUESTO MESE?",
                    icon="question"
                )
                if not risposta:
                    return  # L'utente ha annullato
            
            # Processa il caricamento (prima volta senza sovrascrivere)
            successo, messaggio, percorso_json = processa_carica_lista(
                self.selected_file, anno, mese, 
                file_estero=self.selected_file_estero,
                sovrascrivi=False
            )
            
            if messaggio == "file_esistente":
                # Chiedi conferma all'utente
                risposta = messagebox.askyesno(
                    "File esistente",
                    f"Un file JSON esiste già per {month} {anno}.\n\nVuoi sostituirlo con il nuovo file?",
                    icon="question"
                )
                
                if risposta:
                    # L'utente ha confermato, procedi con la sovrascrittura
                    successo, messaggio, percorso_json = processa_carica_lista(
                        self.selected_file, anno, mese,
                        file_estero=self.selected_file_estero,
                        sovrascrivi=True
                    )
                    if successo:
                        messagebox.showinfo("Successo", messaggio)
                        self.caricamento_completato = True
                        self.destroy()
                    else:
                        messagebox.showerror("Errore", messaggio)
                else:
                    # L'utente ha annullato
                    return
            elif successo:
                messagebox.showinfo("Successo", messaggio)
                self.caricamento_completato = True
                # Chiudi la finestra dopo il successo
                self.destroy()
            else:
                messagebox.showerror("Errore", messaggio)
        
        except ValueError:
            messagebox.showerror("Errore", "Anno non valido")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il caricamento: {str(e)}")


class FattureMancantiWindow(tk.Toplevel):
    """Finestra per mostrare le fatture mancanti"""
    
    def __init__(self, parent, fatture_mancanti, anno, mese):
        super().__init__(parent)
        self.parent = parent
        
        mesi_nomi = {
            1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
            5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
            9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
        }
        mese_nome = mesi_nomi.get(mese, f"Mese {mese}")
        
        self.title(f"Fatture Mancanti - {mese_nome} {anno}")
        self.geometry("900x500")
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.resizable(True, True)
        
        # Centra la finestra
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui(fatture_mancanti, anno, mese)
    
    def setup_ui(self, fatture_mancanti, anno, mese):
        """Imposta l'interfaccia della finestra"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text=f"Fatture mancanti: {len(fatture_mancanti)}",
            font=("Arial", 12, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        )
        title_label.pack(pady=(0, 15))
        
        # Frame per la tabella con scrollbar
        table_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill="both", expand=True)
        
        # Scrollbar verticale
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")
        
        # Scrollbar orizzontale
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # Tabella
        columns = ("Numero", "Data", "Fornitore", "P.IVA", "Codice", "Imponibile")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            height=15
        )
        
        # Configura le colonne
        self.tree.heading("Numero", text="NUMERO FATTURA")
        self.tree.heading("Data", text="DATA EMISSIONE")
        self.tree.heading("Fornitore", text="FORNITORE")
        self.tree.heading("P.IVA", text="PARTITA IVA")
        self.tree.heading("Codice", text="CODICE FATTURA")
        self.tree.heading("Imponibile", text="IMPONIBILE")
        
        self.tree.column("Numero", width=120, anchor="w")
        self.tree.column("Data", width=100, anchor="w")
        self.tree.column("Fornitore", width=200, anchor="w")
        self.tree.column("P.IVA", width=120, anchor="w")
        self.tree.column("Codice", width=150, anchor="w")
        self.tree.column("Imponibile", width=120, anchor="e")
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # Popola la tabella
        for idx, fattura in enumerate(fatture_mancanti):
            numero = fattura.get("numero_fattura", "")
            data = fattura.get("data_emissione", "")
            fornitore = fattura.get("denominazione_fornitore", "")
            piva = fattura.get("partita_iva_fornitore", "")
            codice = fattura.get("codice_fattura", "")
            imponibile = fattura.get("imponibile", "")
            
            # Formatta l'imponibile
            if imponibile:
                try:
                    imponibile_float = float(str(imponibile).replace(",", "."))
                    imponibile_str = f"{imponibile_float:.2f}".replace(".", ",")
                except:
                    imponibile_str = str(imponibile)
            else:
                imponibile_str = ""
            
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=(
                numero, data, fornitore, piva, codice, imponibile_str
            ), tags=(tag,))
        
        # Configura gli stili per le righe alternate
        self.tree.tag_configure('evenrow', background='#f0f0f0')
        self.tree.tag_configure('oddrow', background='white')
        
        # Bottone CHIUDI
        btn_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.pack(pady=(15, 0))
        
        btn_chiudi = tk.Button(
            btn_frame,
            text="CHIUDI",
            font=("Arial", 11, "bold"),
            bg="#4b6cb7",
            fg="white",
            activebackground="#3a5a9f",
            activeforeground="white",
            cursor="hand2",
            padx=30,
            pady=8,
            command=self.destroy
        )
        btn_chiudi.pack()


class SelezionaVerificaWindow(tk.Toplevel):
    """Finestra per selezionare anno e mese per la verifica"""
    
    def __init__(self, parent, anni_disponibili, mesi_per_anno):
        super().__init__(parent)
        self.parent = parent
        self.anno_selezionato = None
        self.mese_selezionato = None
        self.confermato = False
        self.mesi_per_anno = mesi_per_anno  # Dizionario: {anno: set(mesi)}
        
        self.title("Seleziona Anno e Mese")
        self.geometry("400x250")
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.resizable(False, False)
        
        # Centra la finestra
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui(anni_disponibili)
    
    def setup_ui(self, anni_disponibili):
        """Imposta l'interfaccia della finestra"""
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        # Frame per la selezione anno
        year_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        year_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            year_frame,
            text="Anno:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(
            year_frame,
            textvariable=self.year_var,
            width=20,
            state="readonly",
            font=("Arial", 10)
        )
        self.year_combo.pack(side="left", fill="x", expand=True)
        self.year_combo['values'] = [str(anno) for anno in sorted(anni_disponibili, reverse=True)]
        
        # Binding per aggiornare i mesi quando viene selezionato un anno
        self.year_var.trace('w', self.on_year_selected)
        
        # Frame per la selezione mese
        month_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        month_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            month_frame,
            text="Mese:",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(0, 10))
        
        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(
            month_frame,
            textvariable=self.month_var,
            width=20,
            state="readonly",
            font=("Arial", 10)
        )
        self.month_combo.pack(side="left", fill="x", expand=True)
        
        # Inizialmente i mesi sono vuoti (verranno popolati quando si seleziona un anno)
        self.month_combo['values'] = []
        
        # Bottone VERIFICA
        btn_verifica = tk.Button(
            main_frame,
            text="VERIFICA",
            font=("Arial", 11, "bold"),
            bg="#4b6cb7",
            fg="white",
            activebackground="#3a5a9f",
            activeforeground="white",
            cursor="hand2",
            padx=30,
            pady=10,
            command=self.on_verifica_click
        )
        btn_verifica.pack(pady=(10, 0))
    
    def on_year_selected(self, *args):
        """Aggiorna i mesi disponibili quando viene selezionato un anno"""
        selected_year_str = self.year_var.get()
        if not selected_year_str:
            self.month_combo['values'] = []
            self.month_var.set("")
            return
        
        try:
            selected_year = int(selected_year_str)
            # Ottieni i mesi disponibili per l'anno selezionato
            mesi_disponibili = self.mesi_per_anno.get(selected_year, set())
            
            if not mesi_disponibili:
                self.month_combo['values'] = []
                self.month_var.set("")
                return
            
            # Converti i numeri dei mesi in nomi
            mesi_nomi = [
                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
            ]
            mesi_disponibili_nomi = [mesi_nomi[m-1] for m in sorted(mesi_disponibili)]
            self.month_combo['values'] = mesi_disponibili_nomi
            self.month_var.set("")  # Reset della selezione del mese
        except ValueError:
            self.month_combo['values'] = []
            self.month_var.set("")
    
    def on_verifica_click(self):
        """Gestisce il click sul bottone VERIFICA"""
        year = self.year_var.get()
        month = self.month_var.get()
        
        if not year:
            messagebox.showwarning("Attenzione", "Seleziona un anno")
            return
        
        if not month:
            messagebox.showwarning("Attenzione", "Seleziona un mese")
            return
        
        try:
            anno = int(year)
            
            # Converti il nome del mese in numero (1-12)
            mesi_nomi = {
                "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
                "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
                "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
            }
            mese = mesi_nomi.get(month)
            if not mese:
                messagebox.showerror("Errore", f"Mese non valido: {month}")
                return
            
            self.anno_selezionato = anno
            self.mese_selezionato = mese
            self.confermato = True
            self.destroy()
        
        except ValueError:
            messagebox.showerror("Errore", "Anno non valido")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la selezione: {str(e)}")


class VerificaFtAcquistoPage(tk.Frame):
    """Pagina per la verifica delle fatture di acquisto"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        self.parent = parent
        
        # Leggi il percorso delle fatture ricevute
        self.cartella_ricevute = self.get_cartella_ricevute()
        
        if not self.cartella_ricevute:
            return
        
        self.configure_style()
        self.setup_ui()
        self.load_months()
    
    def configure_style(self):
        """Configura lo stile per la tabella (stile documenti_page)"""
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview.Heading", 
                       background=Style.MENU_HEADER_BG,
                       foreground=Style.MENU_HEADER_FG,
                       font=("Arial", 10, "bold"),
                       padding=(5, 8),
                       relief="solid",
                       borderwidth=1,
                       lightcolor="#E0E0E0",
                       darkcolor="#E0E0E0")
        style.configure("Treeview",
                       font=("Arial", 9),
                       rowheight=26,
                       background="#FFFFFF",
                       foreground="#000000",
                       fieldbackground="#FFFFFF",
                       borderwidth=1,
                       relief="solid",
                       lightcolor="#E8E8E8",
                       darkcolor="#E8E8E8")
        style.map("Treeview",
                 background=[('selected', '#4b6cb7')],
                 foreground=[('selected', 'white')])
    
    def get_cartella_ricevute(self):
        """Legge il percorso della cartella ricevute da config.ini"""
        try:
            config = configparser.ConfigParser()
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")
            config.read(config_path, encoding="utf-8")
            
            cartella = config.get("Parametri", "cartellaricevute", fallback="")
            
            if not cartella:
                messagebox.showerror("Errore", "Parametro 'cartellaricevute' non trovato nel file config.ini")
                return None
            
            if not os.path.exists(cartella):
                messagebox.showerror("Errore", f"Cartella fatture ricevute non trovata: {cartella}")
                return None
            
            return cartella
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella lettura di config.ini: {e}")
            return None
    
    def scan_months(self):
        """Scansiona la cartella e restituisce una lista di (anno, mese)"""
        months = []
        
        if not os.path.exists(self.cartella_ricevute):
            return months
        
        try:
            # Scansiona le cartelle anno
            for year_dir in os.listdir(self.cartella_ricevute):
                year_path = os.path.join(self.cartella_ricevute, year_dir)
                
                # Verifica che sia una directory e che contenga solo numeri (anno)
                if os.path.isdir(year_path) and year_dir.isdigit() and len(year_dir) == 4:
                    year = int(year_dir)
                    
                    # Scansiona le cartelle mese dentro l'anno
                    for month_dir in os.listdir(year_path):
                        month_path = os.path.join(year_path, month_dir)
                        
                        # Verifica che sia una directory e che contenga solo numeri (mese 01-12)
                        if os.path.isdir(month_path) and month_dir.isdigit():
                            month_num = int(month_dir)
                            if 1 <= month_num <= 12:
                                months.append((year, month_num))
            
            # Ordina per anno (decrescente) e poi per mese (decrescente)
            months.sort(key=lambda x: (x[0], x[1]), reverse=True)
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la scansione delle cartelle: {e}")
        
        return months
    
    def setup_ui(self):
        """Imposta l'interfaccia utente principale."""
        main_container = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_container.pack(fill="both", expand=True)
        
        # Frame per i tre bottoni con icone (stile download_page)
        buttons_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR, height=100)
        buttons_frame.pack(fill="x", pady=(0, 20))
        buttons_frame.pack_propagate(False)
        
        # Ottieni il percorso delle icone
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_size = (48, 48)  # Stessa dimensione di download_page (IconManager default)
        
        # Bottone 1 con csv.png
        btn1_frame = tk.Frame(buttons_frame, bg=Style.BACKGROUND_COLOR)
        btn1_frame.pack(side="left", padx=20)
        try:
            icon1_img = Image.open(os.path.join(project_root, "assets", "icon", "csv.png"))
            icon1_img = icon1_img.resize(icon_size, Image.Resampling.LANCZOS)
            icon1_photo = ImageTk.PhotoImage(icon1_img)
            btn1 = tk.Button(btn1_frame, image=icon1_photo, bd=0, bg=Style.BACKGROUND_COLOR,
                           activebackground=Style.BACKGROUND_COLOR, cursor="hand2",
                           command=self.on_button1_click)
            btn1.image = icon1_photo
            btn1.pack()
            tk.Label(btn1_frame, text="Carica Lista", font=("Arial", 9, "bold"),
                    bg=Style.BACKGROUND_COLOR, fg="#1f396a").pack(pady=(5, 0))
        except Exception as e:
            print(f"Errore caricamento icona csv: {e}")
        
        # Bottone 2 con check.png
        btn2_frame = tk.Frame(buttons_frame, bg=Style.BACKGROUND_COLOR)
        btn2_frame.pack(side="left", padx=20)
        try:
            icon2_img = Image.open(os.path.join(project_root, "assets", "icon", "check.png"))
            icon2_img = icon2_img.resize(icon_size, Image.Resampling.LANCZOS)
            icon2_photo = ImageTk.PhotoImage(icon2_img)
            btn2 = tk.Button(btn2_frame, image=icon2_photo, bd=0, bg=Style.BACKGROUND_COLOR,
                           activebackground=Style.BACKGROUND_COLOR, cursor="hand2",
                           command=self.on_button2_click)
            btn2.image = icon2_photo
            btn2.pack()
            tk.Label(btn2_frame, text="Verifica", font=("Arial", 9, "bold"),
                    bg=Style.BACKGROUND_COLOR, fg="#1f396a").pack(pady=(5, 0))
        except Exception as e:
            print(f"Errore caricamento icona check: {e}")
        
        # Frame per selezione anno (allineato con i bottoni)
        selection_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
        selection_frame.pack(fill="x", pady=(0, 10))
        
        # Label "SELEZIONA ANNO" (allineato con i bottoni che hanno padx=20)
        tk.Label(
            selection_frame,
            text="SELEZIONA ANNO:",
            font=("Arial", 11, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=getattr(Style, 'TEXT_COLOR', 'black')
        ).pack(side="left", padx=(20, 10))
        
        # Menu a tendina per gli anni (più grande)
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(selection_frame, textvariable=self.year_var, width=25, state="readonly", font=("Arial", 11))
        self.year_combo.pack(side="left", padx=(0, 10))
        self.year_combo.bind("<<ComboboxSelected>>", self.on_year_selected)
        
        # Frame per la tabella (stile documenti_page)
        table_frame = tk.Frame(main_container, bg=Style.BACKGROUND_COLOR)
        content_padding = getattr(Style, 'CONTENT_PADDING', 10)
        table_frame.pack(fill="both", expand=True, padx=content_padding, pady=(0, content_padding))
        
        # Salva il riferimento al frame della tabella (come in documenti_page)
        self.table_frame = table_frame
        
        # Treeview per la tabella con 7 colonne
        columns = ("MESE", "CSV", "NUMERO FT", "FT ITALIA", "FT ESTERO", "TOT IMPONIBILE", "CHECK")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Configura le colonne
        self.tree.heading("MESE", text="MESE")
        self.tree.heading("CSV", text="CSV")
        self.tree.heading("NUMERO FT", text="NUMERO FT")
        self.tree.heading("FT ITALIA", text="FT ITALIA")
        self.tree.heading("FT ESTERO", text="FT ESTERO")
        self.tree.heading("TOT IMPONIBILE", text="TOT IMPONIBILE")
        self.tree.heading("CHECK", text="CHECK")
        
        self.tree.column("MESE", width=150, anchor="center")
        self.tree.column("CSV", width=120, anchor="center")
        self.tree.column("NUMERO FT", width=120, anchor="center")
        self.tree.column("FT ITALIA", width=100, anchor="center")
        self.tree.column("FT ESTERO", width=100, anchor="center")
        self.tree.column("TOT IMPONIBILE", width=130, anchor="center")
        self.tree.column("CHECK", width=100, anchor="center")
        
        # Scrollbar verticale e orizzontale
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
        
        # Layout con grid (stile documenti_page)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Configura righe alternate (stile documenti_page)
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#E6F3FF')
        
        # Nomi dei mesi in italiano
        self.mesi_nomi = {
            1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
            5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
            9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
        }
        
        # Inizializza la lista degli anni
        self.load_years()
    
    def load_years(self):
        """Carica gli anni disponibili nel menu a tendina"""
        months = self.scan_months()
        years = sorted(set(year for year, _ in months), reverse=True)
        
        if years:
            self.year_combo['values'] = [str(year) for year in years]
            if years:
                self.year_var.set(str(years[0]))  # Seleziona l'anno più recente
                self.on_year_selected()
        else:
            self.year_combo['values'] = []
    
    def on_year_selected(self, event=None):
        """Gestisce la selezione dell'anno"""
        self.load_months()
    
    def verifica_json_esistente(self, anno: int, mese: int) -> tuple[Optional[str], Optional[int], Optional[int], Optional[int], Optional[float]]:
        """
        Verifica se esiste un file JSON per l'anno e mese specificati.
        
        Args:
            anno: Anno da verificare
            mese: Mese da verificare (1-12)
            
        Returns:
            Tupla (data_caricamento, totale_fatture, totale_italia, totale_estero, totale_imponibile, check, check_date)
            o (None, None, None, None, None, None, None) se non esiste
        """
        try:
            # Costruisci il percorso del file JSON
            cartella_anno = os.path.join(self.cartella_ricevute, str(anno))
            cartella_mese = os.path.join(cartella_anno, f"{mese:02d}")
            nome_file = f"lista_fatture_{anno}_{mese:02d}.json"
            percorso_json = os.path.join(cartella_mese, nome_file)
            
            if not os.path.exists(percorso_json):
                return None, None, None, None, None, None, None
            
            # Leggi il JSON
            with open(percorso_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data_caricamento = data.get("data_caricamento", "")
            
            # Estrai i totali
            totale_italia = data.get("totale_fatture_italia", 0)
            totale_estero = data.get("totale_fatture_estero", 0)
            totale_fatture = totale_italia + totale_estero
            
            # Se il totale è 0, prova a usare il campo vecchio per retrocompatibilità
            if totale_fatture == 0:
                totale_fatture = data.get("totale_fatture", 0)
                # Se non ci sono i campi separati, prova a dedurli
                if totale_italia == 0 and totale_estero == 0:
                    totale_italia = totale_fatture
            
            # Calcola il totale imponibile sommando tutti gli imponibili delle fatture
            totale_imponibile = 0.0
            fatture = data.get("fatture", [])
            for fattura in fatture:
                imponibile_str = fattura.get("imponibile", "")
                if imponibile_str:
                    try:
                        # Rimuovi eventuali spazi e sostituisci virgola con punto
                        imponibile_str = imponibile_str.strip().replace(",", ".")
                        if imponibile_str:
                            totale_imponibile += float(imponibile_str)
                    except (ValueError, TypeError):
                        # Se non riesce a convertire, ignora
                        pass
            
            # Estrai i valori di check
            check = data.get("check", "")
            check_date = data.get("check_date", "")
            
            return data_caricamento, totale_fatture, totale_italia, totale_estero, totale_imponibile, check, check_date
        
        except Exception as e:
            print(f"Errore nella lettura del JSON per {anno}/{mese:02d}: {e}")
            return None, None, None, None, None, None, None
    
    def load_months(self):
        """Carica i mesi nella tabella per l'anno selezionato"""
        # Pulisci la tabella
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Ottieni l'anno selezionato
        selected_year = self.year_var.get()
        if not selected_year:
            return
        
        try:
            year = int(selected_year)
        except ValueError:
            return
        
        # Scansiona i mesi
        all_months = self.scan_months()
        
        # Filtra per l'anno selezionato
        months = [(y, m) for y, m in all_months if y == year]
        
        if not months:
            return
        
        # Ordina per mese (crescente)
        months.sort(key=lambda x: x[1])
        
        # Popola la tabella con righe alternate
        for idx, (year, month_num) in enumerate(months):
            month_name = self.mesi_nomi.get(month_num, f"Mese {month_num}")
            # Converti in maiuscolo
            month_name = month_name.upper()
            
            # Verifica se esiste il JSON
            data_caricamento, totale_fatture, totale_italia, totale_estero, totale_imponibile, check, check_date = self.verifica_json_esistente(year, month_num)
            
            # Prepara i valori per la tabella (tutti in maiuscolo)
            csv_value = data_caricamento.upper() if data_caricamento else ""
            numero_ft = str(totale_fatture).upper() if totale_fatture else ""
            ft_italia = str(totale_italia).upper() if totale_italia is not None else ""
            ft_estero = str(totale_estero).upper() if totale_estero is not None else ""
            
            # Formatta il totale imponibile con 2 decimali
            if totale_imponibile is not None and totale_imponibile > 0:
                tot_imponibile_str = f"{totale_imponibile:.2f}".replace(".", ",")
            else:
                tot_imponibile_str = ""
            
            # Valore per la colonna CHECK (mostra lo stato del controllo)
            check_value = check.upper() if check else ""
            
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=(
                month_name, csv_value, numero_ft, ft_italia, ft_estero, tot_imponibile_str, check_value
            ), tags=(tag,))
    
    def on_button1_click(self):
        """Apre la finestra per caricare una lista"""
        window = CaricaListaWindow(self)
        # Attendi che la finestra venga chiusa
        self.wait_window(window)
        # Ricarica sempre la tabella (in caso di caricamento completato)
        self.load_months()
    
    def on_button2_click(self):
        """Esegue il controllo delle fatture nel JSON rispetto ai file XML"""
        # Trova tutti gli anni e mesi che hanno un JSON
        all_months = self.scan_months()
        anni_con_json = set()
        mesi_per_anno = {}
        
        for y, m in all_months:
            # Verifica se esiste il JSON per questo mese
            cartella_anno = os.path.join(self.cartella_ricevute, str(y))
            cartella_mese = os.path.join(cartella_anno, f"{m:02d}")
            nome_file = f"lista_fatture_{y}_{m:02d}.json"
            percorso_json = os.path.join(cartella_mese, nome_file)
            if os.path.exists(percorso_json):
                anni_con_json.add(y)
                if y not in mesi_per_anno:
                    mesi_per_anno[y] = set()
                mesi_per_anno[y].add(m)
        
        if not anni_con_json:
            messagebox.showinfo("Informazione", "Nessun file JSON trovato")
            return
        
        # Apri la finestra di selezione
        window = SelezionaVerificaWindow(self, anni_con_json, mesi_per_anno)
        self.wait_window(window)
        
        if not window.confermato:
            return  # L'utente ha annullato
        
        anno = window.anno_selezionato
        mese = window.mese_selezionato
        
        # Verifica che il JSON esista ancora
        cartella_anno = os.path.join(self.cartella_ricevute, str(anno))
        cartella_mese = os.path.join(cartella_anno, f"{mese:02d}")
        nome_file = f"lista_fatture_{anno}_{mese:02d}.json"
        percorso_json = os.path.join(cartella_mese, nome_file)
        
        if not os.path.exists(percorso_json):
            messagebox.showerror("Errore", f"File JSON non trovato per {mese:02d}/{anno}")
            return
        
        # Esegui il controllo
        tutte_presenti, fatture_mancanti = self.verifica_fatture_mese(anno, mese)
        
        # Ricarica la tabella per mostrare i risultati
        self.load_months()
        
        # Mostra il risultato
        mesi_nomi = {
            1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
            5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
            9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
        }
        mese_nome = mesi_nomi.get(mese, f"Mese {mese}")
        
        if tutte_presenti:
            messagebox.showinfo("Completato", f"Controllo completato per {mese_nome} {anno}\n\n✓ Tutte le fatture sono presenti")
        else:
            # Mostra la finestra con le fatture mancanti
            window_mancanti = FattureMancantiWindow(self, fatture_mancanti, anno, mese)
            self.wait_window(window_mancanti)
    
    def verifica_fatture_mese(self, anno: int, mese: int):
        """
        Verifica se tutte le fatture nel JSON hanno un corrispondente file XML.
        
        Args:
            anno: Anno da verificare
            mese: Mese da verificare (1-12)
            
        Returns:
            Tuple (tutte_presenti, fatture_mancanti) dove fatture_mancanti è una lista
            di dizionari con i dettagli delle fatture mancanti
        """
        try:
            # Costruisci il percorso del file JSON
            cartella_anno = os.path.join(self.cartella_ricevute, str(anno))
            cartella_mese = os.path.join(cartella_anno, f"{mese:02d}")
            nome_file = f"lista_fatture_{anno}_{mese:02d}.json"
            percorso_json = os.path.join(cartella_mese, nome_file)
            
            if not os.path.exists(percorso_json):
                print(f"File JSON non trovato: {percorso_json}")
                return True, []
            
            # Leggi il JSON
            with open(percorso_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            fatture = data.get("fatture", [])
            if not fatture:
                print(f"Nessuna fattura nel JSON per {anno}/{mese:02d}")
                return True, []
            
            # Lista dei file XML nella cartella
            xml_files = []
            if os.path.exists(cartella_mese):
                for file in os.listdir(cartella_mese):
                    if file.lower().endswith('.xml'):
                        # Rimuovi l'estensione per il confronto
                        xml_files.append(file[:-4])  # Rimuovi .xml
            
            # Verifica ogni fattura
            tutte_presenti = True
            fatture_mancanti = []
            
            for fattura in fatture:
                codice_fattura = fattura.get("codice_fattura", "")
                if codice_fattura and codice_fattura not in xml_files:
                    tutte_presenti = False
                    # Aggiungi i dettagli della fattura mancante
                    fatture_mancanti.append({
                        "codice_fattura": codice_fattura,
                        "numero_fattura": fattura.get("numero_fattura", ""),
                        "data_emissione": fattura.get("data_emissione", ""),
                        "denominazione_fornitore": fattura.get("denominazione_fornitore", ""),
                        "partita_iva_fornitore": fattura.get("partita_iva_fornitore", ""),
                        "imponibile": fattura.get("imponibile", "")
                    })
            
            # Aggiorna il JSON con i risultati
            from datetime import datetime
            data["check"] = "VERIFIED" if tutte_presenti else "FAILED"
            data["check_date"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Salva il JSON aggiornato
            with open(percorso_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return tutte_presenti, fatture_mancanti
        
        except Exception as e:
            print(f"Errore durante la verifica per {anno}/{mese:02d}: {e}")
            import traceback
            traceback.print_exc()
            return False, []

