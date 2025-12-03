import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkcalendar import DateEntry
import threading
import subprocess
import os
from configparser import ConfigParser
from datetime import datetime
import sys
import re


class DownloadPeriodoWindow(tk.Toplevel):
    """Finestra per il download periodo con selezione parametri"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.process_running = False
        
        self.title("Download Periodo")
        self.geometry("750x520")
        self.resizable(True, True)
        self.transient(parent)
        
        # Leggi config.ini per valori di default
        self.config_path = "config.ini"
        self.config = ConfigParser()
        self.config.read(self.config_path)
        
        self.create_widgets()
        self.center_window()
        
    def center_window(self):
        """Centra la finestra sullo schermo"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        # Frame principale
        main_frame = tk.Frame(self, bg="#FFFFFF", padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="📅 Download Fatture per Periodo",
            font=('Arial', 13, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 10))
        
        # Frame opzioni
        options_frame = tk.LabelFrame(
            main_frame,
            text="Parametri di Ricerca",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=15,
            pady=10
        )
        options_frame.pack(fill="x", pady=(0, 10))
        
        # Data Inizio
        row1 = tk.Frame(options_frame, bg="#FFFFFF")
        row1.pack(fill="x", pady=5)
        
        tk.Label(
            row1,
            text="Data Inizio:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=15,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.data_inizio = DateEntry(
            row1,
            width=15,
            background='#4CAF50',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy',
            locale='it_IT'
        )
        self.data_inizio.pack(side="left")
        
        # Data Fine
        row2 = tk.Frame(options_frame, bg="#FFFFFF")
        row2.pack(fill="x", pady=5)
        
        tk.Label(
            row2,
            text="Data Fine:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=15,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.data_fine = DateEntry(
            row2,
            width=15,
            background='#4CAF50',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy',
            locale='it_IT'
        )
        self.data_fine.pack(side="left")
        
        # Tipo Data (Emissione/Ricezione)
        row3 = tk.Frame(options_frame, bg="#FFFFFF")
        row3.pack(fill="x", pady=5)
        
        tk.Label(
            row3,
            text="Opzione Tipo:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=15,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.tipo_data_var = tk.StringVar(value="emissione")
        
        radio_frame = tk.Frame(row3, bg="#FFFFFF")
        radio_frame.pack(side="left")
        
        tk.Radiobutton(
            radio_frame,
            text="Data di Emissione",
            variable=self.tipo_data_var,
            value="emissione",
            bg="#FFFFFF",
            font=('Arial', 9),
            activebackground="#FFFFFF"
        ).pack(side="left", padx=(0, 15))
        
        tk.Radiobutton(
            radio_frame,
            text="Data di Ricezione",
            variable=self.tipo_data_var,
            value="ricezione",
            bg="#FFFFFF",
            font=('Arial', 9),
            activebackground="#FFFFFF"
        ).pack(side="left")
        
        # Tipo Documento (Acquisti/Vendite)
        row4 = tk.Frame(options_frame, bg="#FFFFFF")
        row4.pack(fill="x", pady=5)
        
        tk.Label(
            row4,
            text="Tipo Documento:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=15,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.tipo_doc_var = tk.StringVar(value="acquisti")
        
        radio_frame2 = tk.Frame(row4, bg="#FFFFFF")
        radio_frame2.pack(side="left")
        
        tk.Radiobutton(
            radio_frame2,
            text="Acquisti",
            variable=self.tipo_doc_var,
            value="acquisti",
            bg="#FFFFFF",
            font=('Arial', 9),
            activebackground="#FFFFFF"
        ).pack(side="left", padx=(0, 15))
        
        tk.Radiobutton(
            radio_frame2,
            text="Vendite",
            variable=self.tipo_doc_var,
            value="vendite",
            bg="#FFFFFF",
            font=('Arial', 9),
            activebackground="#FFFFFF"
        ).pack(side="left")
        
        # Info box
        info_frame = tk.Frame(main_frame, bg="#E8F5E9", padx=10, pady=8)
        info_frame.pack(fill="x", pady=(0, 10))
        
        info_label = tk.Label(
            info_frame,
            text="ℹ️  Le fatture saranno scaricate dal Sistema di Interscambio\n"
                 "per il periodo e i parametri selezionati.",
            font=('Arial', 9),
            bg="#E8F5E9",
            fg="#2E7D32",
            justify="left",
            anchor="w"
        )
        info_label.pack(anchor="w")
        
        # Area di testo per i messaggi
        text_frame = tk.LabelFrame(
            main_frame,
            text="Log Operazioni",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=8,
            pady=8
        )
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=80,
            height=8,
            font=('Courier', 9),
            state='disabled',
            bg="#FAFAFA"
        )
        self.text_area.pack(fill="both", expand=True)
        
        # Progress label
        self.progress_label = tk.Label(
            main_frame,
            text="",
            font=('Arial', 9),
            bg="#FFFFFF",
            fg="#666666"
        )
        self.progress_label.pack(pady=(0, 8))
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg="#FFFFFF")
        button_frame.pack(fill="x")
        
        # Pulsante Avvia Download
        self.btn_download = tk.Button(
            button_frame,
            text="▶ Avvia Download",
            command=self.avvia_download,
            bg="#4CAF50",
            fg="white",
            font=('Arial', 11, 'bold'),
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        self.btn_download.pack(side="left", padx=(0, 10))
        
        # Pulsante Chiudi
        self.btn_chiudi = tk.Button(
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
        self.btn_chiudi.pack(side="right")
        
        # Messaggio iniziale
        self.aggiungi_messaggio("Pronto per il download.")
        self.aggiungi_messaggio("Seleziona i parametri e clicca su 'Avvia Download'.\n")
    
    def aggiungi_messaggio(self, messaggio, end='\n'):
        """Aggiunge un messaggio all'area di testo"""
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, messaggio + end)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')
        self.update_idletasks()
    
    def aggiorna_progress(self, testo):
        """Aggiorna la label di progresso"""
        self.progress_label.config(text=testo)
        self.update_idletasks()
    
    def valida_parametri(self):
        """Valida i parametri inseriti"""
        data_inizio = self.data_inizio.get_date()
        data_fine = self.data_fine.get_date()
        
        if data_inizio > data_fine:
            messagebox.showerror(
                "Errore",
                "La data di inizio deve essere precedente o uguale alla data di fine.",
                parent=self
            )
            return False
        
        return True
    
    def aggiorna_config(self):
        """Aggiorna il file config.ini con i parametri selezionati"""
        try:
            self.aggiungi_messaggio("📝 Aggiornamento parametri config.ini...")
            
            # Leggi config
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "config.ini")
            
            config = ConfigParser()
            config.read(config_path)
            
            # Converti date nel formato richiesto (ddmmyyyy)
            data_inizio = self.data_inizio.get_date()
            data_fine = self.data_fine.get_date()
            
            dal_value = data_inizio.strftime('%d%m%Y')
            al_value = data_fine.strftime('%d%m%Y')
            
            # Tipo: 0 = emissione, 1 = ricezione
            tipo_value = '1' if self.tipo_data_var.get() == 'ricezione' else '0'
            
            # VenOAcq: A = acquisti, V = vendite
            venoacq_value = 'A' if self.tipo_doc_var.get() == 'acquisti' else 'V'
            venoacq_value_text = 'Acquisti' if venoacq_value == 'A' else 'Vendite'
            
            # Aggiorna i parametri
            if 'Parametri' not in config:
                config.add_section('Parametri')
            
            config['Parametri']['dal'] = dal_value
            config['Parametri']['al'] = al_value
            config['Parametri']['tipo'] = tipo_value
            config['Parametri']['venoacq'] = venoacq_value
            
            # Salva
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            
            self.aggiungi_messaggio(f"  ✓ Data dal: {data_inizio.strftime('%d/%m/%Y')}")
            self.aggiungi_messaggio(f"  ✓ Data al: {data_fine.strftime('%d/%m/%Y')}")
            self.aggiungi_messaggio(f"  ✓ Tipo: {'Data di Ricezione' if tipo_value == '1' else 'Data di Emissione'}")
            self.aggiungi_messaggio(f"  ✓ Documento: {venoacq_value_text}")
            self.aggiungi_messaggio("")
            
            return True
            
        except Exception as e:
            self.aggiungi_messaggio(f"✗ ERRORE aggiornamento config: {str(e)}")
            return False
    
    def esegui_script(self, nome_script, descrizione):
        """Esegue uno script Python e cattura l'output"""
        self.aggiungi_messaggio(f"{'='*60}")
        self.aggiungi_messaggio(f"🔄 {descrizione}")
        self.aggiungi_messaggio(f"{'='*60}")
        
        try:
            # Ottieni il percorso dello script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            script_path = os.path.join(project_root, 'scripts', nome_script)
            
            if not os.path.exists(script_path):
                self.aggiungi_messaggio(f"✗ ERRORE: Script non trovato: {script_path}")
                return False
            
            self.aggiungi_messaggio(f"📂 Esecuzione: {nome_script}")
            self.aggiungi_messaggio("")
            
            # Cambia directory di lavoro
            original_dir = os.getcwd()
            os.chdir(project_root)
            
            # Configura ambiente
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Esegui lo script
            process = subprocess.Popen(
                [sys.executable, '-u', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                universal_newlines=True,
                cwd=project_root,
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            # Leggi output
            import time
            last_output_time = time.time()
            no_output_timeout = 30
            
            while True:
                if time.time() - last_output_time > no_output_timeout:
                    self.aggiungi_messaggio("⏱ Attendo risposta dallo script...")
                    last_output_time = time.time()
                
                if process.poll() is not None:
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.split('\n'):
                            line_clean = line.rstrip()
                            if line_clean:
                                line_clean = line_clean.replace('✓', '[OK]').replace('✗', '[ERR]')
                                line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line_clean)
                                if len(line_clean) > 200:
                                    self.aggiungi_messaggio(f"  {line_clean[:200]}...")
                                else:
                                    self.aggiungi_messaggio(f"  {line_clean}")
                    break
                
                try:
                    line = process.stdout.readline()
                    if line:
                        last_output_time = time.time()
                        line_clean = line.rstrip()
                        if line_clean:
                            line_clean = line_clean.replace('✓', '[OK]').replace('✗', '[ERR]')
                            line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line_clean)
                            
                            if len(line_clean) > 200:
                                self.aggiungi_messaggio(f"  {line_clean[:200]}...")
                            else:
                                self.aggiungi_messaggio(f"  {line_clean}")
                    else:
                        time.sleep(0.1)
                except Exception as e:
                    self.aggiungi_messaggio(f"  [Avviso lettura: {str(e)}]")
                    time.sleep(0.1)
            
            return_code = process.wait(timeout=10)
            os.chdir(original_dir)
            
            if return_code != 0:
                self.aggiungi_messaggio(f"\n⚠ Script terminato con codice: {return_code}")
            
            self.aggiungi_messaggio("")
            self.aggiungi_messaggio(f"✓ {descrizione} completato")
            return True
            
        except subprocess.TimeoutExpired:
            self.aggiungi_messaggio(f"\n✗ TIMEOUT: Lo script ha impiegato troppo tempo")
            try:
                process.kill()
                os.chdir(original_dir)
            except:
                pass
            return False
        except Exception as e:
            self.aggiungi_messaggio(f"\n✗ ERRORE: {str(e)}")
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
    
    def avvia_download(self):
        """Avvia il download in un thread separato"""
        # Valida parametri
        if not self.valida_parametri():
            return
        
        self.process_running = True
        self.btn_download.config(state='disabled')
        
        # Pulisci log
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state='disabled')
        
        def esegui():
            try:
                self.aggiungi_messaggio("🚀 Avvio Download per Periodo")
                self.aggiungi_messaggio("")
                
                # Aggiorna config con parametri selezionati
                if not self.aggiorna_config():
                    raise Exception("Errore nell'aggiornamento della configurazione")
                
                # Step 1: Scarfec32
                self.aggiorna_progress("⏳ Fase 1/2: Download e elaborazione fatture...")
                if not self.esegui_script("scarfec32.py", "Download e elaborazione fatture"):
                    raise Exception("Errore durante il download delle fatture")
                
                # Step 2: Rinomina
                self.aggiorna_progress("⏳ Fase 2/2: Organizzazione documenti...")
                if not self.esegui_script("rinomina.py", "Rinomina e organizzazione documenti"):
                    raise Exception("Errore durante la rinomina dei file")
                
                # Completato
                self.aggiungi_messaggio("")
                self.aggiungi_messaggio("="*60)
                self.aggiungi_messaggio("🎉 DOWNLOAD PERIODO COMPLETATO CON SUCCESSO!")
                self.aggiungi_messaggio("="*60)
                self.aggiorna_progress("✅ Tutte le operazioni completate!")
                
                self.after(0, lambda: messagebox.showinfo(
                    "Successo",
                    "Download periodo completato con successo!\n\n"
                    "Tutte le fatture sono state scaricate e organizzate.",
                    parent=self
                ))
                
            except Exception as e:
                self.aggiungi_messaggio("")
                self.aggiungi_messaggio("="*60)
                self.aggiungi_messaggio(f"❌ ERRORE: {str(e)}")
                self.aggiungi_messaggio("="*60)
                self.aggiorna_progress("❌ Operazione interrotta")
                
                self.after(0, lambda: messagebox.showerror(
                    "Errore",
                    f"Si è verificato un errore:\n\n{str(e)}",
                    parent=self
                ))
            
            finally:
                self.process_running = False
                self.after(0, lambda: self.btn_download.config(state="normal"))
        
        thread = threading.Thread(target=esegui, daemon=True)
        thread.start()
    
    def destroy(self):
        """Override del destroy per gestire la chiusura"""
        if self.process_running:
            risposta = messagebox.askyesno(
                "Attenzione",
                "Un'operazione è ancora in corso.\n\nSei sicuro di voler chiudere?",
                parent=self
            )
            if not risposta:
                return
        
        super().destroy()


# Per testare la finestra standalone
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    app = DownloadPeriodoWindow(root)
    
    root.mainloop()