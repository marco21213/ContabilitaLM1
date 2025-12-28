import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

import sys
sys.path.append("assets/style")
from styles import Style


class MovimentiDichiarazioneWindow(tk.Toplevel):
    def __init__(self, parent, db_path, id_dichiarazione):
        super().__init__(parent)

        self.db_path = db_path
        self.id_dichiarazione = id_dichiarazione

        self.title("Movimenti Plafond – Dichiarazione")
        self.geometry("900x550")
        self.configure(bg=Style.BACKGROUND_COLOR)
        self.resizable(True, True)

        self.create_header()
        self.create_button_bar()
        self.create_table()
        self.load_data()

    # -------------------------------------------------------------------
    # HEADER
    # -------------------------------------------------------------------
    def create_header(self):
        header = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        header.pack(fill="x", padx=20, pady=(20, 10))

        self.title_label = tk.Label(
            header,
            text="Movimenti Dichiarazione",
            font=("Arial", 16, "bold"),
            bg=Style.BACKGROUND_COLOR
        )
        self.title_label.pack(side="left")

        self.plafond_label = tk.Label(
            header,
            text="",
            bg=Style.BACKGROUND_COLOR,
            fg="#444",
            font=("Arial", 11)
        )
        self.plafond_label.pack(side="right")

    # -------------------------------------------------------------------
    # BARRA PULSANTI
    # -------------------------------------------------------------------
    def create_button_bar(self):
        bar = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        bar.pack(fill="x", padx=20, pady=(5, 10))

        btn_nuovo = tk.Button(
            bar,
            text="➕ Nuovo Movimento",
            bg="#4CAF50", fg="white",
            font=("Arial", 10, "bold"),
            padx=10, pady=6,
            cursor="hand2",
            command=self.nuovo_movimento
        )
        btn_nuovo.pack(side="left", padx=5)

        btn_elimina = tk.Button(
            bar,
            text="🗑 Elimina Movimento",
            bg="#F44336", fg="white",
            font=("Arial", 10, "bold"),
            padx=10, pady=6,
            cursor="hand2",
            command=self.elimina_movimento
        )
        btn_elimina.pack(side="left", padx=5)

    # -------------------------------------------------------------------
    # TABELLA
    # -------------------------------------------------------------------
    def create_table(self):
        columns = ("DATA", "DOCUMENTO", "IMPORTO")

        frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("DATA", width=120, anchor="center")
        self.tree.column("DOCUMENTO", width=200, anchor="w")
        self.tree.column("IMPORTO", width=120, anchor="e")

        # Scrollbar
        sy = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=sy.set, xscroll=sx.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    # -------------------------------------------------------------------
    # CARICAMENTO DATI
    # -------------------------------------------------------------------
    def load_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Leggi dati dichiarazione dalla vista
            cur.execute("""
                SELECT numero_dichiarazione, plafond_iniziale, plafond_residuo
                FROM vw_dichiarazioni_intento
                WHERE id = ?
            """, (self.id_dichiarazione,))
            dichiarazione = cur.fetchone()

            # Leggi movimenti
            cur.execute("""
                SELECT cp.id, cp.data, cp.importo_consumato,
                       d.numero_documento, d.data_documento
                FROM consumo_plafond cp
                LEFT JOIN documenti d ON d.id = cp.id_documento
                WHERE cp.id_dichiarazione = ?
                ORDER BY cp.data ASC
            """, (self.id_dichiarazione,))

            movimenti = cur.fetchall()

            conn.close()

        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore nel caricamento movimenti:\n{e}")
            return

        # Aggiorna intestazione
        numero, p_ini, p_res = dichiarazione

        self.title_label.config(
            text=f"Movimenti – Dichiarazione {numero}"
        )
        self.plafond_label.config(
            text=f"Plafond Iniziale: € {p_ini:,.2f}   •   Residuo: € {p_res:,.2f}"
        )

        # Pulisci tabella
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Popola tabella
        for row in movimenti:
            mid, data, imp, num_doc, data_doc = row

            # La data in consumo_plafond è già in formato dd/mm/yyyy
            data_fmt = data if data else ""
            imp_fmt = f"€ {imp:,.2f}"
            # La data_documento potrebbe essere in formato dd/mm/yyyy o yyyy-mm-dd
            if num_doc and data_doc:
                try:
                    # Prova formato dd/mm/yyyy
                    if '/' in data_doc:
                        doc_txt = f"{num_doc} del {data_doc}"
                    else:
                        # Prova formato yyyy-mm-dd
                        doc_txt = f"{num_doc} del {datetime.strptime(data_doc, '%Y-%m-%d').strftime('%d/%m/%Y')}"
                except:
                    doc_txt = f"{num_doc} del {data_doc}"
            else:
                doc_txt = "-"

            self.tree.insert(
                "",
                "end",
                values=(data_fmt, doc_txt, imp_fmt),
                tags=(f"id_{mid}",)
            )

    # -------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------
    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        tags = self.tree.item(sel[0], "tags")
        for t in tags:
            if t.startswith("id_"):
                return int(t[3:])
        return None

    # -------------------------------------------------------------------
    # BOTTONI
    # -------------------------------------------------------------------
    def nuovo_movimento(self):
        from dichiarazioni_page_nuovo_movimento import NuovoMovimentoWindow
        NuovoMovimentoWindow(
            self, self.db_path, self.id_dichiarazione,
            on_success=self.load_data
        )

    def elimina_movimento(self):
        mid = self.get_selected_id()
        if not mid:
            messagebox.showwarning("Attenzione", "Seleziona un movimento da eliminare.")
            return

        if not messagebox.askyesno("Conferma", "Eliminare questo movimento?"):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Recupera importo movimento
            cur.execute("SELECT importo_consumato FROM consumo_plafond WHERE id=?", (mid,))
            imp = cur.fetchone()[0]

            # Elimina movimento
            # Il plafond_residuo viene calcolato automaticamente dalla vista
            cur.execute("DELETE FROM consumo_plafond WHERE id=?", (mid,))

            conn.commit()
            conn.close()

            self.load_data()

        except Exception as e:
            messagebox.showerror("Errore", f"Errore eliminazione movimento:\n{e}")
