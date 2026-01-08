import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import sqlite3
import configparser

sys.path.append('assets/style')
from styles import Style

# Tentativo di importare matplotlib (opzionale)
MATPLOTLIB_AVAILABLE = False
plt = None
FigureCanvasTkAgg = None

try:
    # Prova a importare matplotlib in modo sicuro
    import os
    # Disabilita il backend interattivo per evitare problemi su Linux
    os.environ['MPLBACKEND'] = 'Agg'
    import matplotlib
    matplotlib.use('Agg', force=True)  # Forza backend non interattivo
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception as e:
    # Se matplotlib non è disponibile o causa errori, continua senza
    MATPLOTLIB_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning(f"Matplotlib non disponibile: {e}")


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

        # === Connessione al database e aggiornamento report_mensile ===
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Aggiorna report_mensile con i dati più recenti
            try:
                # Prima svuota la tabella
                cursor.execute("DELETE FROM report_mensile")
                
                # Calcola i totali mensili dalla tabella documenti
                # data_documento è in formato DD/MM/YYYY
                cursor.execute("""
                    INSERT INTO report_mensile (mese, totale_acquisti, totale_vendite)
                    SELECT 
                        substr(data_documento, 7, 4) || '-' || substr(data_documento, 4, 2) AS mese,
                        COALESCE(SUM(CASE WHEN segno = -1 THEN CAST(totale AS REAL) ELSE 0 END), 0) AS totale_acquisti,
                        COALESCE(SUM(CASE WHEN segno = 1 THEN CAST(totale AS REAL) ELSE 0 END), 0) AS totale_vendite
                    FROM documenti
                    WHERE data_documento IS NOT NULL 
                      AND data_documento != ''
                      AND length(data_documento) >= 10
                      AND substr(data_documento, 3, 1) = '/'
                      AND substr(data_documento, 6, 1) = '/'
                    GROUP BY substr(data_documento, 7, 4) || '-' || substr(data_documento, 4, 2)
                    ORDER BY mese DESC
                """)
                conn.commit()
            except Exception as e:
                # Se la tabella non esiste o c'è un errore, continua comunque
                print(f"Errore aggiornamento report_mensile: {e}")
                conn.rollback()
            
            # Legge i dati aggiornati
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
