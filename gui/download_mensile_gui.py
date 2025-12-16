import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import os
from configparser import ConfigParser
from datetime import datetime
import calendar
import sys
import re


class DownloadMensileWindow(tk.Toplevel):
    """Finestra per il download mensile con selezione mese e anno"""
    
    def __init__(self, parent, tipo_documento):
        super().__init__(parent)
        
        self.parent = parent
        self.tipo_documento = tipo_documento  # 'acquisti' o 'vendite'
        self.process_running = False
        
        tipo_text = "Acquisti" if tipo_documento == "acquisti" else "Vendite"
        self.title(f"Download Mensile {tipo_text}")
        self.geometry("700x480")
        self.resizable(True, True)
        self.transient(parent)
        
        # Leggi config.ini
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
        tipo_text = "Acquisti" if self.tipo_documento == "acquisti" else "Vendite"
        emoji = "📥" if self.tipo_documento == "acquisti" else "📤"
        
        title_label = tk.Label(
            main_frame,
            text=f"{emoji} Download Mensile {tipo_text}",
            font=('Arial', 13, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 10))
        
        # Frame selezione periodo
        periodo_frame = tk.LabelFrame(
            main_frame,
            text="Seleziona Periodo",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=15,
            pady=10
        )
        periodo_frame.pack(fill="x", pady=(0, 10))
        
        # Anno
        row_anno = tk.Frame(periodo_frame, bg="#FFFFFF")
        row_anno.pack(fill="x", pady=5)
        
        tk.Label(
            row_anno,
            text="Anno:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=10,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.anno_var = tk.StringVar(value=str(datetime.now().year))
        anno_combo = ttk.Combobox(
            row_anno,
            textvariable=self.anno_var,
            values=[str(y) for y in range(2020, datetime.now().year + 1)],
            state="readonly",
            width=15,
            font=('Arial', 10)
        )
        anno_combo.pack(side="left")
        
        # Mese
        row_mese = tk.Frame(periodo_frame, bg="#FFFFFF")
        row_mese.pack(fill="x", pady=5)
        
        tk.Label(
            row_mese,
            text="Mese:",
            font=('Arial', 10, 'bold'),
            bg="#FFFFFF",
            width=10,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        mesi = [
            ("01", "Gennaio"), ("02", "Febbraio"), ("03", "Marzo"),
            ("04", "Aprile"), ("05", "Maggio"), ("06", "Giugno"),
            ("07", "Luglio"), ("08", "Agosto"), ("09", "Settembre"),
            ("10", "Ottobre"), ("11", "Novembre"), ("12", "Dicembre")
        ]
        
        self.mese_var = tk.StringVar()
        mese_combo = ttk.Combobox(
            row_mese,
            textvariable=self.mese_var,
            values=[f"{cod} - {nome}" for cod, nome in mesi],
            state="readonly",
            width=25,
            font=('Arial', 10)
        )
        mese_combo.pack(side="left")
        
        # Imposta mese corrente
        mese_corrente = f"{datetime.now().month:02d}"
        for i, (cod, nome) in enumerate(mesi):
            if cod == mese_corrente:
                mese_combo.current(i)
                break
        
        # Info box
        info_frame = tk.Frame(main_frame, bg="#E3F2FD", padx=10, pady=8)
        info_frame.pack(fill="x", pady=(0, 10))
        
        info_label = tk.Label(
            info_frame,
            text=f"ℹ️  Saranno scaricate tutte le fatture {tipo_text.lower()} del mese selezionato\n"
                 f"dal Sistema di Interscambio.",
            font=('Arial', 9),
            bg="#E3F2FD",
            fg="#1976D2",
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
            width=70,
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
        self.aggiungi_messaggio("Pronto per il download mensile.")
        self.aggiungi_messaggio("Seleziona mese e anno, poi clicca su 'Avvia Download'.\n")
    
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
    
    def calcola_date_mese(self, anno, mese):
        """Calcola primo e ultimo giorno del mese"""
        primo_giorno = 1
        ultimo_giorno = calendar.monthrange(anno, mese)[1]
        
        data_inizio = datetime(anno, mese, primo_giorno)
        data_fine = datetime(anno, mese, ultimo_giorno)
        
        return data_inizio, data_fine
    
    def aggiorna_config(self):
        """Aggiorna il file config.ini con i parametri del mese selezionato"""
        try:
            self.aggiungi_messaggio("📝 Aggiornamento parametri config.ini...")
            
            # Leggi config
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "config.ini")
            
            config = ConfigParser()
            config.read(config_path)
            
            # Ottieni anno e mese
            anno = int(self.anno_var.get())
            mese_str = self.mese_var.get().split(' - ')[0]  # Estrae "01" da "01 - Gennaio"
            mese = int(mese_str)
            
            # Calcola primo e ultimo giorno del mese
            data_inizio, data_fine = self.calcola_date_mese(anno, mese)
            
            dal_value = data_inizio.strftime('%d%m%Y')
            al_value = data_fine.strftime('%d%m%Y')
            
            # Tipo: 1 = ricezione (per download mensile usiamo sempre ricezione)
            tipo_value = '1'
            
            # VenOAcq: A = acquisti, V = vendite
            venoacq_value = 'A' if self.tipo_documento == 'acquisti' else 'V'
            venoacq_text = 'Acquisti' if venoacq_value == 'A' else 'Vendite'
            
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
            
            # Nome mese per log
            mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
            mese_nome = mesi_nomi[mese - 1]
            
            self.aggiungi_messaggio(f"  ✓ Periodo: {mese_nome} {anno}")
            self.aggiungi_messaggio(f"  ✓ Dal: {data_inizio.strftime('%d/%m/%Y')}")
            self.aggiungi_messaggio(f"  ✓ Al: {data_fine.strftime('%d/%m/%Y')}")
            self.aggiungi_messaggio(f"  ✓ Tipo: {venoacq_text}")
            self.aggiungi_messaggio("")
            
            return True
            
        except Exception as e:
            self.aggiungi_messaggio(f"✗ ERRORE aggiornamento config: {str(e)}")
            return False
    
    def esegui_script(self, nome_script, descrizione, args=None):
        """Esegue uno script Python e cattura l'output
        
        Args:
            nome_script: Nome dello script da eseguire
            descrizione: Descrizione dell'operazione
            args: Lista di argomenti opzionali da passare allo script (default: None)
        """
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
            if args:
                self.aggiungi_messaggio(f"📋 Argomenti: {' '.join(args)}")
            self.aggiungi_messaggio("")
            
            # Cambia directory di lavoro
            original_dir = os.getcwd()
            os.chdir(project_root)
            
            # Configura ambiente
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Prepara il comando con eventuali argomenti
            cmd = [sys.executable, '-u', script_path]
            if args:
                cmd.extend(args)
            
            # Esegui lo script
            process = subprocess.Popen(
                cmd,
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
        self.process_running = True
        self.btn_download.config(state='disabled')
        
        # Pulisci log
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state='disabled')
        
        def esegui():
            try:
                tipo_text = "Acquisti" if self.tipo_documento == "acquisti" else "Vendite"
                self.aggiungi_messaggio(f"🚀 Avvio Download Mensile {tipo_text}")
                self.aggiungi_messaggio("")
                
                # Aggiorna config con parametri del mese
                if not self.aggiorna_config():
                    raise Exception("Errore nell'aggiornamento della configurazione")
                
                # Step 1: Scarfec32
                self.aggiorna_progress("⏳ Fase 1/2: Download e elaborazione fatture...")
                if not self.esegui_script("scarfec32.py", "Download e elaborazione fatture"):
                    raise Exception("Errore durante il download delle fatture")
                
                # Step 2: Rinomina (senza copia in Stampa per download mensile)
                self.aggiorna_progress("⏳ Fase 2/2: Organizzazione documenti...")
                if not self.esegui_script("rinomina.py", "Rinomina e organizzazione documenti", ["--no-stampa"]):
                    raise Exception("Errore durante la rinomina dei file")
                
                # Completato
                self.aggiungi_messaggio("")
                self.aggiungi_messaggio("="*60)
                self.aggiungi_messaggio(f"🎉 DOWNLOAD MENSILE {tipo_text.upper()} COMPLETATO!")
                self.aggiungi_messaggio("="*60)
                self.aggiorna_progress("✅ Tutte le operazioni completate!")
                
                self.after(0, lambda: messagebox.showinfo(
                    "Successo",
                    f"Download mensile {tipo_text.lower()} completato con successo!\n\n"
                    f"Tutte le fatture sono state scaricate e organizzate.",
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
    
    # Test con acquisti
    app = DownloadMensileWindow(root, "acquisti")
    
    root.mainloop()