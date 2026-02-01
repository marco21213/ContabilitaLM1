"""
Pagina per la gestione degli appunti in stile blog.
Interfaccia semplice: TITOLO - CONTENUTO (con supporto HTML)
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
import os
import sys
import platform
from datetime import datetime
from typing import Optional
import re
import webbrowser
import shutil
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'assets', 'style'))
from styles import Style

# Importa la funzione per ottenere il percorso del database
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from parametri_db import get_db_path

# Importa HtmlFrame per visualizzazione HTML
try:
    from tkinterweb import HtmlFrame
    HTML_SUPPORT = True
except ImportError:
    HTML_SUPPORT = False
    print("tkinterweb non disponibile, HTML non supportato")


class AppuntiPage(tk.Frame):
    """Pagina per la gestione degli appunti in stile blog"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=Style.BACKGROUND_COLOR)
        
        # Inizializza il database
        self.db_path = get_db_path()
        self.init_database()
        
        # Crea la cartella per le immagini degli appunti
        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'appunti_images')
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Variabili
        self.selected_appunto_id = None
        self.telegram_bot_manager = None
        
        # Crea l'interfaccia
        self.create_ui()
        
        # Carica gli appunti
        self.refresh_appunti()
        
        # Inizializza il bot manager
        self.init_telegram_bot()
        
        # Avvia aggiornamento periodico se il bot è attivo
        self.start_periodic_refresh()
    
    def init_database(self):
        """Inizializza la tabella appunti se non esiste"""
        try:
            from scripts.init_appunti_database import init_appunti_tables
            init_appunti_tables()
        except Exception as e:
            print(f"Errore inizializzazione database appunti: {e}")
    
    def create_ui(self):
        """Crea l'interfaccia utente"""
        # Titolo e pulsante nuovo
        header_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            header_frame,
            text="📝 Appunti",
            font=("Arial", 24, "bold"),
            bg=Style.BACKGROUND_COLOR,
            fg=Style.MENU_HEADER_BG
        ).pack(side='left')
        
        # Frame pulsanti header
        buttons_frame = tk.Frame(header_frame, bg=Style.BACKGROUND_COLOR)
        buttons_frame.pack(side='right')
        
        # Pulsante Telegram Bot
        self.telegram_btn = tk.Button(
            buttons_frame,
            text="🤖 Telegram",
            command=self.toggle_telegram_bot,
            bg="#0088cc",
            fg="white",
            font=("Arial", 11),
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=10
        )
        self.telegram_btn.pack(side='left', padx=(0, 10))
        
        # Pulsante nuovo appunto
        tk.Button(
            buttons_frame,
            text="+ Nuovo Appunto",
            command=self.nuovo_appunto,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=10
        ).pack(side='left')
        
        # Frame principale con layout orizzontale
        main_frame = tk.Frame(self, bg=Style.BACKGROUND_COLOR)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Pannello sinistro: lista appunti
        left_panel = tk.Frame(main_frame, bg=Style.WHITE, relief=tk.RAISED, bd=1)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        left_panel.config(width=400)
        
        self.create_list_panel(left_panel)
        
        # Pannello destro: dettaglio appunto
        right_panel = tk.Frame(main_frame, bg=Style.WHITE, relief=tk.RAISED, bd=1)
        right_panel.pack(side='right', fill='both', expand=True)
        
        self.create_detail_panel(right_panel)
    
    def create_list_panel(self, parent):
        """Crea il pannello con la lista degli appunti"""
        # Titolo
        tk.Label(
            parent,
            text="Lista Appunti",
            font=("Arial", 14, "bold"),
            bg=Style.WHITE,
            fg=Style.MENU_HEADER_BG
        ).pack(pady=(15, 10), padx=15, anchor='w')
        
        # Lista appunti
        list_frame = tk.Frame(parent, bg=Style.WHITE)
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Listbox per gli appunti
        self.appunti_listbox = tk.Listbox(
            list_frame,
            font=("Arial", 11),
            bg=Style.WHITE,
            selectbackground=Style.MENU_HEADER_BG,
            selectforeground='white',
            yscrollcommand=scrollbar.set,
            activestyle='none'
        )
        self.appunti_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.appunti_listbox.yview)
        
        self.appunti_listbox.bind('<<ListboxSelect>>', self.on_appunto_selected)
        self.appunti_listbox.bind('<Double-1>', lambda e: self.modifica_appunto())
        
        # Pulsanti azioni
        buttons_frame = tk.Frame(parent, bg=Style.WHITE)
        buttons_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        tk.Button(
            buttons_frame,
            text="✏️ Modifica",
            command=self.modifica_appunto,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=8
        ).pack(side='left', padx=(0, 5))
        
        tk.Button(
            buttons_frame,
            text="🗑️ Elimina",
            command=self.elimina_appunto,
            bg="#f44336",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=8
        ).pack(side='left')
    
    def create_detail_panel(self, parent):
        """Crea il pannello con i dettagli dell'appunto"""
        # Frame contenuto
        content_frame = tk.Frame(parent, bg=Style.WHITE)
        content_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Titolo appunto
        self.dettaglio_titolo = tk.Label(
            content_frame,
            text="",
            font=("Arial", 18, "bold"),
            bg=Style.WHITE,
            fg="#333",
            wraplength=600,
            anchor='w',
            justify='left'
        )
        self.dettaglio_titolo.pack(fill='x', pady=(0, 15))
        
        # Separatore
        separator = tk.Frame(content_frame, bg="#ddd", height=1)
        separator.pack(fill='x', pady=(0, 15))
        
        # Contenuto - usa HtmlFrame se disponibile, altrimenti Text widget
        if HTML_SUPPORT:
            # Usa HtmlFrame per visualizzare HTML
            self.dettaglio_contenuto_html = HtmlFrame(
                content_frame, 
                messages_enabled=False
            )
            self.dettaglio_contenuto_html.pack(fill='both', expand=True)
            self.dettaglio_contenuto = None  # Non usato in modalità HTML
        else:
            # Fallback a Text widget normale
            text_frame = tk.Frame(content_frame, bg=Style.WHITE)
            text_frame.pack(fill='both', expand=True)
            
            scrollbar_text = tk.Scrollbar(text_frame)
            scrollbar_text.pack(side='right', fill='y')
            
            self.dettaglio_contenuto = tk.Text(
                text_frame,
                font=("Arial", 11),
                bg=Style.WHITE,
                wrap=tk.WORD,
                state=tk.DISABLED,
                yscrollcommand=scrollbar_text.set,
                padx=5,
                pady=5
            )
            self.dettaglio_contenuto.pack(side='left', fill='both', expand=True)
            scrollbar_text.config(command=self.dettaglio_contenuto.yview)
            self.dettaglio_contenuto_html = None
    
    def refresh_appunti(self):
        """Aggiorna la lista degli appunti"""
        # Pulisci la listbox
        self.appunti_listbox.delete(0, tk.END)
        
        # Dizionario per mappare indice -> appunto_id
        self.appunti_map = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, titolo
                FROM appunti
                ORDER BY titolo ASC
            """)
            
            appunti = cursor.fetchall()
            conn.close()
            
            for idx, appunto in enumerate(appunti):
                appunto_id, titolo = appunto
                
                # Aggiungi alla listbox (solo titolo, senza data)
                self.appunti_listbox.insert(tk.END, titolo)
                self.appunti_map[idx] = appunto_id
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento degli appunti: {e}")
    
    def on_appunto_selected(self, event):
        """Gestisce la selezione di un appunto"""
        selection = self.appunti_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx in self.appunti_map:
                self.selected_appunto_id = self.appunti_map[idx]
                self.show_dettaglio(self.selected_appunto_id)
    
    def show_dettaglio(self, appunto_id: int):
        """Mostra i dettagli di un appunto"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT titolo, contenuto
                FROM appunti
                WHERE id = ?
            """, (appunto_id,))
            
            appunto = cursor.fetchone()
            conn.close()
            
            if appunto:
                titolo, contenuto = appunto
                
                self.dettaglio_titolo.config(text=titolo)
                
                # Visualizza contenuto HTML o testo normale
                if HTML_SUPPORT and self.dettaglio_contenuto_html:
                    # Usa HtmlFrame per visualizzare HTML
                    html_content = contenuto or ""
                    # Se non è già HTML valido, avvolgilo in tag base
                    if html_content and not html_content.strip().startswith('<'):
                        html_content = f"<div style='padding: 10px; font-family: Arial;'>{html_content.replace(chr(10), '<br>')}</div>"
                    elif not html_content:
                        html_content = "<div style='padding: 10px;'>Nessun contenuto</div>"
                    
                    self.dettaglio_contenuto_html.load_html(f"<html><body>{html_content}</body></html>")
                elif self.dettaglio_contenuto:
                    # Fallback a Text widget
                    self.dettaglio_contenuto.config(state=tk.NORMAL)
                    self.dettaglio_contenuto.delete('1.0', tk.END)
                    self.dettaglio_contenuto.insert('1.0', contenuto or "")
                    self.dettaglio_contenuto.config(state=tk.DISABLED)
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del dettaglio: {e}")
    
    def clear_dettaglio(self):
        """Pulisce il pannello dei dettagli"""
        self.dettaglio_titolo.config(text="")
        if HTML_SUPPORT and self.dettaglio_contenuto_html:
            self.dettaglio_contenuto_html.load_html("<html><body><div style='padding: 10px;'>Nessun appunto selezionato</div></body></html>")
        elif self.dettaglio_contenuto:
            self.dettaglio_contenuto.config(state=tk.NORMAL)
            self.dettaglio_contenuto.delete('1.0', tk.END)
            self.dettaglio_contenuto.config(state=tk.DISABLED)
        self.selected_appunto_id = None
    
    def nuovo_appunto(self):
        """Apre la finestra per creare un nuovo appunto"""
        dialog = AppuntoDialog(self, self.db_path, images_dir=self.images_dir)
        if dialog.result:
            # Aggiorna la lista
            self.refresh_appunti()
            # Seleziona il nuovo appunto creato
            if dialog.created_appunto_id:
                self.select_appunto_by_id(dialog.created_appunto_id)
            else:
                self.clear_dettaglio()
            # Forza l'aggiornamento della GUI
            self.update_idletasks()
    
    def modifica_appunto(self):
        """Modifica l'appunto selezionato"""
        if not self.selected_appunto_id:
            messagebox.showwarning("Attenzione", "Seleziona un appunto da modificare")
            return
        
        old_id = self.selected_appunto_id
        dialog = AppuntoDialog(self, self.db_path, appunto_id=old_id, images_dir=self.images_dir)
        if dialog.result:
            # Aggiorna la lista
            self.refresh_appunti()
            # Mostra i dettagli aggiornati
            self.select_appunto_by_id(old_id)
            # Forza l'aggiornamento della GUI
            self.update_idletasks()
    
    def select_appunto_by_id(self, appunto_id: int):
        """Seleziona un appunto nella lista per ID e mostra i dettagli"""
        # Trova l'indice dell'appunto nella mappa
        for idx, mapped_id in self.appunti_map.items():
            if mapped_id == appunto_id:
                # Seleziona nella listbox
                self.appunti_listbox.selection_clear(0, tk.END)
                self.appunti_listbox.selection_set(idx)
                self.appunti_listbox.see(idx)  # Scrolla per renderlo visibile
                # Aggiorna i dettagli
                self.selected_appunto_id = appunto_id
                self.show_dettaglio(appunto_id)
                return
        # Se non trovato, mostra comunque i dettagli
        self.selected_appunto_id = appunto_id
        self.show_dettaglio(appunto_id)
    
    def elimina_appunto(self):
        """Elimina l'appunto selezionato"""
        if not self.selected_appunto_id:
            messagebox.showwarning("Attenzione", "Seleziona un appunto da eliminare")
            return
        
        if messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questo appunto?"):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM appunti WHERE id = ?", (self.selected_appunto_id,))
                conn.commit()
                conn.close()
                
                self.clear_dettaglio()
                self.refresh_appunti()
                messagebox.showinfo("Successo", "Appunto eliminato con successo")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nell'eliminazione: {e}")
    
    def init_telegram_bot(self):
        """Inizializza il manager del bot Telegram"""
        try:
            # Prova prima la versione semplice (solo requests)
            try:
                from scripts.telegram_bot_simple import TelegramBotManagerSimple
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
                self.telegram_bot_manager = TelegramBotManagerSimple(config_path)
                print("[INFO] Usando bot Telegram versione semplice (requests)")
                self.update_telegram_button()
                return
            except ImportError as e:
                print(f"[INFO] Versione semplice non disponibile: {e}")
            
            # Fallback: prova la versione completa (python-telegram-bot)
            try:
                import telegram
                from scripts.telegram_bot import TelegramBotManager, TELEGRAM_AVAILABLE
                
                if not TELEGRAM_AVAILABLE:
                    raise ImportError("python-telegram-bot non disponibile")
                
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
                self.telegram_bot_manager = TelegramBotManager(config_path)
                print("[INFO] Usando bot Telegram versione completa (python-telegram-bot)")
                self.update_telegram_button()
                return
            except ImportError:
                print("[WARNING] Nessuna versione del bot disponibile")
                self.telegram_bot_manager = None
                if hasattr(self, 'telegram_btn'):
                    self.telegram_btn.config(state='disabled', text="⚠️ Telegram (non disponibile)")
                return
            
        except Exception as e:
            print(f"Errore inizializzazione bot Telegram: {e}")
            import traceback
            traceback.print_exc()
            self.telegram_bot_manager = None
            if hasattr(self, 'telegram_btn'):
                self.telegram_btn.config(state='disabled', text="⚠️ Telegram (errore)")
    
    def update_telegram_button(self):
        """Aggiorna il testo e lo stato del pulsante Telegram"""
        if not hasattr(self, 'telegram_btn') or not self.telegram_btn:
            return
        
        if self.telegram_bot_manager and self.telegram_bot_manager.is_bot_running():
            self.telegram_btn.config(
                text="🟢 Telegram ON",
                bg="#4CAF50"
            )
        else:
            self.telegram_btn.config(
                text="🔴 Telegram OFF",
                bg="#f44336"
            )
    
    def toggle_telegram_bot(self):
        """Avvia o ferma il bot Telegram"""
        if not self.telegram_bot_manager:
            # Prova a reinizializzare
            try:
                self.init_telegram_bot()
                if not self.telegram_bot_manager:
                    # Verifica se il problema è l'installazione
                    try:
                        import requests
                    except ImportError:
                        messagebox.showerror(
                            "Libreria Non Installata",
                            "requests non è installato.\n\n"
                            "Per installarlo, esegui nel terminale:\n\n"
                            "pip install requests\n\n"
                            "Oppure se usi un ambiente virtuale:\n"
                            "source venv/bin/activate\n"
                            "pip install requests"
                        )
                    else:
                        messagebox.showerror(
                            "Errore",
                            "Bot Telegram non disponibile.\n\n"
                            "Errore nell'inizializzazione.\n"
                            "Controlla la console per dettagli."
                        )
                    return
            except Exception as e:
                messagebox.showerror("Errore", f"Errore nell'inizializzazione del bot: {e}")
                return
        
        try:
            if self.telegram_bot_manager.is_bot_running():
                # Ferma il bot
                self.telegram_bot_manager.stop_bot()
                messagebox.showinfo("Bot Telegram", "Bot Telegram fermato")
            else:
                # Avvia il bot
                token = self.telegram_bot_manager.get_bot_token()
                if not token:
                    messagebox.showwarning(
                        "Configurazione Richiesta",
                        "Token bot non configurato.\n\n"
                        "Aggiungi in config.ini:\n"
                        "[Telegram]\n"
                        "bot_token = IL_TUO_TOKEN_QUI\n\n"
                        "Ottieni il token da @BotFather su Telegram"
                    )
                    return
                
                if self.telegram_bot_manager.start_bot():
                    messagebox.showinfo("Bot Telegram", "Bot Telegram avviato con successo!")
                else:
                    messagebox.showerror("Errore", "Impossibile avviare il bot Telegram")
            
            self.update_telegram_button()
            
            # Aggiorna la lista appunti dopo un breve delay (per eventuali nuovi appunti)
            self.after(2000, self.refresh_appunti)
            
            # Avvia/ferma aggiornamento periodico
            if self.telegram_bot_manager.is_bot_running():
                self.start_periodic_refresh()
            else:
                self.stop_periodic_refresh()
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella gestione del bot: {e}")
    
    def start_periodic_refresh(self):
        """Avvia l'aggiornamento periodico della lista appunti"""
        self.stop_periodic_refresh()  # Ferma eventuali refresh già attivi
        if self.telegram_bot_manager and self.telegram_bot_manager.is_bot_running():
            self.refresh_timer = self.after(5000, self.periodic_refresh)  # Aggiorna ogni 5 secondi
    
    def stop_periodic_refresh(self):
        """Ferma l'aggiornamento periodico"""
        if hasattr(self, 'refresh_timer'):
            self.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def periodic_refresh(self):
        """Aggiorna periodicamente la lista appunti se il bot è attivo"""
        if self.telegram_bot_manager and self.telegram_bot_manager.is_bot_running():
            self.refresh_appunti()
            self.refresh_timer = self.after(5000, self.periodic_refresh)  # Riprogramma


class AppuntoDialog(tk.Toplevel):
    """Finestra di dialogo per creare/modificare un appunto"""
    
    def __init__(self, parent, db_path: str, appunto_id: Optional[int] = None, images_dir: str = None):
        super().__init__(parent)
        
        self.db_path = db_path
        self.appunto_id = appunto_id
        self.result = False
        self.created_appunto_id = None  # ID dell'appunto creato/modificato
        self.images_dir = images_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'appunti_images')
        
        self.title("Nuovo Appunto" if not appunto_id else "Modifica Appunto")
        self.geometry("700x650")
        self.minsize(600, 500)
        self.resizable(True, True)
        
        # Centra la finestra
        self.transient(parent)
        
        # Frame principale
        main_frame = tk.Frame(self, bg=Style.WHITE)
        main_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Frame superiore (titolo e campo titolo)
        top_frame = tk.Frame(main_frame, bg=Style.WHITE)
        top_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(
            top_frame,
            text="Titolo:",
            font=("Arial", 12, "bold"),
            bg=Style.WHITE,
            anchor='w'
        ).pack(fill='x', pady=(0, 8))
        
        self.titolo_entry = tk.Entry(top_frame, font=("Arial", 14))
        self.titolo_entry.pack(fill='x')
        
        # Frame centrale (contenuto) - con altezza limitata
        middle_frame = tk.Frame(main_frame, bg=Style.WHITE)
        middle_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Toolbar per formattazione HTML
        toolbar_frame = tk.Frame(middle_frame, bg=Style.WHITE)
        toolbar_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(
            toolbar_frame,
            text="Contenuto (HTML):",
            font=("Arial", 12, "bold"),
            bg=Style.WHITE,
            anchor='w'
        ).pack(side='left', padx=(0, 10))
        
        # Pulsanti formattazione
        tk.Button(
            toolbar_frame,
            text="B",
            command=lambda: self.wrap_selection("<b>", "</b>"),
            bg="#666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side='left', padx=2)
        
        tk.Button(
            toolbar_frame,
            text="I",
            command=lambda: self.wrap_selection("<i>", "</i>"),
            bg="#666",
            fg="white",
            font=("Arial", 10, "italic"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side='left', padx=2)
        
        tk.Button(
            toolbar_frame,
            text="U",
            command=lambda: self.wrap_selection("<u>", "</u>"),
            bg="#666",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side='left', padx=2)
        
        tk.Button(
            toolbar_frame,
            text="🖼️ Immagine",
            command=self.insert_image,
            bg="#9C27B0",
            fg="white",
            font=("Arial", 9),
            cursor="hand2",
            relief=tk.FLAT,
            padx=8,
            pady=4
        ).pack(side='left', padx=2)
        
        # Text widget con scrollbar - dentro un frame con altezza fissa
        text_container = tk.Frame(middle_frame, bg=Style.WHITE)
        text_container.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side='right', fill='y')
        
        self.contenuto_text = tk.Text(
            text_container,
            font=("Arial", 12),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            height=15  # Altezza fissa in righe
        )
        self.contenuto_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.contenuto_text.yview)
        
        # Frame inferiore (pulsanti) - sempre visibile
        buttons_frame = tk.Frame(main_frame, bg=Style.WHITE)
        buttons_frame.pack(fill='x', side='bottom')
        
        tk.Button(
            buttons_frame,
            text="Annulla",
            command=self.cancel,
            bg="#999",
            fg="white",
            font=("Arial", 11),
            cursor="hand2",
            relief=tk.FLAT,
            padx=25,
            pady=10
        ).pack(side='right', padx=(15, 0))
        
        tk.Button(
            buttons_frame,
            text="Salva",
            command=self.save,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=25,
            pady=10
        ).pack(side='right')
        
        # Carica i dati se in modalità modifica
        if appunto_id:
            self.load_appunto()
        
        # Assicurati che la finestra sia renderizzata prima di fare grab
        self.update_idletasks()
        
        # Centra la finestra sullo schermo
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Ora che la finestra è visibile, puoi fare grab
        self.grab_set()
        
        # Focus sul titolo
        self.titolo_entry.focus()
    
    def wrap_selection(self, start_tag: str, end_tag: str):
        """Avvolge il testo selezionato con i tag HTML specificati"""
        try:
            if self.contenuto_text.tag_ranges(tk.SEL):
                # C'è una selezione
                start = self.contenuto_text.index(tk.SEL_FIRST)
                end = self.contenuto_text.index(tk.SEL_LAST)
                selected_text = self.contenuto_text.get(start, end)
                self.contenuto_text.delete(start, end)
                self.contenuto_text.insert(start, f"{start_tag}{selected_text}{end_tag}")
            else:
                # Nessuna selezione, inserisci i tag alla posizione del cursore
                cursor_pos = self.contenuto_text.index(tk.INSERT)
                self.contenuto_text.insert(cursor_pos, f"{start_tag}{end_tag}")
                # Posiziona il cursore tra i tag
                self.contenuto_text.mark_set(tk.INSERT, f"{cursor_pos}+{len(start_tag)}c")
        except Exception as e:
            print(f"Errore nell'inserimento tag: {e}")
    
    def insert_image(self):
        """Inserisce un'immagine nel contenuto"""
        try:
            # Chiedi all'utente di selezionare un'immagine
            file_path = filedialog.askopenfilename(
                title="Seleziona un'immagine",
                filetypes=[
                    ("Immagini", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                    ("Tutti i file", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # Ottieni il nome del file
            filename = os.path.basename(file_path)
            
            # Crea un nome univoco per evitare conflitti
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            dest_path = os.path.join(self.images_dir, unique_filename)
            
            # Copia l'immagine nella cartella appunti_images
            shutil.copy2(file_path, dest_path)
            
            # Chiedi dimensioni opzionali
            width = simpledialog.askstring("Dimensioni Immagine", "Larghezza in pixel (lascia vuoto per dimensione originale):")
            alt_text = simpledialog.askstring("Testo Alternativo", "Testo alternativo per l'immagine (opzionale):")
            
            # Costruisci il tag immagine
            # Normalizza il percorso per file:// (cross-platform)
            if platform.system() == 'Windows':
                # Su Windows, converti backslash in forward slash per URL
                file_url = dest_path.replace('\\', '/')
                # Aggiungi file:/// (3 slash) per percorsi assoluti
                if file_url.startswith('/'):
                    file_url = f'file:///{file_url}'
                else:
                    file_url = f'file:///{file_url}'
            else:
                # Linux/Mac: usa file:// con forward slash
                file_url = f'file://{dest_path}'
            
            img_html = f'<img src="{file_url}"'
            
            if width:
                try:
                    width_int = int(width)
                    img_html += f' width="{width_int}"'
                except ValueError:
                    pass
            
            if alt_text:
                img_html += f' alt="{alt_text}"'
            else:
                img_html += f' alt="{name}"'
            
            img_html += ' />'
            
            # Inserisci il tag immagine nel contenuto
            if self.contenuto_text.tag_ranges(tk.SEL):
                # Sostituisci la selezione con l'immagine
                start = self.contenuto_text.index(tk.SEL_FIRST)
                end = self.contenuto_text.index(tk.SEL_LAST)
                self.contenuto_text.delete(start, end)
                self.contenuto_text.insert(start, img_html)
            else:
                # Inserisci alla posizione del cursore
                cursor_pos = self.contenuto_text.index(tk.INSERT)
                self.contenuto_text.insert(cursor_pos, img_html)
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nell'inserimento dell'immagine: {e}")
    
    def load_appunto(self):
        """Carica i dati dell'appunto da modificare"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT titolo, contenuto
                FROM appunti
                WHERE id = ?
            """, (self.appunto_id,))
            
            appunto = cursor.fetchone()
            conn.close()
            
            if appunto:
                titolo, contenuto = appunto
                self.titolo_entry.insert(0, titolo)
                self.contenuto_text.insert('1.0', contenuto or "")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")
    
    def save(self):
        """Salva l'appunto"""
        titolo = self.titolo_entry.get().strip()
        contenuto = self.contenuto_text.get('1.0', tk.END).strip()
        
        if not titolo:
            messagebox.showwarning("Attenzione", "Inserisci un titolo")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.appunto_id:
                # Modifica
                cursor.execute("""
                    UPDATE appunti
                    SET titolo = ?, contenuto = ?, data_modifica = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (titolo, contenuto, self.appunto_id))
                self.created_appunto_id = self.appunto_id
            else:
                # Nuovo - ottieni l'ID dell'appunto appena creato
                cursor.execute("""
                    INSERT INTO appunti (titolo, contenuto)
                    VALUES (?, ?)
                """, (titolo, contenuto))
                self.created_appunto_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")
    
    def cancel(self):
        """Annulla e chiude la finestra"""
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Appunti - Test")
    root.geometry("1200x700")
    AppuntiPage(root).pack(fill='both', expand=True)
    root.mainloop()
