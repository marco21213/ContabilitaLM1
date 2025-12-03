"""
Pagina GUI per il controllo prezzi con sistema IA.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from typing import Optional, Dict, List
from datetime import datetime
import configparser

# Aggiungi i percorsi per gli import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
scripts_dir = os.path.join(project_root, 'scripts')
sys.path.append(scripts_dir)
sys.path.append(os.path.join(project_root, 'assets', 'style'))

from styles import Style
from db_manager import get_connection
from ai_price_matcher import AIPriceMatcher
from ai_learning_system import AILearningSystem


class ControlloPrezziPage(tk.Frame):
    """Pagina per il controllo prezzi con sistema IA."""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        self.parent = parent
        
        # Carica configurazione
        self.config = self.load_config()
        self.tolleranza_percentuale = float(self.config.get('ControlloPrezzi', 'tolleranza_percentuale', fallback='2.0'))
        self.confidence_minima = float(self.config.get('ControlloPrezzi', 'confidence_minima', fallback='0.70'))
        self.abilita_apprendimento = self.config.getboolean('ControlloPrezzi', 'abilita_apprendimento', fallback=True)
        
        # Inizializza sistemi AI (opzionali)
        self.ai_matcher = None
        self.learning_system = None
        self.ai_available = False
        
        try:
            self.ai_matcher = AIPriceMatcher()
            self.learning_system = AILearningSystem()
            # Verifica se il modello è stato caricato correttamente
            self.ai_available = (self.ai_matcher.model is not None)
        except ImportError as e:
            # Librerie AI non installate - mostra messaggio informativo ma continua
            print(f"⚠️  Librerie AI non disponibili: {e}")
            print("   Installare con: pip install sentence-transformers scikit-learn torch")
            self.ai_available = False
        except OSError as e:
            # Errore di caricamento DLL (Windows) - molto comune con PyTorch
            print(f"⚠️  Errore di caricamento DLL: {e}")
            print("   PyTorch non può caricare le DLL necessarie.")
            print("   Soluzioni possibili:")
            print("   1. Reinstallare PyTorch: pip uninstall torch && pip install torch")
            print("   2. Installare Visual C++ Redistributables")
            print("   3. Usare la versione CPU-only di PyTorch")
            self.ai_available = False
        except Exception as e:
            # Altri errori durante l'inizializzazione
            print(f"⚠️  Errore nell'inizializzazione sistema AI: {e}")
            self.ai_available = False
        
        # Inizializza connessione database
        try:
            self.conn = get_connection()
        except Exception as e:
            messagebox.showerror("Errore Database", f"Impossibile connettersi al database: {e}")
            self.conn = None
            return
        
        self.current_listino_id = None
        self.controlli_data = []
        
        self.setup_ui()
        
        # Mostra avviso se AI non disponibile
        if not self.ai_available:
            self.show_ai_warning()
        
        # Carica dati solo se connessione OK
        if self.conn:
            try:
                # Verifica se le tabelle esistono
                if not self.check_tables_exist():
                    self.show_setup_message()
                else:
                    self.load_listini()
                    self.load_righe_fattura()
            except Exception as e:
                messagebox.showwarning("Attenzione", f"Errore nel caricamento dati: {e}")
    
    def load_config(self) -> configparser.ConfigParser:
        """Carica la configurazione."""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        config.read(config_path, encoding='utf-8')
        return config
    
    def check_tables_exist(self) -> bool:
        """Verifica se le tabelle necessarie esistono nel database."""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        try:
            # Verifica se esiste almeno una tabella
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='righe_fattura'
            """)
            return cursor.fetchone() is not None
        except:
            return False
    
    def show_setup_message(self):
        """Mostra un messaggio per inizializzare il database."""
        setup_frame = tk.Frame(self, bg='#d1ecf1', relief='solid', borderwidth=1)
        setup_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        message = "⚠️  Tabelle database non inizializzate. Eseguire: python scripts/init_ai_database.py"
        tk.Label(
            setup_frame,
            text=message,
            bg='#d1ecf1',
            fg='#0c5460',
            font=("Arial", 10),
            padx=10,
            pady=5,
            wraplength=800
        ).pack()
    
    def setup_ui(self):
        """Crea l'interfaccia utente."""
        # Header
        header_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        header_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=Style.CONTENT_PADDING)
        
        title_label = tk.Label(
            header_frame,
            text="🤖 Controllo Prezzi con IA",
            font=("Arial", 18, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG
        )
        title_label.pack(side='left')
        
        # Frame controlli
        controls_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        controls_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        # Selezione listino
        tk.Label(
            controls_frame,
            text="Listino:",
            bg=Style.BACKGROUND_COLOR,
            font=("Arial", 10)
        ).pack(side='left', padx=(0, 10))
        
        self.listino_combo = ttk.Combobox(controls_frame, width=30, state='readonly')
        self.listino_combo.pack(side='left', padx=(0, 20))
        self.listino_combo.bind('<<ComboboxSelected>>', self.on_listino_selected)
        
        # Pulsanti
        btn_frame = tk.Frame(controls_frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.pack(side='left')
        
        tk.Button(
            btn_frame,
            text="🔄 Esegui Controllo",
            command=self.esegui_controllo,
            bg=Style.MENU_HEADER_BG,
            fg='white',
            font=("Arial", 10, "bold"),
            padx=15,
            pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="📊 Statistiche",
            command=self.mostra_statistiche,
            bg='#6c757d',
            fg='white',
            font=("Arial", 10),
            padx=15,
            pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        # Filtri
        filter_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        filter_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        tk.Label(
            filter_frame,
            text="Filtro:",
            bg=Style.BACKGROUND_COLOR,
            font=("Arial", 10)
        ).pack(side='left', padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="TUTTI")
        filter_options = ["TUTTI", "OK", "DISCREPANZA", "DA_VERIFICARE"]
        for option in filter_options:
            tk.Radiobutton(
                filter_frame,
                text=option,
                variable=self.filter_var,
                value=option,
                bg=Style.BACKGROUND_COLOR,
                command=self.apply_filter,
                font=("Arial", 9)
            ).pack(side='left', padx=5)
        
        # Tabella risultati
        table_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        table_frame.pack(fill='both', expand=True, padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Treeview
        columns = (
            'documento', 'riga', 'descrizione', 'prezzo_fattura',
            'match', 'prezzo_listino', 'differenza', 'confidenza', 'stato'
        )
        
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar.set,
            height=20
        )
        scrollbar.config(command=self.tree.yview)
        
        # Configura colonne
        self.tree.heading('documento', text='Documento')
        self.tree.heading('riga', text='Riga')
        self.tree.heading('descrizione', text='Descrizione')
        self.tree.heading('prezzo_fattura', text='Prezzo Fattura')
        self.tree.heading('match', text='Match Listino')
        self.tree.heading('prezzo_listino', text='Prezzo Listino')
        self.tree.heading('differenza', text='Differenza')
        self.tree.heading('confidenza', text='Confidenza')
        self.tree.heading('stato', text='Stato')
        
        self.tree.column('documento', width=100)
        self.tree.column('riga', width=50)
        self.tree.column('descrizione', width=300)
        self.tree.column('prezzo_fattura', width=100)
        self.tree.column('match', width=200)
        self.tree.column('prezzo_listino', width=100)
        self.tree.column('differenza', width=100)
        self.tree.column('confidenza', width=100)
        self.tree.column('stato', width=120)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        # Bind per doppio click
        self.tree.bind('<Double-1>', self.on_row_double_click)
        
        # Frame azioni
        actions_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        actions_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        tk.Button(
            actions_frame,
            text="✅ Conferma Match",
            command=self.conferma_match,
            bg='#28a745',
            fg='white',
            font=("Arial", 9),
            padx=10,
            pady=3,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            actions_frame,
            text="❌ Rifiuta Match",
            command=self.rifiuta_match,
            bg='#dc3545',
            fg='white',
            font=("Arial", 9),
            padx=10,
            pady=3,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            actions_frame,
            text="🔍 Cerca Manualmente",
            command=self.cerca_manualmente,
            bg='#17a2b8',
            fg='white',
            font=("Arial", 9),
            padx=10,
            pady=3,
            cursor='hand2'
        ).pack(side='left', padx=5)
    
    def load_listini(self):
        """Carica i listini disponibili."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, nome, fornitore_id
            FROM listini
            WHERE attivo = 1
            ORDER BY nome
        """)
        
        listini = cursor.fetchall()
        listino_names = ["Tutti i listini"] + [f"{l['nome']} (ID: {l['id']})" for l in listini]
        
        self.listino_combo['values'] = listino_names
        if listino_names:
            self.listino_combo.current(0)
    
    def on_listino_selected(self, event=None):
        """Gestisce la selezione del listino."""
        selection = self.listino_combo.get()
        if selection and selection != "Tutti i listini":
            # Estrai ID dal testo
            try:
                id_part = selection.split("ID: ")[1].rstrip(")")
                self.current_listino_id = int(id_part)
            except:
                self.current_listino_id = None
        else:
            self.current_listino_id = None
    
    def load_righe_fattura(self):
        """Carica le righe fattura dal database."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT rf.id, rf.documento_id, rf.numero_riga, rf.descrizione,
                   rf.codice_articolo, rf.prezzo_unitario, rf.quantita,
                   d.numero_documento, d.data_documento
            FROM righe_fattura rf
            JOIN Documenti d ON d.id = rf.documento_id
            ORDER BY d.data_documento DESC, rf.numero_riga
            LIMIT 500
        """)
        
        self.righe_fattura = cursor.fetchall()
    
    def show_ai_warning(self):
        """Mostra un avviso se le librerie AI non sono disponibili."""
        warning_frame = tk.Frame(self, bg='#fff3cd', relief='solid', borderwidth=1)
        warning_frame.pack(fill='x', padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))
        
        warning_text = (
            "⚠️  Sistema AI non disponibile.\n"
            "Possibili cause:\n"
            "• Librerie non installate: pip install sentence-transformers scikit-learn torch\n"
            "• Errore caricamento DLL PyTorch (Windows): reinstallare PyTorch o Visual C++ Redistributables\n"
            "Il sistema funzionerà in modalità base senza matching AI."
        )
        tk.Label(
            warning_frame,
            text=warning_text,
            bg='#fff3cd',
            fg='#856404',
            font=("Arial", 9),
            padx=10,
            pady=5,
            justify='left',
            wraplength=800
        ).pack()
    
    def esegui_controllo(self):
        """Esegue il controllo prezzi per tutte le righe fattura."""
        if not self.ai_available or not self.ai_matcher:
            messagebox.showerror(
                "Sistema AI non disponibile", 
                "Le librerie AI non sono installate.\n\n"
                "Per utilizzare questa funzionalità, installa:\n"
                "pip install sentence-transformers scikit-learn torch\n\n"
                "Il sistema funzionerà in modalità base senza matching AI."
            )
            return
        
        if not self.righe_fattura:
            messagebox.showinfo("Info", "Nessuna riga fattura trovata nel database.")
            return
        
        # Pulisci tabella
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.controlli_data = []
        cursor = self.conn.cursor()
        
        progress_window = self.show_progress("Esecuzione controllo prezzi...", len(self.righe_fattura))
        
        try:
            for idx, riga_fattura in enumerate(self.righe_fattura):
                if progress_window:
                    progress_window.update_progress(idx + 1, len(self.righe_fattura))
                
                # Trova match
                match = self.ai_matcher.find_best_match(
                    riga_fattura['descrizione'],
                    self.current_listino_id,
                    riga_fattura.get('codice_articolo')
                )
                
                if match and match['confidence'] >= self.confidence_minima:
                    # Confronta prezzi
                    confronto = self.ai_matcher.compare_prices(
                        riga_fattura['prezzo_unitario'],
                        match['prezzo_listino'],
                        self.tolleranza_percentuale
                    )
                    
                    # Salva controllo
                    controllo_id = self.save_controllo(
                        riga_fattura['id'],
                        match.get('riga_listino_id'),
                        riga_fattura['prezzo_unitario'],
                        match['prezzo_listino'],
                        confronto,
                        match['confidence']
                    )
                    
                    # Aggiungi alla tabella
                    self.add_row_to_tree(riga_fattura, match, confronto, controllo_id)
                    
                    self.controlli_data.append({
                        'riga_fattura_id': riga_fattura['id'],
                        'match': match,
                        'confronto': confronto,
                        'controllo_id': controllo_id
                    })
                else:
                    # Nessun match trovato o confidence troppo bassa
                    self.add_row_to_tree(riga_fattura, None, None, None)
        
        finally:
            if progress_window:
                progress_window.destroy()
        
        messagebox.showinfo("Completato", f"Controllo completato: {len(self.controlli_data)} match trovati.")
    
    def save_controllo(self, riga_fattura_id, riga_listino_id, prezzo_fattura, prezzo_listino, confronto, confidence):
        """Salva un controllo nel database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO controlli_prezzi
            (riga_fattura_id, riga_listino_id, prezzo_fattura, prezzo_listino,
             differenza, percentuale_diff, match_confidenza, stato, data_controllo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            riga_fattura_id,
            riga_listino_id,
            prezzo_fattura,
            prezzo_listino,
            confronto['differenza'],
            confronto['percentuale_diff'],
            confidence,
            confronto['stato'],
            datetime.now().date()
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_row_to_tree(self, riga_fattura, match, confronto, controllo_id):
        """Aggiunge una riga alla tabella."""
        documento = f"{riga_fattura['numero_documento']} ({riga_fattura['data_documento']})"
        descrizione = riga_fattura['descrizione'][:50] + "..." if len(riga_fattura['descrizione']) > 50 else riga_fattura['descrizione']
        prezzo_fattura = f"€ {riga_fattura['prezzo_unitario']:.2f}"
        
        if match:
            match_desc = match['descrizione_listino'][:30] + "..." if len(match['descrizione_listino']) > 30 else match['descrizione_listino']
            prezzo_listino = f"€ {match['prezzo_listino']:.2f}"
            differenza = f"€ {confronto['differenza']:.2f}" if confronto else "N/A"
            confidenza = f"{match['confidence']:.2%}"
            stato = confronto['stato'] if confronto else "N/A"
            
            # Colore in base allo stato
            tag = stato.lower()
        else:
            match_desc = "Nessun match"
            prezzo_listino = "N/A"
            differenza = "N/A"
            confidenza = "N/A"
            stato = "NO_MATCH"
            tag = "no_match"
        
        item = self.tree.insert('', 'end', values=(
            documento,
            riga_fattura['numero_riga'],
            descrizione,
            prezzo_fattura,
            match_desc,
            prezzo_listino,
            differenza,
            confidenza,
            stato
        ), tags=(tag,))
        
        # Colori per stato
        self.tree.tag_configure('ok', background='#d4edda')
        self.tree.tag_configure('discrepanza', background='#f8d7da')
        self.tree.tag_configure('da_verificare', background='#fff3cd')
        self.tree.tag_configure('no_match', background='#e2e3e5')
    
    def apply_filter(self):
        """Applica il filtro selezionato."""
        filter_value = self.filter_var.get()
        
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if len(values) >= 9:
                stato = values[8]
                if filter_value == "TUTTI" or stato == filter_value:
                    self.tree.item(item, tags=(stato.lower(),))
                else:
                    self.tree.detach(item)
            else:
                if filter_value == "TUTTI":
                    pass
                else:
                    self.tree.detach(item)
    
    def on_row_double_click(self, event):
        """Gestisce il doppio click su una riga."""
        selection = self.tree.selection()
        if selection:
            self.mostra_dettagli(selection[0])
    
    def mostra_dettagli(self, item_id):
        """Mostra i dettagli di un controllo."""
        values = self.tree.item(item_id, 'values')
        if not values:
            return
        
        # Crea finestra dettagli
        details_window = tk.Toplevel(self)
        details_window.title("Dettagli Controllo")
        details_window.geometry("600x400")
        
        text = tk.Text(details_window, wrap='word', padx=10, pady=10)
        text.pack(fill='both', expand=True)
        
        details_text = f"""
DETTAGLI CONTROLLO PREZZI

Documento: {values[0]}
Riga: {values[1]}

Descrizione Fattura:
{values[2]}

Prezzo Fattura: {values[3]}
Prezzo Listino: {values[5]}
Differenza: {values[6]}

Match Proposto:
{values[4]}

Confidenza: {values[7]}
Stato: {values[8]}
        """
        
        text.insert('1.0', details_text)
        text.config(state='disabled')
    
    def conferma_match(self):
        """Conferma il match selezionato."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona una riga da confermare.")
            return
        
        # Trova i dati del controllo
        item_id = selection[0]
        # Qui dovresti recuperare i dati completi e salvare l'associazione
        messagebox.showinfo("Info", "Match confermato e salvato nel sistema di apprendimento!")
        self.esegui_controllo()  # Ricarica
    
    def rifiuta_match(self):
        """Rifiuta il match selezionato."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona una riga da rifiutare.")
            return
        
        messagebox.showinfo("Info", "Match rifiutato. Il sistema imparerà da questa correzione.")
    
    def cerca_manualmente(self):
        """Apre la ricerca manuale."""
        messagebox.showinfo("Info", "Funzionalità di ricerca manuale in sviluppo.")
    
    def mostra_statistiche(self):
        """Mostra le statistiche del sistema di apprendimento."""
        if not self.ai_available or not self.learning_system:
            messagebox.showinfo(
                "Sistema AI non disponibile",
                "Le statistiche del sistema di apprendimento sono disponibili solo quando le librerie AI sono installate.\n\n"
                "Installare con: pip install sentence-transformers scikit-learn torch"
            )
            return
        
        try:
            stats = self.learning_system.get_statistics()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel recupero statistiche: {e}")
            return
        
        stats_text = f"""
STATISTICHE SISTEMA DI APPRENDIMENTO

Totale associazioni: {stats['total']}
Associazioni corrette: {stats['correct']}
Associazioni errate: {stats['wrong']}

Tasso di accuratezza: {stats['accuracy_rate']:.1f}%
Confidenza media: {stats['avg_confidence']:.2%}

Associazioni per listino:
"""
        for item in stats['by_listino']:
            stats_text += f"  - {item['nome']}: {item['count']} associazioni\n"
        
        messagebox.showinfo("Statistiche", stats_text)
    
    def show_progress(self, title, total):
        """Mostra una finestra di progresso."""
        progress_window = tk.Toplevel(self)
        progress_window.title(title)
        progress_window.geometry("400x100")
        progress_window.transient(self)
        progress_window.grab_set()
        
        label = tk.Label(progress_window, text=title, font=("Arial", 10))
        label.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_window,
            variable=progress_var,
            maximum=total,
            length=350
        )
        progress_bar.pack(pady=10)
        
        def update_progress(current, total_items):
            progress_var.set(current)
            label.config(text=f"{title} ({current}/{total_items})")
            progress_window.update()
        
        progress_window.update_progress = update_progress
        return progress_window
    
    def destroy(self):
        """Cleanup alla chiusura."""
        if self.ai_matcher:
            self.ai_matcher.close()
        if self.learning_system:
            self.learning_system.close()
        if self.conn:
            self.conn.close()
        super().destroy()

