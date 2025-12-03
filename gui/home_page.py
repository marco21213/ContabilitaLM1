import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import sqlite3
import configparser

sys.path.append('assets/style')
from styles import Style

# Tentativo di importare matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class HomePage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=Style.WHITE)

        tk.Label(
            self,
            text="Report Mensile - Ultimi 5 mesi",
            font=("Arial", 24, "bold"),
            bg=Style.WHITE,
            fg="black"
        ).pack(pady=20)

        # === Lettura percorso database dal file config.ini ===
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
        config = configparser.ConfigParser()
        config.read(config_path)

        if not config.has_option("Autenticazione", "percorso_database"):
            tk.Label(self, text="Percorso database non trovato in config.ini.", bg=Style.WHITE, fg="red").pack(pady=10)
            return

        db_path = config.get("Autenticazione", "percorso_database")

        if not os.path.exists(db_path):
            tk.Label(self, text=f"Database non trovato: {db_path}", bg=Style.WHITE, fg="red").pack(pady=10)
            return

        # === Connessione al database e lettura dati ===
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT mese, totale_acquisti, totale_vendite
                FROM report_mensile
                ORDER BY mese DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            tk.Label(self, text=f"Errore nel caricamento dati: {e}", bg=Style.WHITE, fg="red").pack(pady=10)
            return

        if not rows:
            tk.Label(self, text="Nessun dato disponibile nel report mensile.", bg=Style.WHITE, fg="gray").pack(pady=10)
            return

        rows.reverse()  # Mostra dal più vecchio al più recente

        # === Tabella dati ===
        tree = ttk.Treeview(self, columns=("mese", "acquisti", "vendite"), show="headings", height=6)
        tree.heading("mese", text="Mese")
        tree.heading("acquisti", text="Totale Acquisti (€)")
        tree.heading("vendite", text="Totale Vendite (€)")

        tree.column("mese", width=120, anchor="center")
        tree.column("acquisti", width=150, anchor="e")
        tree.column("vendite", width=150, anchor="e")

        for r in rows:
            tree.insert("", tk.END, values=r)

        tree.pack(pady=10)

        # === Grafico ===
        if MATPLOTLIB_AVAILABLE:
            mesi = [r[0] for r in rows]
            acquisti = [r[1] for r in rows]
            vendite = [r[2] for r in rows]

            fig, ax = plt.subplots(figsize=(6, 4))
            bar_width = 0.35
            x = range(len(mesi))

            ax.bar([i - bar_width/2 for i in x], acquisti, width=bar_width, label="Acquisti", alpha=0.7)
            ax.bar([i + bar_width/2 for i in x], vendite, width=bar_width, label="Vendite", alpha=0.7)

            ax.set_xticks(x)
            ax.set_xticklabels(mesi)
            ax.set_ylabel("Totale (€)")
            ax.set_title("Andamento Mensile Acquisti / Vendite")
            ax.legend()

            canvas = FigureCanvasTkAgg(fig, master=self)
            canvas.draw()
            canvas.get_tk_widget().pack(pady=20)
        else:
            tk.Label(
                self,
                text="Grafico non disponibile: installa matplotlib con 'pip install matplotlib'.",
                font=("Arial", 12),
                bg=Style.WHITE,
                fg="gray"
            ).pack(pady=20)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Home Page - Contabilità 3B")
    root.geometry("800x700")
    HomePage(root).pack(fill="both", expand=True)
    root.mainloop()
