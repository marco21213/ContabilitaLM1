import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime

import sys
sys.path.append("assets/style")
from styles import Style


class ModificaDichiarazioneWindow(tk.Toplevel):
    def __init__(self, parent, db_path, dichiarazione_id, on_success=None):
        super().__init__(parent)

        self.db_path = db_path
        self.dichiarazione_id = dichiarazione_id
        self.on_success = on_success

        self.title("Modifica Dichiarazione d'Intento")
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(bg=Style.BACKGROUND_COLOR)

        self.create_widgets()
        self.load_soggetti()
        self.load_dichiarazione_data()

    # ----------------------------------------------------------------
    #   LAYOUT
    # ----------------------------------------------------------------
    def create_widgets(self):
        frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="✏️ Modifica Dichiarazione d'Intento",
                         font=("Arial", 15, "bold"), bg=Style.BACKGROUND_COLOR)
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        # Configura colonne per allineamento
        frame.columnconfigure(1, weight=1)

        row = 1

        # ------------------------------
        # SOGGETTO
        # ------------------------------
        tk.Label(frame, text="Soggetto:", bg=Style.BACKGROUND_COLOR, 
                font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
        
        self.soggetto_cb = ttk.Combobox(frame, width=45, state="normal")
        self.soggetto_cb.grid(row=row, column=1, sticky="ew", pady=10)
        self.soggetto_cb.bind('<KeyRelease>', self.on_soggetto_keyrelease)
        self.soggetto_cb.bind('<FocusOut>', self.on_soggetto_focusout)
        row += 1

        # ------------------------------
        # NUMERO DICHIARAZIONE
        # ------------------------------
        tk.Label(frame, text="Numero Dichiarazione:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
        self.numero_entry = tk.Entry(frame, width=30)
        self.numero_entry.grid(row=row, column=1, sticky="w", pady=10)
        row += 1

        # ------------------------------
        # DATE
        # ------------------------------
        tk.Label(frame, text="Data Inizio:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
        self.data_inizio = DateEntry(
            frame, width=20, date_pattern="dd/mm/yyyy"
        )
        self.data_inizio.grid(row=row, column=1, sticky="w", pady=10)
        row += 1

        tk.Label(frame, text="Data Fine:", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
        self.data_fine = DateEntry(
            frame, width=20, date_pattern="dd/mm/yyyy"
        )
        self.data_fine.grid(row=row, column=1, sticky="w", pady=10)
        row += 1

        # ------------------------------
        # PLAFOND
        # ------------------------------
        tk.Label(frame, text="Plafond Iniziale (€):", bg=Style.BACKGROUND_COLOR,
                font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
        self.plafond_entry = tk.Entry(frame, width=20)
        self.plafond_entry.grid(row=row, column=1, sticky="w", pady=10)
        row += 1

        # ------------------------------
        # BOTTONI
        # ------------------------------
        btn_frame = tk.Frame(frame, bg=Style.BACKGROUND_COLOR)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(20, 0))

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
            self.soggetti_nomi = [r[1] for r in rows]
            self.soggetto_cb["values"] = self.soggetti_nomi

        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore caricamento soggetti:\n{e}")

    # ----------------------------------------------------------------
    #   CARICA DATI DICHIARAZIONE
    # ----------------------------------------------------------------
    def load_dichiarazione_data(self):
        """Carica i dati della dichiarazione dal database e li inserisce nei campi"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Carica dalla vista per avere tutti i dati inclusi plafond_residuo
            cur.execute("""
                SELECT id_soggetto, numero_dichiarazione, data_inizio, data_fine,
                       plafond_iniziale
                FROM vw_dichiarazioni_intento
                WHERE id = ?
            """, (self.dichiarazione_id,))

            row = cur.fetchone()
            conn.close()

            if not row:
                messagebox.showerror("Errore", "Dichiarazione non trovata.")
                self.destroy()
                return

            id_soggetto, numero, data_inizio, data_fine, plafond_iniziale = row

            # Trova il nome del soggetto
            soggetto_nome = None
            for sid, name in self.soggetti:
                if sid == id_soggetto:
                    soggetto_nome = name
                    break

            if soggetto_nome:
                self.soggetto_cb.set(soggetto_nome)

            # Precompila i campi
            self.numero_entry.insert(0, numero if numero else "")
            
            # Converti date da yyyy-mm-dd a dd/mm/yyyy per DateEntry
            if data_inizio:
                try:
                    data_inizio_obj = datetime.strptime(data_inizio, "%Y-%m-%d")
                    self.data_inizio.set_date(data_inizio_obj)
                except:
                    pass

            if data_fine:
                try:
                    data_fine_obj = datetime.strptime(data_fine, "%Y-%m-%d")
                    self.data_fine.set_date(data_fine_obj)
                except:
                    pass

            # Plafond iniziale
            if plafond_iniziale:
                self.plafond_entry.insert(0, str(plafond_iniziale))

        except Exception as e:
            messagebox.showerror("Errore", f"Errore caricamento dati:\n{e}")
            self.destroy()

    # ----------------------------------------------------------------
    #   RICERCA SOGGETTO CON TASTIERA
    # ----------------------------------------------------------------
    def on_soggetto_keyrelease(self, event):
        """Filtra i soggetti mentre l'utente digita"""
        value = event.widget.get().strip()
        
        if not value:
            self.soggetto_cb["values"] = self.soggetti_nomi
        else:
            # Filtra i soggetti che contengono il testo digitato (case-insensitive)
            filtered = [nome for nome in self.soggetti_nomi 
                       if value.lower() in nome.lower()]
            self.soggetto_cb["values"] = filtered
        
        # Mostra il dropdown se ci sono risultati
        if self.soggetto_cb["values"]:
            self.soggetto_cb.event_generate('<Down>')
    
    def on_soggetto_focusout(self, event):
        """Verifica che il valore selezionato sia valido quando perde il focus"""
        value = self.soggetto_cb.get().strip()
        if value and value not in self.soggetti_nomi:
            # Se il valore non è nella lista, cerca il match più vicino
            matches = [nome for nome in self.soggetti_nomi 
                      if value.lower() in nome.lower()]
            if matches:
                self.soggetto_cb.set(matches[0])
            else:
                # Se non c'è match, svuota il campo
                self.soggetto_cb.set("")

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

            # Aggiorna la dichiarazione (solo nella tabella dichiarazioni_intento)
            cur.execute("""
                UPDATE dichiarazioni_intento
                SET id_soggetto = ?,
                    numero_dichiarazione = ?,
                    data_inizio = ?,
                    data_fine = ?,
                    plafond_iniziale = ?
                WHERE id = ?
            """, (
                id_soggetto,
                self.numero_entry.get().strip(),
                d_in,
                d_fi,
                p_iniziale,
                self.dichiarazione_id
            ))

            conn.commit()
            conn.close()

            if self.on_success:
                self.on_success()

            messagebox.showinfo("Successo", "Dichiarazione modificata con successo.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Errore", f"Errore salvataggio:\n{e}")

