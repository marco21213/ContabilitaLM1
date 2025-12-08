import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime

import sys
sys.path.append("assets/style")
from styles import Style


class NuovaDichiarazioneWindow(tk.Toplevel):
    def __init__(self, parent, db_path, on_success=None):
        super().__init__(parent)

        self.db_path = db_path
        self.on_success = on_success

        self.title("Nuova Dichiarazione d’Intento")
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)

        self.create_widgets()
        self.load_soggetti()

    # ----------------------------------------------------------------
    #   LAYOUT
    # ----------------------------------------------------------------
    def create_widgets(self):
        frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="➕ Nuova Dichiarazione d’Intento",
                         font=("Arial", 15, "bold"), bg=Style.BACKGROUND_COLOR)
        title.pack(pady=(0, 20))

        # ------------------------------
        # SOGGETTO
        # ------------------------------
        lab = tk.Label(frame, text="Soggetto:", bg=Style.BACKGROUND_COLOR)
        lab.pack(anchor="w")

        self.soggetto_cb = ttk.Combobox(frame, width=45, state="readonly")
        self.soggetto_cb.pack(pady=(0, 15))

        # ------------------------------
        # NUMERO DICHIARAZIONE
        # ------------------------------
        tk.Label(frame, text="Numero Dichiarazione:", bg=Style.BACKGROUND_COLOR).pack(anchor="w")
        self.numero_entry = tk.Entry(frame, width=30)
        self.numero_entry.pack(pady=(0, 15))

        # ------------------------------
        # DATE
        # ------------------------------
        tk.Label(frame, text="Data Inizio:", bg=Style.BACKGROUND_COLOR).pack(anchor="w")
        self.data_inizio = DateEntry(
            frame, width=20, date_pattern="dd/mm/yyyy"
        )
        self.data_inizio.pack(pady=(0, 15))

        tk.Label(frame, text="Data Fine:", bg=Style.BACKGROUND_COLOR).pack(anchor="w")
        self.data_fine = DateEntry(
            frame, width=20, date_pattern="dd/mm/yyyy"
        )
        self.data_fine.pack(pady=(0, 15))

        # ------------------------------
        # PLAFOND
        # ------------------------------
        tk.Label(frame, text="Plafond Iniziale (€):", bg=Style.BACKGROUND_COLOR).pack(anchor="w")
        self.plafond_entry = tk.Entry(frame, width=20)
        self.plafond_entry.pack(pady=(0, 20))

        # ------------------------------
        # BOTTONI
        # ------------------------------
        btn_frame = tk.Frame(frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.pack(pady=(20, 0))

        salva_btn = tk.Button(
            btn_frame, text="Salva",
            bg="#4CAF50", fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=20, pady=8,
            command=self.salva
        )
        salva_btn.pack(side="left", padx=10)

        annulla_btn = tk.Button(
            btn_frame, text="Annulla",
            bg="#F44336", fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=20, pady=8,
            command=self.destroy
        )
        annulla_btn.pack(side="left", padx=10)

    # ----------------------------------------------------------------
    #   CARICA SOGGETTI
    # ----------------------------------------------------------------
    def load_soggetti(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("SELECT id, ragione_sociale FROM soggetti ORDER BY ragione_sociale")
            rows = cur.fetchall()
            conn.close()

            self.soggetti = rows
            names = [r[1] for r in rows]
            self.soggetto_cb["values"] = names

        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore caricamento soggetti:\n{e}")

    # ----------------------------------------------------------------
    #   SALVATAGGIO
    # ----------------------------------------------------------------
    def salva(self):
        if not self.soggetto_cb.get():
            messagebox.showwarning("Attenzione", "Seleziona un soggetto.")
            return

        if not self.numero_entry.get().strip():
            messagebox.showwarning("Attenzione", "Inserisci un numero dichiarazione.")
            return

        try:
            p_iniziale = float(self.plafond_entry.get().replace(",", "."))
        except:
            messagebox.showwarning("Errore", "Plafond non valido.")
            return

        # ---- Recupero ID soggetto
        id_soggetto = None
        for sid, name in self.soggetti:
            if name == self.soggetto_cb.get():
                id_soggetto = sid
                break

        if id_soggetto is None:
            messagebox.showerror("Errore", "Soggetto non valido.")
            return

        # ---- Converti date in formato YYYY-MM-DD
        d_in = datetime.strptime(self.data_inizio.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        d_fi = datetime.strptime(self.data_fine.get(), "%d/%m/%Y").strftime("%Y-%m-%d")

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO dichiarazioni_intento
                (id_soggetto, numero_dichiarazione, data_inizio, data_fine,
                 plafond_iniziale, plafond_residuo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                id_soggetto,
                self.numero_entry.get().strip(),
                d_in,
                d_fi,
                p_iniziale,
                p_iniziale     # residuo = iniziale
            ))

            conn.commit()
            conn.close()

            if self.on_success:
                self.on_success()

            messagebox.showinfo("Successo", "Dichiarazione salvata con successo.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Errore", f"Errore salvataggio:\n{e}")
