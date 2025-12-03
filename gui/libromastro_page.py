import tkinter as tk
from tkinter import ttk, messagebox
from tkinterweb import HtmlFrame
import sqlite3
import configparser
import os
from datetime import datetime
from pathlib import Path
import subprocess
import platform
import logging

# Per PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# Importa gli stili
import sys
sys.path.append('assets/style')
from styles import Style

# Sopprime gli errori di matplotlib quando si usa HtmlFrame
# Questi errori sono causati da un conflitto tra matplotlib e tkinterweb
# e non influenzano il funzionamento dell'applicazione
from io import StringIO

# Intercetta e ignora gli errori specifici di matplotlib
class MatplotlibErrorFilter:
    """Filtra gli errori di matplotlib causati dal conflitto con tkinterweb"""
    def __init__(self):
        self.original_stderr = sys.stderr
        
    def write(self, message):
        # Ignora solo gli errori specifici di matplotlib con winfo_containing
        if 'winfo_containing' in message and 'matplotlib' in message:
            return  # Ignora questo errore
        self.original_stderr.write(message)
        
    def flush(self):
        self.original_stderr.flush()

# Installa il filtro solo se matplotlib è importato
try:
    import matplotlib
    if not hasattr(sys.stderr, '_is_matplotlib_filter'):
        sys.stderr = MatplotlibErrorFilter()
        sys.stderr._is_matplotlib_filter = True
except ImportError:
    pass  # matplotlib non è installato, nessun problema


class LibroMastroWindow(tk.Frame):
    def __init__(self, parent, db_path=None):
        super().__init__(parent)
        self.parent = parent
        
        # Carica il percorso del database da config.ini se non fornito
        if db_path is None:
            self.db_path = self.get_db_path()
        else:
            self.db_path = db_path
            
        # Verifica che il database esista
        if not os.path.exists(self.db_path):
            messagebox.showerror("Errore", f"Database non trovato:\n{self.db_path}")
            self.destroy()
            return
            
        self.soggetti = []
        self.movimenti_data = []  # Per memorizzare i dati per PDF
        self.current_html = None
        self.create_widgets()
        self.load_soggetti()

    def get_db_path(self):
        """Carica il percorso del database da config.ini"""
        try:
            config = configparser.ConfigParser()
            # Se siamo in gui/, il config.ini è nella cartella parent
            config_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
            if not os.path.exists(config_path):
                # Prova nella stessa cartella
                config_path = "config.ini"
            
            config.read(config_path, encoding="utf-8")
            db_path = config.get("Autenticazione", "percorso_database", fallback="./database.db")
            
            # Se il percorso è relativo, risolvilo rispetto alla root del progetto
            if not os.path.isabs(db_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(project_root, db_path)
            
            return db_path
        except Exception as e:
            messagebox.showerror("Errore Config", f"Errore nel caricamento della configurazione:\n{str(e)}")
            return "./database.db"

    def create_widgets(self):
        # --- FILTRI ---
        filter_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        filter_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(filter_frame, text="Soggetto:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).grid(row=0, column=0, sticky="w")
        self.soggetto_cb = ttk.Combobox(filter_frame, state="readonly", width=40)
        self.soggetto_cb.grid(row=0, column=1, padx=(5, 20))

        tk.Label(filter_frame, text="Dal:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).grid(row=0, column=2, sticky="w")
        self.dal_entry = tk.Entry(filter_frame, width=12)
        self.dal_entry.insert(0, "01/01/2024")
        self.dal_entry.grid(row=0, column=3, padx=(5, 15))

        tk.Label(filter_frame, text="Al:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).grid(row=0, column=4, sticky="w")
        self.al_entry = tk.Entry(filter_frame, width=12)
        self.al_entry.insert(0, "31/12/2025")
        self.al_entry.grid(row=0, column=5, padx=(5, 15))

        tk.Button(filter_frame, text="Aggiorna", bg="#4CAF50", fg="white",
                  command=self.load_movimenti, font=("Arial", 10, "bold")).grid(row=0, column=6, padx=10)

        # --- TOTALI ---
        total_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        total_frame.pack(fill="x", padx=10, pady=(5, 10))

        tk.Label(total_frame, text="Totale Dare:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).pack(side="left")
        self.tot_dare_var = tk.StringVar(value="0.00")
        tk.Label(total_frame, textvariable=self.tot_dare_var, fg="blue", bg=Style.BACKGROUND_COLOR).pack(side="left", padx=10)

        tk.Label(total_frame, text="Totale Avere:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).pack(side="left")
        self.tot_avere_var = tk.StringVar(value="0.00")
        tk.Label(total_frame, textvariable=self.tot_avere_var, fg="blue", bg=Style.BACKGROUND_COLOR).pack(side="left", padx=10)

        tk.Label(total_frame, text="Saldo finale:", font=("Arial", 10, "bold"), bg=Style.BACKGROUND_COLOR).pack(side="left")
        self.saldo_finale_var = tk.StringVar(value="0.00")
        tk.Label(total_frame, textvariable=self.saldo_finale_var, fg="red", bg=Style.BACKGROUND_COLOR).pack(side="left", padx=10)

        # Toolbar per pulsanti
        toolbar = tk.Frame(self, bg=Style.WHITE, height=40)
        toolbar.pack(fill="x", padx=10, pady=(0, 5))

        tk.Button(toolbar, text="Esporta PDF", bg="#9C27B0", fg="white",
                 command=self.esporta_pdf, font=("Arial", 10, "bold"), width=15).pack(side="left", padx=5)

        # HTML Viewer
        html_container = tk.Frame(self, bg=Style.WHITE)
        html_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.html_frame = HtmlFrame(html_container, messages_enabled=False)
        self.html_frame.pack(fill="both", expand=True)

        # Mostra messaggio iniziale
        initial_html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; text-align: center; color: #666; }
                h2 { color: #333; }
            </style>
        </head>
        <body>
            <h2>Libro Mastro</h2>
            <p>Seleziona un soggetto e clicca su "Aggiorna" per visualizzare i movimenti</p>
        </body>
        </html>
        """
        self.html_frame.load_html(initial_html)

    def load_soggetti(self):
        """Carica l'elenco soggetti direttamente dalla vista."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT soggetto_id, ragione_sociale
                FROM vista_movimenti
                ORDER BY ragione_sociale
            """)
            rows = cur.fetchall()
            conn.close()

            self.soggetti = rows
            labels = [r[1] for r in rows]
            self.soggetto_cb['values'] = labels

        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore nel caricamento dei soggetti:\n{str(e)}\n\nPercorso DB: {self.db_path}")

    def parse_date(self, date_str):
        """Converte una data da dd/mm/yyyy a formato datetime"""
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except Exception:
            return None

    def load_movimenti(self):
        idx = self.soggetto_cb.current()
        if idx < 0:
            messagebox.showwarning("Attenzione", "Seleziona un soggetto")
            return
        soggetto_id = self.soggetti[idx][0]
        
        dal = self.dal_entry.get().strip()
        al = self.al_entry.get().strip()

        where_clauses = ["soggetto_id = ?"]
        params = [soggetto_id]

        # Valida e converte le date
        dal_date = None
        al_date = None

        if dal:
            dal_date = self.parse_date(dal)
            if not dal_date:
                messagebox.showwarning("Attenzione", "Data 'Dal' non valida. Usa formato GG/MM/AAAA")
                return

        if al:
            al_date = self.parse_date(al)
            if not al_date:
                messagebox.showwarning("Attenzione", "Data 'Al' non valida. Usa formato GG/MM/AAAA")
                return

        # Costruisci filtri per date in formato ISO (yyyy-mm-dd)
        if dal_date and al_date:
            where_clauses.append("data_movimento BETWEEN ? AND ?")
            params.extend([
                dal_date.strftime("%Y-%m-%d"),
                al_date.strftime("%Y-%m-%d")
            ])
        elif al_date:
            where_clauses.append("data_movimento <= ?")
            params.append(al_date.strftime("%Y-%m-%d"))
        elif dal_date:
            where_clauses.append("data_movimento >= ?")
            params.append(dal_date.strftime("%Y-%m-%d"))

        # La vista vista_movimenti ora include già sia documenti che pagamenti
        # Quindi possiamo usare direttamente la vista senza query UNION complesse
        query = f"""
            SELECT data_movimento, descrizione, dare, avere
            FROM vista_movimenti
            WHERE {" AND ".join(where_clauses)}
            ORDER BY data_movimento
        """

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Errore DB", f"Errore nel caricamento dei movimenti:\n{str(e)}")
            return

        # Memorizza i dati per PDF
        self.movimenti_data = []
        saldo = 0
        tot_dare = 0
        tot_avere = 0
        soggetto_nome = self.soggetti[idx][1]

        for r in rows:
            data_mov, descrizione, dare, avere = r
            dare = dare or 0
            avere = avere or 0
            saldo += dare - avere
            tot_dare += dare
            tot_avere += avere

            # Converte la data da formato ISO (yyyy-mm-dd) a formato italiano (dd/mm/yyyy)
            data_fmt = data_mov
            try:
                if data_mov and len(data_mov) == 10 and data_mov[4] == '-':
                    dt = datetime.strptime(data_mov, "%Y-%m-%d")
                    data_fmt = dt.strftime("%d/%m/%Y")
            except:
                pass

            # Memorizza per PDF e HTML
            self.movimenti_data.append({
                'data': data_fmt,
                'descrizione': descrizione or '',
                'dare': dare,
                'avere': avere,
                'saldo': saldo
            })

        # Aggiorna totali
        self.tot_dare_var.set(f"{tot_dare:.2f}")
        self.tot_avere_var.set(f"{tot_avere:.2f}")
        self.saldo_finale_var.set(f"{(tot_dare - tot_avere):.2f}")

        # Genera visualizzazione HTML
        self.generate_html_report(soggetto_nome, dal, al, tot_dare, tot_avere)

    def generate_html_report(self, soggetto_nome, dal, al, tot_dare, tot_avere):
        """Genera il report HTML formattato"""
        saldo_finale = tot_dare - tot_avere
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    margin: 1.5cm;
                }}
                body {{
                    font-family: 'Arial', 'Helvetica', sans-serif;
                    font-size: 12px;
                    margin: 0;
                    padding: 15px;
                    color: #000;
                    background-color: #fff;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    background-color: #fff;
                    font-size: 11px;
                }}
                thead {{
                    background-color: #2B579A !important;
                }}
                th {{
                    color: #ffffff !important;
                    background-color: #2B579A !important;
                    font-weight: bold;
                    padding: 8px 6px;
                    text-align: left;
                    border: 1px solid #1a3d6b;
                    font-size: 11px;
                }}
                th.text-center {{
                    text-align: center;
                }}
                th.text-right {{
                    text-align: right;
                }}
                td {{
                    padding: 6px;
                    border: 1px solid #ccc;
                    font-size: 11px;
                    vertical-align: top;
                }}
                tbody tr {{
                    border-bottom: 1px solid #ddd;
                }}
                tbody tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                tbody tr:hover {{
                    background-color: #f0f7ff;
                }}
                .text-right {{
                    text-align: right;
                    font-family: 'Courier New', monospace;
                }}
                .text-center {{
                    text-align: center;
                }}
                tfoot {{
                    border-top: 2px solid #2B579A;
                }}
                .total-row {{
                    background-color: #e8f4fd !important;
                    font-weight: bold;
                }}
                .total-row td {{
                    padding: 8px 6px;
                    font-size: 12px;
                    border-top: 2px solid #2B579A;
                }}
                .saldo-finale {{
                    background-color: #fff9e6 !important;
                    font-weight: bold;
                }}
                .saldo-finale td {{
                    border-top: 3px solid #2B579A;
                    font-size: 13px;
                }}
                .footer {{
                    margin-top: 25px;
                    padding: 10px;
                    text-align: center;
                    font-size: 10px;
                    color: #666;
                    border-top: 1px solid #ddd;
                }}
                @media print {{
                    body {{
                        margin: 0;
                        padding: 10px;
                    }}
                    table {{
                        page-break-inside: auto;
                    }}
                    tr {{
                        page-break-inside: avoid;
                        page-break-after: auto;
                    }}
                    thead {{
                        display: table-header-group;
                    }}
                    tfoot {{
                        display: table-footer-group;
                    }}
                }}
            </style>
        </head>
        <body>
            <table>
                <thead>
                    <tr>
                        <th class="text-center" style="width: 10%;">Data</th>
                        <th style="width: 45%;">Descrizione</th>
                        <th class="text-right" style="width: 15%;">Dare</th>
                        <th class="text-right" style="width: 15%;">Avere</th>
                        <th class="text-right" style="width: 15%;">Saldo</th>
                    </tr>
                </thead>
                <tbody>
        """

        for mov in self.movimenti_data:
            dare_str = f"€ {mov['dare']:,.2f}" if mov['dare'] > 0 else ""
            avere_str = f"€ {mov['avere']:,.2f}" if mov['avere'] > 0 else ""
            saldo_str = f"€ {mov['saldo']:,.2f}"
            
            html_content += f"""
                    <tr>
                        <td class="text-center">{mov['data']}</td>
                        <td>{mov['descrizione']}</td>
                        <td class="text-right">{dare_str}</td>
                        <td class="text-right">{avere_str}</td>
                        <td class="text-right">{saldo_str}</td>
                    </tr>
            """

        html_content += f"""
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="2" class="text-right"><strong>TOTALI</strong></td>
                        <td class="text-right"><strong>€ {tot_dare:,.2f}</strong></td>
                        <td class="text-right"><strong>€ {tot_avere:,.2f}</strong></td>
                        <td class="text-right"></td>
                    </tr>
                    <tr class="total-row saldo-finale">
                        <td colspan="4" class="text-right"><strong>SALDO FINALE</strong></td>
                        <td class="text-right"><strong>€ {saldo_finale:,.2f}</strong></td>
                    </tr>
                </tfoot>
            </table>

            <div class="footer">
                <p>Report generato automaticamente da Contabilità 3B</p>
            </div>
        </body>
        </html>
        """

        self.current_html = html_content
        self.html_frame.load_html(html_content)

    def esporta_pdf(self):
        """Esporta il libro mastro in PDF"""
        if not self.movimenti_data:
            messagebox.showwarning("Attenzione", "Nessun dato da esportare. Carica prima i movimenti.")
            return

        try:
            # Ottieni informazioni sul soggetto
            idx = self.soggetto_cb.current()
            if idx < 0:
                messagebox.showwarning("Attenzione", "Seleziona un soggetto")
                return
            
            soggetto_nome = self.soggetti[idx][1]
            dal = self.dal_entry.get().strip()
            al = self.al_entry.get().strip()

            # Calcola totali
            tot_dare = sum(m['dare'] for m in self.movimenti_data)
            tot_avere = sum(m['avere'] for m in self.movimenti_data)
            saldo_finale = tot_dare - tot_avere

            # Crea directory per PDF se non esiste
            outdir = Path('report_pdf')
            outdir.mkdir(exist_ok=True)

            # Nome file
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = outdir / f"LibroMastro_{soggetto_nome.replace(' ', '_')}_{date_str}.pdf"

            # Crea PDF
            c = canvas.Canvas(str(filename), pagesize=A4)
            width, height = A4
            x_margin = 40
            y = height - 40

            # Intestazione
            c.setFont('Helvetica-Bold', 16)
            c.drawString(x_margin, y, "LIBRO MASTRO")
            y -= 25

            c.setFont('Helvetica', 10)
            c.drawString(x_margin, y, f"Soggetto: {soggetto_nome}")
            y -= 15
            c.drawString(x_margin, y, f"Periodo: Dal {dal} al {al}")
            y -= 15
            c.drawString(x_margin, y, f"Data generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 30

            # Linea separatrice
            c.line(x_margin, y, width - x_margin, y)
            y -= 20

            # Intestazione colonne
            c.setFont('Helvetica-Bold', 9)
            col_widths = [80, 250, 80, 80, 100]
            col_x = x_margin
            headers = ["Data", "Descrizione", "Dare", "Avere", "Saldo"]
            
            for i, header in enumerate(headers):
                c.drawString(col_x, y, header)
                col_x += col_widths[i]

            y -= 15
            c.line(x_margin, y, width - x_margin, y)
            y -= 10

            # Dati
            c.setFont('Helvetica', 8)
            page_height = 60  # Altezza minima prima di nuova pagina

            for mov in self.movimenti_data:
                if y < page_height:
                    c.showPage()
                    y = height - 40
                    # Re-disegna intestazione colonne
                    c.setFont('Helvetica-Bold', 9)
                    col_x = x_margin
                    for i, header in enumerate(headers):
                        c.drawString(col_x, y, header)
                        col_x += col_widths[i]
                    y -= 15
                    c.line(x_margin, y, width - x_margin, y)
                    y -= 10
                    c.setFont('Helvetica', 8)

                # Data
                c.drawString(x_margin, y, mov['data'])
                # Descrizione (troncata se troppo lunga)
                desc = mov['descrizione'][:35] if len(mov['descrizione']) > 35 else mov['descrizione']
                c.drawString(x_margin + 80, y, desc)
                # Dare
                if mov['dare'] > 0:
                    c.drawRightString(x_margin + 330, y, f"€ {mov['dare']:,.2f}")
                # Avere
                if mov['avere'] > 0:
                    c.drawRightString(x_margin + 410, y, f"€ {mov['avere']:,.2f}")
                # Saldo
                c.drawRightString(x_margin + 490, y, f"€ {mov['saldo']:,.2f}")

                y -= 12

            # Totali
            if y < page_height + 50:
                c.showPage()
                y = height - 40

            y -= 10
            c.line(x_margin, y, width - x_margin, y)
            y -= 15

            c.setFont('Helvetica-Bold', 10)
            c.drawString(x_margin + 80, y, "TOTALI:")
            c.drawRightString(x_margin + 330, y, f"€ {tot_dare:,.2f}")
            c.drawRightString(x_margin + 410, y, f"€ {tot_avere:,.2f}")
            y -= 20

            c.setFont('Helvetica-Bold', 11)
            c.drawString(x_margin + 80, y, "SALDO FINALE:")
            c.drawRightString(x_margin + 490, y, f"€ {saldo_finale:,.2f}")

            c.save()

            # Apri il PDF
            if platform.system() == 'Windows':
                try:
                    os.startfile(str(filename))
                except:
                    subprocess.Popen(['start', str(filename)], shell=True)
            else:
                subprocess.Popen(['xdg-open', str(filename)])

            messagebox.showinfo('PDF creato', f'File generato:\n{filename}')

        except Exception as e:
            messagebox.showerror('Errore PDF', f'Errore durante la creazione del PDF:\n{str(e)}')