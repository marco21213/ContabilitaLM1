import tkinter as tk
from tkinter import ttk, messagebox
from tkinterweb import HtmlFrame
import sys
import os
import configparser
import glob
from lxml import etree
import tempfile
import pdfkit
import win32api
import win32print

sys.path.append('assets/style')
from styles import Style

class MastrinoClientiPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=Style.WHITE)
        self.parent = parent
        self.current_html = None
        
        # Leggi il percorso dalla configurazione
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.p7m_dir = config['Parametri']['cartellastampa']
        self.xsl_path = os.path.join(self.current_dir, '../documents/css_fatture', 'FoglioStileConDatiTrasmissione.xsl')
        
        self.wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        
        # Configura PDFKit
        try:
            self.config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
        except Exception as e:
            messagebox.showerror("Errore", f"Configurazione PDFKit fallita: {str(e)}")
            return
        
        # Controlla la validità dei percorsi
        if not all(os.path.exists(p) for p in [self.p7m_dir, self.xsl_path, self.wkhtmltopdf_path]):
            messagebox.showerror("Errore", "File o directory mancanti!")
            return
            
        self.setup_ui()
        self.load_files()
        
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)
        
        left_frame = tk.Frame(self, bg=Style.WHITE)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=5)
        
        ttk.Label(left_frame, text="Fatture disponibili", font=('Arial', 12, 'bold')).pack(pady=5)
        
        self.file_listbox = tk.Listbox(left_frame, width=30, font=('Arial', 10), selectmode=tk.SINGLE,
                                       bg=Style.WHITE, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        separator = ttk.Separator(self, orient="vertical", style="Blue.TSeparator")
        separator.grid(row=0, column=1, sticky="ns", padx=2)
        
        style = ttk.Style()
        style.configure("Blue.TSeparator", background="#000080")
        
        right_frame = tk.Frame(self, bg=Style.WHITE)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        
        button_frame = tk.Frame(right_frame, bg=Style.WHITE)
        button_frame.pack(fill="x", pady=5)
        
        self.stampa_btn = ttk.Button(button_frame, text="Stampa", command=self.stampa_fattura)
        self.stampa_btn.pack(side="left", padx=5)
        
        self.visualizza_btn = ttk.Button(button_frame, text="Visualizza", command=self.visualizza_fattura)
        self.visualizza_btn.pack(side="left", padx=5)
        
        self.pdf_btn = ttk.Button(button_frame, text="Visualizza PDF", command=self.visualizza_pdf)
        self.pdf_btn.pack(side="left", padx=5)
        
        self.html_frame = HtmlFrame(right_frame)
        self.html_frame.pack(fill="both", expand=True)
        
    def load_files(self):
        try:
            files = glob.glob(os.path.join(self.p7m_dir, '*.[xX][mM][lL]'))
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for file in files:
                basename = os.path.splitext(os.path.basename(file))[0]
                self.file_listbox.insert(tk.END, basename)
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei file: {str(e)}")
    
    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.visualizza_fattura()
            
    def visualizza_fattura(self):
        selection = self.file_listbox.curselection()
        if not selection:
            return
            
        try:
            basename = self.file_listbox.get(selection[0])
            filepath = os.path.join(self.p7m_dir, basename + '.xml')
            
            xml_tree = etree.parse(filepath)
            xsl_tree = etree.parse(self.xsl_path)
            transform = etree.XSLT(xsl_tree)
            self.current_html = str(transform(xml_tree))
            
            self.html_frame.load_html(self.current_html)
            
        except Exception as e:
            error_html = f"<html><body><h1>Errore</h1><p>{str(e)}</p></body></html>"
            self.html_frame.load_html(error_html)
            self.current_html = None
    
    def stampa_fattura(self):
        if not self.current_html:
            messagebox.showwarning("Attenzione", "Seleziona prima una fattura da stampare")
            return
        
        try:
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf.close()

            pdfkit.from_string(self.current_html, temp_pdf.name, configuration=self.config)

            printer_name = win32print.GetDefaultPrinter()
            win32api.ShellExecute(0, "print", temp_pdf.name, None, ".", 0)

            self.after(5000, lambda: os.unlink(temp_pdf.name))
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la stampa: {str(e)}")
    
    def visualizza_pdf(self):
        if not self.current_html:
            messagebox.showwarning("Attenzione", "Seleziona prima una fattura")
            return
            
        try:
            temp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
            temp_html.write(self.current_html.encode('utf-8'))
            temp_html.close()
            
            pdf_path = temp_html.name.replace('.html', '.pdf')
            pdfkit.from_file(temp_html.name, pdf_path, configuration=self.config)

            os.startfile(pdf_path)

            self.after(1000, lambda: [os.unlink(temp_html.name), os.unlink(pdf_path)])
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella creazione del PDF: {str(e)}")
