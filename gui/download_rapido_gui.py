import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import subprocess
import os
from configparser import ConfigParser
from datetime import datetime
import sys
import json


class DownloadRapidoWindow(tk.Toplevel):
    """Finestra per il download rapido con log delle operazioni"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.process_running = False
        
        self.title("Download Rapido Acquisti")
        self.geometry("750x500")
        self.resizable(True, True)
        self.transient(parent)
        
        self.create_widgets()
        self.center_window()
        
        # Avvia automaticamente il download
        self.after(100, self.avvia_download)
        
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
        main_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="⚡ Download Rapido Fatture Acquisti",
            font=('Arial', 14, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 20))
        
        # Info box
        info_frame = tk.Frame(main_frame, bg="#E3F2FD", padx=15, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_label = tk.Label(
            info_frame,
            text="📋 Operazioni in corso:\n"
                 "1. Download fatture dal Sistema di Interscambio\n"
                 "2. Elaborazione e conversione file\n"
                 "3. Rinomina e organizzazione documenti\n"
                 "4. Aggiornamento configurazione",
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
            font=('Arial', 11, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=10,
            pady=10
        )
        text_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=80,
            height=15,
            font=('Courier', 9),
            state='disabled',
            bg="#FAFAFA"
        )
        self.text_area.pack(fill="both", expand=True)
        
        # Progress label
        self.progress_label = tk.Label(
            main_frame,
            text="",
            font=('Arial', 10),
            bg="#FFFFFF",
            fg="#666666"
        )
        self.progress_label.pack(pady=(0, 10))
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg="#FFFFFF")
        button_frame.pack(fill="x")
        
        # Pulsante Chiudi (inizialmente disabilitato)
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
            relief="flat",
            state="disabled"
        )
        self.btn_chiudi.pack(side="right")
        
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
    
    def esegui_script(self, nome_script, descrizione, args=None):
        """Esegue uno script Python e cattura l'output
        
        Args:
            nome_script: Nome dello script da eseguire
            descrizione: Descrizione dell'operazione
            args: Lista di argomenti opzionali da passare allo script (default: None)
        """
        self.aggiungi_messaggio(f"\n{'='*60}")
        self.aggiungi_messaggio(f"🔄 {descrizione}")
        self.aggiungi_messaggio(f"{'='*60}")
        
        try:
            # Ottieni il percorso dello script (dalla cartella scripts)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)  # Risale alla root del progetto
            script_path = os.path.join(project_root, 'scripts', nome_script)
            
            if not os.path.exists(script_path):
                self.aggiungi_messaggio(f"✗ ERRORE: Script non trovato: {script_path}")
                return False
            
            self.aggiungi_messaggio(f"📂 Esecuzione: {nome_script}")
            if args:
                self.aggiungi_messaggio(f"📋 Argomenti: {' '.join(args)}")
            self.aggiungi_messaggio("")
            
            # Cambia directory di lavoro alla root del progetto
            original_dir = os.getcwd()
            os.chdir(project_root)
            
            # Configura le variabili d'ambiente per Python
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Disabilita il buffering
            env['PYTHONIOENCODING'] = 'utf-8'  # Forza encoding UTF-8
            
            # Prepara il comando con eventuali argomenti
            cmd = [sys.executable, '-u', script_path]
            if args:
                cmd.extend(args)
            
            # Esegui lo script con output in tempo reale
            process = subprocess.Popen(
                cmd,  # -u per unbuffered
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # Nessun buffering
                universal_newlines=True,
                cwd=project_root,
                env=env,
                encoding='utf-8',
                errors='replace'  # Sostituisce caratteri non decodificabili
            )
            
            # Leggi l'output in tempo reale con timeout
            import select
            import time
            
            last_output_time = time.time()
            timeout_seconds = 300  # 5 minuti di timeout totale
            no_output_timeout = 30  # 30 secondi senza output
            
            while True:
                # Verifica timeout
                if time.time() - last_output_time > no_output_timeout:
                    self.aggiungi_messaggio("⏱ Attendo risposta dallo script...")
                    last_output_time = time.time()
                
                # Controlla se il processo è terminato
                if process.poll() is not None:
                    # Leggi eventuali output rimanenti
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.split('\n'):
                            line_clean = line.rstrip()
                            if line_clean:
                                # Rimuovi caratteri problematici
                                line_clean = line_clean.replace('✓', '[OK]').replace('✗', '[ERR]')
                                if len(line_clean) > 200:
                                    self.aggiungi_messaggio(f"  {line_clean[:200]}...")
                                else:
                                    self.aggiungi_messaggio(f"  {line_clean}")
                    break
                
                # Leggi con timeout breve
                try:
                    line = process.stdout.readline()
                    if line:
                        last_output_time = time.time()
                        line_clean = line.rstrip()
                        if line_clean:
                            # Rimuovi caratteri problematici e pulisci la stringa
                            line_clean = line_clean.replace('✓', '[OK]').replace('✗', '[ERR]')
                            # Rimuovi sequenze ANSI se presenti
                            import re
                            line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line_clean)
                            
                            if len(line_clean) > 200:
                                self.aggiungi_messaggio(f"  {line_clean[:200]}...")
                            else:
                                self.aggiungi_messaggio(f"  {line_clean}")
                    else:
                        time.sleep(0.1)  # Piccola pausa per non sovraccaricare la CPU
                except Exception as e:
                    self.aggiungi_messaggio(f"  [Avviso lettura output: {str(e)}]")
                    time.sleep(0.1)
            
            # Attendi il completamento
            return_code = process.wait(timeout=10)
            
            # Ripristina la directory originale
            os.chdir(original_dir)
            
            # Verifica il codice di ritorno
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
            self.aggiungi_messaggio(f"\n✗ ERRORE durante l'esecuzione: {str(e)}")
            # Ripristina la directory in caso di errore
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
    
    def aggiorna_config(self):
        """Aggiorna il file config.ini con la data odierna"""
        try:
            self.aggiungi_messaggio(f"\n{'='*60}")
            self.aggiungi_messaggio("📝 Aggiornamento configurazione")
            self.aggiungi_messaggio(f"{'='*60}")
            
            # Il config.ini si trova nella root del progetto
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "config.ini")
            
            config = ConfigParser()
            config.read(config_path)
            
            data_odierna = datetime.now().strftime("%d/%m/%Y")
            
            if 'Parametri' not in config:
                config.add_section('Parametri')
            
            config['Parametri']['aggiornamento'] = data_odierna
            
            with open(config_path, "w") as config_file:
                config.write(config_file)
            
            self.aggiungi_messaggio(f"✓ Configurazione aggiornata con data: {data_odierna}")
            return True
            
        except Exception as e:
            self.aggiungi_messaggio(f"✗ ERRORE aggiornamento config: {str(e)}")
            return False
    
    def avvia_download(self):
        """Avvia il processo di download in un thread separato"""
        self.process_running = True
        
        def esegui():
            try:
                self.aggiungi_messaggio("🚀 Avvio Download Rapido Fatture Acquisti")
                self.aggiungi_messaggio("")
                
                # Step 1: Speed Download
                self.aggiorna_progress("⏳ Fase 1/4: Download fatture...")
                if not self.esegui_script("speed_download.py", "Download fatture dal Sistema di Interscambio"):
                    raise Exception("Errore durante il download delle fatture")
                
                # Step 2: Scarfec32
                self.aggiorna_progress("⏳ Fase 2/4: Elaborazione file...")
                if not self.esegui_script("scarfec32.py", "Elaborazione e conversione file"):
                    raise Exception("Errore durante l'elaborazione dei file")
                
                # Step 3: Rinomina
                self.aggiorna_progress("⏳ Fase 3/4: Organizzazione documenti...")
                if not self.esegui_script("rinomina.py", "Rinomina e organizzazione documenti"):
                    raise Exception("Errore durante la rinomina dei file")
                
                # Step 4: Aggiorna config
                self.aggiorna_progress("⏳ Fase 4/4: Aggiornamento configurazione...")
                if not self.aggiorna_config():
                    raise Exception("Errore durante l'aggiornamento della configurazione")
                
                # Completato con successo
                self.aggiungi_messaggio("")
                self.aggiungi_messaggio("="*60)
                self.aggiungi_messaggio("🎉 DOWNLOAD RAPIDO COMPLETATO CON SUCCESSO!")
                self.aggiungi_messaggio("="*60)
                self.aggiorna_progress("✅ Tutte le operazioni completate con successo!")
                
                # Salva lo storico dei download
                self.salva_storico_download()
                
                # Mostra messaggio di successo
                self.after(0, lambda: messagebox.showinfo(
                    "Successo",
                    "Download rapido completato con successo!\n\n"
                    "Tutte le fatture sono state scaricate, elaborate e organizzate.",
                    parent=self
                ))
                
            except Exception as e:
                self.aggiungi_messaggio("")
                self.aggiungi_messaggio("="*60)
                self.aggiungi_messaggio(f"❌ ERRORE: {str(e)}")
                self.aggiungi_messaggio("="*60)
                self.aggiorna_progress("❌ Operazione interrotta a causa di errori")
                
                self.after(0, lambda: messagebox.showerror(
                    "Errore",
                    f"Si è verificato un errore durante il download:\n\n{str(e)}",
                    parent=self
                ))
            
            finally:
                self.process_running = False
                # Abilita il pulsante chiudi
                self.after(0, lambda: self.btn_chiudi.config(state="normal"))
        
        # Esegui in un thread separato
        thread = threading.Thread(target=esegui, daemon=True)
        thread.start()
    
    def salva_storico_download(self):
        """Salva lo storico del download rapido nel file JSON."""
        try:
            # Ottieni il percorso del file temporaneo creato da rinomina.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            temp_history_file = os.path.join(project_root, "temp_download_fatture.json")
            
            # Verifica se il file temporaneo esiste
            if not os.path.exists(temp_history_file):
                self.aggiungi_messaggio("ℹ️ Nessun dato da salvare nello storico")
                return
            
            # Leggi le fatture processate dal file temporaneo
            try:
                with open(temp_history_file, 'r', encoding='utf-8') as f:
                    fatture = json.load(f)
            except json.JSONDecodeError as e:
                self.aggiungi_messaggio(f"⚠️ Errore nella lettura dello storico: {e}")
                return
            
            # Importa e usa il modulo download_history
            scripts_dir = os.path.join(project_root, 'scripts')
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            
            try:
                from download_history import DownloadHistory
                
                # Crea il percorso del file storico nella root del progetto
                history_file = os.path.join(project_root, "download_history.json")
                history = DownloadHistory(history_file)
                
                # Aggiungi il download allo storico
                if history.add_download(fatture):
                    self.aggiungi_messaggio(f"📝 Storico aggiornato: {len(fatture)} fatture salvate")
                else:
                    self.aggiungi_messaggio("⚠️ Errore nel salvataggio dello storico")
            except ImportError as e:
                self.aggiungi_messaggio(f"⚠️ Impossibile importare download_history: {e}")
            except Exception as e:
                self.aggiungi_messaggio(f"⚠️ Errore nel salvataggio dello storico: {e}")
            finally:
                # Rimuovi il file temporaneo
                try:
                    if os.path.exists(temp_history_file):
                        os.remove(temp_history_file)
                except Exception as e:
                    self.aggiungi_messaggio(f"⚠️ Impossibile rimuovere file temporaneo: {e}")
                    
        except Exception as e:
            self.aggiungi_messaggio(f"⚠️ Errore generale nel salvataggio dello storico: {e}")
    
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
    root.withdraw()  # Nascondi la finestra principale
    
    app = DownloadRapidoWindow(root)
    
    root.mainloop()