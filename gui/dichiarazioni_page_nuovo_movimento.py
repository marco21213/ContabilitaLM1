import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

import sys
sys.path.append("assets/style")
from styles import Style


class NuovoMovimentoWindow(tk.Toplevel):
    def __init__(self, parent, db_path, id_dichiarazione, on_success=None):
        super().__init__(parent)

        self.db_path = db_path
        self.id_dichiarazione = id_dichiarazione
        self.on_success = on_success

        self.title("Nuovo Movimento Plafond")
        self.geometry("550x420")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)

        self.create_widgets()
        self.load_documents()

    # ----------------------------------------------------------------
    # WIDGETS
    # ----------------------------------------------------------------
    def create_widgets(self):
        frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        title = tk.Label(
            frame,
            text="➕ Nuovo Consumo Plafond",
            font=("Arial", 15, "bold"),
            bg=Style.BACKGROUND_COLOR
        )
        title.pack(pady=(0, 20))

        # -------------------------
        # DOCUMENTO
        # -------------------------
        tk.Label(frame, text="Documento:", bg=Style.BACKGROUND_COLOR).pack(anchor="w")

        self.doc_cb = ttk.Combobox(frame, width=50, state="readonly")
        self.doc_cb.pack(pady=(0, 15))

        # -------------------------
        # IMPORTO
        # -------------------------
        tk.Label(frame, text="Importo consumato (€):", bg=Style.BACKGROUND_COLOR).pack(anchor="w")

        self.importo_entry = tk.Entry(frame, width=20)
        self.importo_entry.pack(pady=(0, 20))

        # -------------------------
        # BOTTONI
        # -------------------------
        btn_frame = tk.Frame(frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.pack(pady=10)

        salva_btn = tk.Button(
            btn_frame,
            text="Salva",
            bg="#4CAF50", fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2", padx=20, pady=7,
            command=self.salva
        )
        salva_btn.pack(side="left", padx=10)

        annulla_btn = tk.Button(
            btn_frame,
            text="Annulla",
            bg="#F44336", fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2", padx=20, pady=7,
            command=self.destroy
        )
        annulla_btn.pack(side="left", padx=10)

    # ----------------------------------------------------------------
    # CARICA DOCUMENTI DEL CLIENTE (LEGATI ALLA DICHIARAZIONE)
    # ----------------------------------------------------------------
    def load_documents(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Recupera il cliente da dichiarazione
            cur.execute("""
                SELECT id_soggetto FROM dichiarazioni_intento
                WHERE id=?
            """, (self.id_dichiarazione,))
            id_cliente = cur.fetchone()[0]

            # Carica documenti del cliente
            cur.execute("""
                SELECT id, numero_documento, data_documento, importo_imponibile
                FROM documenti
                WHERE soggetto_id=?
                ORDER BY data_documento DESC
            """, (id_cliente,))

            rows = cur.fetchall()
            conn.close()

        except Exception as e:
            messagebox.showerror("Errore", f"Errore caricamento documenti:\n{e}")
            return

        self.doc_list = rows
        display = []

        for did, num, data, imp in rows:
            # Le date nel database sono già in formato dd/mm/yyyy
            # Se per caso sono in formato YYYY-MM-DD, convertiamo
            if data:
                try:
                    # Se contiene '/' è già in formato dd/mm/yyyy
                    if '/' in str(data):
                        d_fmt = data
                    else:
                        # Se è in formato YYYY-MM-DD, converti
                        d_fmt = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    d_fmt = data  # Fallback: usa il valore originale
            else:
                d_fmt = ""
            display.append(f"{num} del {d_fmt} – € {imp:,.2f}")

        self.doc_cb["values"] = display

        # autocompilazione importo quando seleziono un documento
        self.doc_cb.bind("<<ComboboxSelected>>", self.precompila_importo)

    # ----------------------------------------------------------------
    # PRECOMPILA IMPORTO DA DOCUMENTO
    # ----------------------------------------------------------------
    def precompila_importo(self, event=None):
        idx = self.doc_cb.current()
        if idx < 0:
            return

        imponibile = self.doc_list[idx][3]
        self.importo_entry.delete(0, tk.END)
        self.importo_entry.insert(0, str(imponibile))

    # ----------------------------------------------------------------
    # SALVATAGGIO MOVIMENTO
    # ----------------------------------------------------------------
    def salva(self):
        if self.doc_cb.current() < 0:
            messagebox.showwarning("Attenzione", "Seleziona un documento.")
            return

        try:
            importo = float(self.importo_entry.get().replace(",", "."))
        except:
            messagebox.showwarning("Errore", "Importo non valido.")
            return

        did, num, data_doc, imponibile = self.doc_list[self.doc_cb.current()]

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Inserisci movimento
            # Usa formato dd/mm/yyyy per la data
            # Il plafond_residuo viene calcolato automaticamente dalla vista
            data_oggi = datetime.now().strftime('%d/%m/%Y')
            cur.execute("""
                INSERT INTO consumo_plafond
                (id_dichiarazione, id_documento, data, importo_consumato)
                VALUES (?, ?, ?, ?)
            """, (
                self.id_dichiarazione,
                did,
                data_oggi,
                importo
            ))

            conn.commit()
            conn.close()

            if self.on_success:
                self.on_success()

            messagebox.showinfo("Successo", "Movimento registrato correttamente.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Errore", f"Errore salvataggio movimento:\n{e}")
