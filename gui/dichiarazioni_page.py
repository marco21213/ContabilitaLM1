import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
from PIL import Image, ImageTk
import sys, os

# Import stile
sys.path.append("assets/style")
from styles import Style


class DichiarazioniIntentoPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.db_path = self.get_db_path()

        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            return

        self.configure(bg=Style.BACKGROUND_COLOR)

        self.create_header()
        self.create_button_bar()
        self.create_table()

        self.load_data()

    # --------------------------------------------------------
    #                 HEADER PAGINA
    # --------------------------------------------------------
    def create_header(self):
        header = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        header.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(Style.CONTENT_PADDING, 0))

        label = tk.Label(
            header,
            text="📄 DICHIARAZIONI D'INTENTO",
            font=("Arial", 16, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg="#000"
        )
        label.pack(side="left")

        self.counter_label = tk.Label(
            header,
            text="",
            font=("Arial", 10),
            bg=Style.BACKGROUND_COLOR,
            fg="#666"
        )
        self.counter_label.pack(side="right")

    # --------------------------------------------------------
    #                 BARRA PULSANTI
    # --------------------------------------------------------
    def create_button_bar(self):
        bar = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        bar.pack(fill="x", padx=Style.CONTENT_PADDING, pady=(10, 10))

        buttons = [
            ("nuovo", "Nuova", self.nuova_dichiarazione, "#4CAF50"),
            ("modifica", "Modifica", self.modifica_dichiarazione, "#FF9800"),
            ("cancella", "Cancella", self.cancella_dichiarazione, "#F44336"),
            ("documento", "Movimenti", self.apri_movimenti, "#2196F3"),
        ]

        icon_size = (32, 32)
        btn_size = 40

        for icon, text, cmd, color in buttons:
            f = tk.Frame(bar, bg=Style.BACKGROUND_COLOR)
            f.pack(side="left", padx=(0, 25))

            try:
                img = Image.open(f"assets/icon/{icon}.png")
                img = img.resize(icon_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                btn = tk.Button(f, image=photo, command=cmd,
                                bg=Style.BACKGROUND_COLOR, relief="flat",
                                cursor="hand2", width=btn_size, height=btn_size)
                btn.image = photo
                btn.pack()
            except:
                btn = tk.Button(f, text=text, command=cmd, bg=color,
                                fg="white", font=("Arial", 10, "bold"),
                                relief="flat", cursor="hand2")
                btn.pack()

            tk.Label(f, text=text, bg=Style.BACKGROUND_COLOR,
                     font=("Arial", 10, "bold")).pack(pady=(8, 0))

    # --------------------------------------------------------
    #                 TABELLA PRINCIPALE
    # --------------------------------------------------------
    def create_table(self):
        columns = ("SOGGETTO", "NUMERO", "DATA INIZIO", "DATA FINE", "PLAFOND", "RESIDUO")

        frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        frame.pack(fill="both", expand=True,
                   padx=Style.CONTENT_PADDING, pady=(0, Style.CONTENT_PADDING))

        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("SOGGETTO", width=200, anchor="w")
        self.tree.column("NUMERO", width=120, anchor="center")
        self.tree.column("DATA INIZIO", width=100, anchor="center")
        self.tree.column("DATA FINE", width=100, anchor="center")
        self.tree.column("PLAFOND", width=120, anchor="e")
        self.tree.column("RESIDUO", width=120, anchor="e")

        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("oddrow", background="#E6F3FF")
        self.tree.tag_configure("evenrow", background="#FFFFFF")

    # --------------------------------------------------------
    #                 CARICAMENTO DATI
    # --------------------------------------------------------
    def load_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("""
                SELECT di.id, s.ragione_sociale, di.numero_dichiarazione,
                       di.data_inizio, di.data_fine,
                       di.plafond_iniziale, di.plafond_residuo
                FROM dichiarazioni_intento di
                JOIN soggetti s ON s.id = di.id_soggetto
                ORDER BY di.data_inizio DESC
            """)

            rows = cur.fetchall()
            conn.close()

        except Exception as e:
            messagebox.showerror("Errore DB", str(e))
            return

        # Cancella righe precedenti
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Inserisci nuove righe
        for n, r in enumerate(rows):
            _, soggetto, numero, d1, d2, p_in, p_res = r

            data1 = datetime.strptime(d1, "%Y-%m-%d").strftime("%d/%m/%Y")
            data2 = datetime.strptime(d2, "%Y-%m-%d").strftime("%d/%m/%Y")

            self.tree.insert(
                "",
                "end",
                values=(
                    soggetto,
                    numero,
                    data1,
                    data2,
                    f"€ {p_in:,.2f}",
                    f"€ {p_res:,.2f}",
                ),
                tags=("evenrow" if n % 2 == 0 else "oddrow", f"id_{r[0]}")
            )

        self.counter_label.config(text=f"{len(rows)} dichiarazioni trovate")

    # --------------------------------------------------------
    #                 UTILS DB
    # --------------------------------------------------------
    def get_db_path(self):
        import configparser
        c = configparser.ConfigParser()
        c.read("config.ini", encoding="utf-8")
        return c.get("Autenticazione", "percorso_database", fallback="./database.db")

    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None

        tags = self.tree.item(sel[0], "tags")
        for t in tags:
            if t.startswith("id_"):
                return int(t[3:])
        return None

    # --------------------------------------------------------
    #                 PULSANTI
    # --------------------------------------------------------
    def nuova_dichiarazione(self):
        from dichiarazioni_page_nuova import NuovaDichiarazioneWindow
        NuovaDichiarazioneWindow(self, self.db_path, on_success=self.load_data)


    def modifica_dichiarazione(self):
        did = self.get_selected_id()
        if not did:
            messagebox.showwarning("Attenzione", "Seleziona una dichiarazione.")
            return

        messagebox.showinfo("Modifica", f"Da implementare — ID {did}")

    def cancella_dichiarazione(self):
        did = self.get_selected_id()
        if not did:
            messagebox.showwarning("Attenzione", "Seleziona una dichiarazione da eliminare.")
            return

        if not messagebox.askyesno("Conferma", "Eliminare questa dichiarazione?"):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM consumo_plafond WHERE id_dichiarazione=?", (did,))
            cur.execute("DELETE FROM dichiarazioni_intento WHERE id=?", (did,))
            conn.commit()
            conn.close()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def apri_movimenti(self):
        did = self.get_selected_id()
        if not did:
            messagebox.showwarning("Attenzione", "Seleziona una dichiarazione.")
            return

        def apri_movimenti(self):
            did = self.get_selected_id()
            if not did:
                messagebox.showwarning("Attenzione", "Seleziona una dichiarazione.")
                return

        from dichiarazioni_page_movimenti import MovimentiDichiarazioneWindow
        MovimentiDichiarazioneWindow(self, self.db_path, did)



if __name__ == "__main__":
    root = tk.Tk()
    root.title("Dichiarazioni d'intento")
    root.geometry("1200x600")
    app = DichiarazioniIntentoPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
