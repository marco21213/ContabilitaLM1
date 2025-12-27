import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import sys
import os

# Import stile
sys.path.append("assets/style")
try:
    from styles import Style
except ImportError:
    class Style:
        BACKGROUND_COLOR = "#FFFFFF"
        CONTENT_PADDING = 20


class AgganciaDichiarazioniWindow(tk.Toplevel):
    def __init__(self, parent, db_path, fatture_con_di):
        super().__init__(parent)
        
        self.parent = parent
        self.db_path = db_path
        self.fatture_con_di = fatture_con_di
        
        self.title("Aggancia Fatture a Dichiarazioni d'Intento")
        self.geometry("1000x700")
        self.resizable(True, True)
        self.transient(parent)
        
        # Raggruppa le fatture per cliente
        self.fatture_per_cliente = self.raggruppa_per_cliente()
        
        self.create_widgets()
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def raggruppa_per_cliente(self):
        """Raggruppa le fatture per cliente (soggetto_id)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crea un dizionario per raggruppare per cliente
            fatture_per_cliente = {}
            
            for fattura in self.fatture_con_di:
                soggetto_id = fattura['soggetto_id']
                
                # Recupera il nome del cliente
                cursor.execute("SELECT ragione_sociale FROM soggetti WHERE id = ?", (soggetto_id,))
                result = cursor.fetchone()
                ragione_sociale = result[0] if result else f"Cliente ID {soggetto_id}"
                
                if soggetto_id not in fatture_per_cliente:
                    fatture_per_cliente[soggetto_id] = {
                        'ragione_sociale': ragione_sociale,
                        'fatture': []
                    }
                
                fatture_per_cliente[soggetto_id]['fatture'].append(fattura)
            
            conn.close()
            return fatture_per_cliente
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel raggruppamento fatture:\n{str(e)}")
            return {}
    
    def create_widgets(self):
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="🔗 Aggancia Fatture a Dichiarazioni d'Intento",
            font=('Arial', 14, 'bold'),
            bg=Style.BACKGROUND_COLOR,
            fg="#333333"
        )
        title_label.pack(pady=(0, 20))
        
        # Frame principale con scrollbar
        container_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        container_frame.pack(fill="both", expand=True)
        
        # Canvas e scrollbar
        canvas = tk.Canvas(container_frame, bg=Style.BACKGROUND_COLOR)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Style.BACKGROUND_COLOR)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Crea una sezione per ogni cliente
        self.selezioni = {}  # {documento_id: id_dichiarazione}
        
        for soggetto_id, dati_cliente in self.fatture_per_cliente.items():
            self.create_cliente_section(scrollable_frame, soggetto_id, dati_cliente)
        
        # Bottoni
        button_frame = tk.Frame(main_frame, bg=Style.BACKGROUND_COLOR)
        button_frame.pack(fill="x", pady=(15, 0))
        
        btn_salva = tk.Button(
            button_frame,
            text="💾 Salva Aggancamenti",
            command=self.salva_agganciamenti,
            bg="#4CAF50",
            fg="white",
            font=('Arial', 11, 'bold'),
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        btn_salva.pack(side="left", padx=(0, 10))
        
        btn_chiudi = tk.Button(
            button_frame,
            text="✖ Chiudi",
            command=self.destroy,
            bg="#f44336",
            fg="white",
            font=('Arial', 11, 'bold'),
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        btn_chiudi.pack(side="right")
    
    def create_cliente_section(self, parent, soggetto_id, dati_cliente):
        """Crea una sezione per un cliente con le sue fatture"""
        # Frame cliente
        cliente_frame = tk.LabelFrame(
            parent,
            text=f"👤 {dati_cliente['ragione_sociale']}",
            font=('Arial', 11, 'bold'),
            bg=Style.BACKGROUND_COLOR,
            fg="#333333",
            padx=15,
            pady=15
        )
        cliente_frame.pack(fill="x", pady=10, padx=10)
        
        # Carica le dichiarazioni disponibili per questo cliente
        dichiarazioni = self.carica_dichiarazioni_cliente(soggetto_id)
        
        # Tabella fatture
        columns = ('Numero', 'Data', 'Imponibile', 'Dichiarazione')
        tree = ttk.Treeview(cliente_frame, columns=columns, show='headings', height=min(len(dati_cliente['fatture']), 5))
        
        tree.heading('Numero', text='Numero Fattura')
        tree.heading('Data', text='Data')
        tree.heading('Imponibile', text='Imponibile (€)')
        tree.heading('Dichiarazione', text='Dichiarazione d\'Intento')
        
        tree.column('Numero', width=150)
        tree.column('Data', width=100)
        tree.column('Imponibile', width=150)
        tree.column('Dichiarazione', width=300)
        
        # Popola la tabella
        for fattura in dati_cliente['fatture']:
            documento_id = fattura['documento_id']
            numero = fattura['numero_documento']
            data = fattura['data_documento']
            imponibile = fattura['imponibile']
            
            tree.insert('', 'end', iid=documento_id, values=(
                numero,
                data,
                f"€ {imponibile:,.2f}",
                ""  # Sarà popolato dal combobox
            ))
        
        tree.pack(fill="both", expand=True, pady=(10, 0))
        
        # Combobox per ogni riga (non direttamente nella treeview, ma in un frame separato)
        # In alternativa, usiamo un approccio più semplice: combobox per ogni fattura
        combobox_frame = tk.Frame(cliente_frame, bg=Style.BACKGROUND_COLOR)
        combobox_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(
            combobox_frame,
            text="Seleziona dichiarazione per ogni fattura:",
            font=('Arial', 9),
            bg=Style.BACKGROUND_COLOR,
            fg="#666666"
        ).pack(anchor="w", pady=(0, 5))
        
        # Crea un combobox per ogni fattura
        self.combobox_per_documento = {}
        
        for fattura in dati_cliente['fatture']:
            documento_id = fattura['documento_id']
            
            row_frame = tk.Frame(combobox_frame, bg=Style.BACKGROUND_COLOR)
            row_frame.pack(fill="x", pady=2)
            
            tk.Label(
                row_frame,
                text=f"Fattura {fattura['numero_documento']}:",
                font=('Arial', 9),
                bg=Style.BACKGROUND_COLOR,
                width=20,
                anchor="w"
            ).pack(side="left", padx=(0, 10))
            
            # Combobox con le dichiarazioni disponibili
            combo_var = tk.StringVar()
            valori_combo = ["Nessuna"] + [f"{d['numero']} (Residuo: € {d['plafond_residuo']:,.2f})" for d in dichiarazioni]
            combo = ttk.Combobox(
                row_frame,
                textvariable=combo_var,
                values=valori_combo,
                state="readonly",
                width=50
            )
            combo.pack(side="left", fill="x", expand=True)
            
            # Verifica se il documento è già agganciato a una dichiarazione
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id_dichiarazione_intento FROM documenti WHERE id = ?
                """, (documento_id,))
                risultato = cursor.fetchone()
                id_dichiarazione_attuale = risultato[0] if risultato and risultato[0] else None
                conn.close()
                
                # Se è già agganciato, seleziona la dichiarazione corrispondente
                if id_dichiarazione_attuale:
                    for idx, di in enumerate(dichiarazioni):
                        if di['id'] == id_dichiarazione_attuale:
                            combo.current(idx + 1)  # +1 perché "Nessuna" è all'indice 0
                            break
                    else:
                        combo.current(0)  # Se la dichiarazione non è più disponibile, mostra "Nessuna"
                else:
                    combo.current(0)  # Default: "Nessuna"
            except Exception:
                combo.current(0)  # In caso di errore, default: "Nessuna"
            
            # Salva il riferimento per il salvataggio (includi anche l'imponibile)
            self.combobox_per_documento[documento_id] = {
                'combo': combo,
                'dichiarazioni': dichiarazioni,
                'imponibile': fattura['imponibile']
            }
    
    def carica_dichiarazioni_cliente(self, soggetto_id):
        """Carica le dichiarazioni d'intento disponibili per un cliente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Carica dichiarazioni attive (con plafond residuo > 0)
            cursor.execute("""
                SELECT id, numero_dichiarazione, data_inizio, data_fine, plafond_residuo
                FROM dichiarazioni_intento
                WHERE id_soggetto = ? AND plafond_residuo > 0
                ORDER BY data_inizio DESC
            """, (soggetto_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            dichiarazioni = []
            for row in rows:
                id_di, numero, data_inizio, data_fine, plafond_residuo = row
                dichiarazioni.append({
                    'id': id_di,
                    'numero': numero,
                    'data_inizio': data_inizio,
                    'data_fine': data_fine,
                    'plafond_residuo': plafond_residuo
                })
            
            return dichiarazioni
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dichiarazioni:\n{str(e)}")
            return []
    
    def salva_agganciamenti(self):
        """Salva gli agganciamenti selezionati nel database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            agganciate = 0
            
            for documento_id, dati_combo in self.combobox_per_documento.items():
                combo = dati_combo['combo']
                dichiarazioni = dati_combo['dichiarazioni']
                imponibile = dati_combo['imponibile']
                
                selezione = combo.get()
                
                # Recupera la dichiarazione attuale del documento (se presente)
                cursor.execute("""
                    SELECT id_dichiarazione_intento FROM documenti WHERE id = ?
                """, (documento_id,))
                risultato = cursor.fetchone()
                id_dichiarazione_attuale = risultato[0] if risultato and risultato[0] else None
                
                if selezione == "Nessuna":
                    # Rimuovi aggancio: elimina movimento se esiste e ripristina plafond
                    if id_dichiarazione_attuale:
                        # Verifica se esiste un movimento per questo documento
                        cursor.execute("""
                            SELECT id, importo_consumato FROM consumo_plafond
                            WHERE id_dichiarazione = ? AND id_documento = ?
                        """, (id_dichiarazione_attuale, documento_id))
                        movimento = cursor.fetchone()
                        
                        if movimento:
                            movimento_id, importo_movimento = movimento
                            # Elimina il movimento
                            cursor.execute("""
                                DELETE FROM consumo_plafond WHERE id = ?
                            """, (movimento_id,))
                            # Ripristina il plafond residuo
                            cursor.execute("""
                                UPDATE dichiarazioni_intento
                                SET plafond_residuo = plafond_residuo + ?
                                WHERE id = ?
                            """, (importo_movimento, id_dichiarazione_attuale))
                    
                    # Imposta id_dichiarazione_intento a NULL
                    cursor.execute("""
                        UPDATE documenti
                        SET id_dichiarazione_intento = NULL
                        WHERE id = ?
                    """, (documento_id,))
                else:
                    # Estrai l'ID della dichiarazione dalla selezione
                    # Formato: "NUMERO (Residuo: € X,XXX.XX)"
                    numero_di = selezione.split(' (')[0]
                    
                    # Trova l'ID corrispondente
                    id_dichiarazione_nuova = None
                    for di in dichiarazioni:
                        if di['numero'] == numero_di:
                            id_dichiarazione_nuova = di['id']
                            break
                    
                    if id_dichiarazione_nuova:
                        # Se c'era già un aggancio a un'altra dichiarazione, rimuovilo prima
                        if id_dichiarazione_attuale and id_dichiarazione_attuale != id_dichiarazione_nuova:
                            # Verifica se esiste un movimento per questo documento con la vecchia dichiarazione
                            cursor.execute("""
                                SELECT id, importo_consumato FROM consumo_plafond
                                WHERE id_dichiarazione = ? AND id_documento = ?
                            """, (id_dichiarazione_attuale, documento_id))
                            movimento = cursor.fetchone()
                            
                            if movimento:
                                movimento_id, importo_movimento = movimento
                                # Elimina il movimento
                                cursor.execute("""
                                    DELETE FROM consumo_plafond WHERE id = ?
                                """, (movimento_id,))
                                # Ripristina il plafond residuo della vecchia dichiarazione
                                cursor.execute("""
                                    UPDATE dichiarazioni_intento
                                    SET plafond_residuo = plafond_residuo + ?
                                    WHERE id = ?
                                """, (importo_movimento, id_dichiarazione_attuale))
                        
                        # Aggiorna il documento con la nuova dichiarazione
                        cursor.execute("""
                            UPDATE documenti
                            SET id_dichiarazione_intento = ?
                            WHERE id = ?
                        """, (id_dichiarazione_nuova, documento_id))
                        
                        # Verifica se esiste già un movimento per questo documento con la nuova dichiarazione
                        cursor.execute("""
                            SELECT id FROM consumo_plafond
                            WHERE id_dichiarazione = ? AND id_documento = ?
                        """, (id_dichiarazione_nuova, documento_id))
                        movimento_esistente = cursor.fetchone()
                        
                        if not movimento_esistente:
                            # Crea nuovo movimento in consumo_plafond
                            cursor.execute("""
                                INSERT INTO consumo_plafond
                                (id_dichiarazione, id_documento, data, importo_consumato)
                                VALUES (?, ?, date('now'), ?)
                            """, (id_dichiarazione_nuova, documento_id, imponibile))
                            
                            # Aggiorna plafond residuo
                            cursor.execute("""
                                UPDATE dichiarazioni_intento
                                SET plafond_residuo = plafond_residuo - ?
                                WHERE id = ?
                            """, (imponibile, id_dichiarazione_nuova))
                        
                        agganciate += 1
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo(
                "Successo",
                f"Aggancamenti salvati con successo!\n{agganciate} fatture agganciate a dichiarazioni d'intento."
            )
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio:\n{str(e)}")

