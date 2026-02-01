"""
Bot Telegram semplificato usando solo requests (senza python-telegram-bot).
Più leggero e facile da installare su Linux.
"""
import os
import sys
import sqlite3
import threading
import logging
import time
import json
from datetime import datetime
from typing import Optional

# Aggiungi il percorso per importare i moduli
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WARNING] requests non disponibile. Installa con: pip install requests")

from parametri_db import get_db_path
from config_loader import load_config


class TelegramBotManagerSimple:
    """Gestisce il bot Telegram usando solo requests (polling manuale)"""
    
    def __init__(self, config_path: Optional[str] = None):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests non disponibile. Installa con: pip install requests")
        
        self.config_path = config_path or os.path.join(os.path.dirname(current_dir), 'config.ini')
        self.config = load_config()
        self.db_path = get_db_path(self.config_path)
        self.bot_token = None
        self.api_url = None
        self.last_update_id = 0
        self.polling_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Ottieni il token
        self.bot_token = self.get_bot_token()
        if self.bot_token:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def get_bot_token(self) -> Optional[str]:
        """Ottiene il token del bot da config.ini"""
        try:
            if 'Telegram' in self.config and 'bot_token' in self.config['Telegram']:
                token = self.config.get('Telegram', 'bot_token')
                return token if token and token.strip() else None
        except Exception as e:
            self.logger.error(f"Errore lettura token bot: {e}")
        return None
    
    def save_appunto_from_telegram(self, message_text: str, user_id: int, username: str = None) -> bool:
        """Salva un appunto ricevuto da Telegram nel database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crea un titolo dal messaggio (prima riga o primi 50 caratteri)
            lines = message_text.strip().split('\n')
            if lines:
                titolo = lines[0][:50] if len(lines[0]) <= 50 else lines[0][:47] + "..."
            else:
                titolo = f"Appunto Telegram {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            # Aggiungi informazioni sul mittente nel contenuto
            user_info = f"<p><small>Ricevuto da Telegram - Utente: {username or f'ID {user_id}'}</small></p>"
            contenuto = f"{user_info}<div>{message_text}</div>"
            
            # Inserisci nel database
            cursor.execute("""
                INSERT INTO appunti (titolo, contenuto)
                VALUES (?, ?)
            """, (titolo, contenuto))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Appunto salvato da Telegram: {titolo}")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore salvataggio appunto da Telegram: {e}")
            return False
    
    def send_message(self, chat_id: int, text: str) -> bool:
        """Invia un messaggio tramite l'API Telegram"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Errore invio messaggio: {e}")
            return False
    
    def process_update(self, update: dict):
        """Processa un update ricevuto da Telegram"""
        try:
            message = update.get('message', {})
            if not message:
                return
            
            chat_id = message.get('chat', {}).get('id')
            user = message.get('from', {})
            user_id = user.get('id')
            username = user.get('username') or user.get('first_name', 'Sconosciuto')
            text = message.get('text', '')
            
            # Gestisci comandi
            if text.startswith('/'):
                command = text.split()[0] if text else ''
                
                if command == '/start':
                    self.send_message(chat_id, 
                        "🤖 Bot Appunti Attivo!\n\n"
                        "Invia un messaggio e verrà salvato come appunto.\n"
                        "Usa /help per vedere i comandi disponibili."
                    )
                elif command == '/help':
                    self.send_message(chat_id,
                        "📝 Comandi disponibili:\n\n"
                        "/start - Avvia il bot\n"
                        "/help - Mostra questo messaggio\n"
                        "/status - Verifica lo stato del bot\n\n"
                        "Invia qualsiasi messaggio per salvarlo come appunto."
                    )
                elif command == '/status':
                    self.send_message(chat_id, "✅ Bot attivo e funzionante!")
                return
            
            # Salva il messaggio come appunto
            if text:
                if self.save_appunto_from_telegram(text, user_id, username):
                    self.send_message(chat_id, "✅ Appunto salvato con successo!")
                else:
                    self.send_message(chat_id, "❌ Errore nel salvataggio dell'appunto.")
            
        except Exception as e:
            self.logger.error(f"Errore processamento update: {e}")
    
    def polling_loop(self):
        """Loop principale per il polling degli aggiornamenti"""
        while self.is_running:
            try:
                url = f"{self.api_url}/getUpdates"
                params = {
                    "offset": self.last_update_id + 1,
                    "timeout": 30
                }
                
                response = requests.get(url, params=params, timeout=35)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        updates = data.get('result', [])
                        for update in updates:
                            update_id = update.get('update_id')
                            if update_id:
                                self.last_update_id = max(self.last_update_id, update_id)
                            self.process_update(update)
                else:
                    self.logger.warning(f"Errore API Telegram: {response.status_code}")
                    time.sleep(5)  # Attendi prima di riprovare
                    
            except requests.exceptions.Timeout:
                # Timeout normale durante il long polling
                continue
            except Exception as e:
                self.logger.error(f"Errore nel polling: {e}")
                time.sleep(5)  # Attendi prima di riprovare
    
    def start_bot(self) -> bool:
        """Avvia il bot Telegram in un thread separato"""
        if self.is_running:
            return False
        
        if not self.bot_token:
            self.logger.error("Token bot non configurato in config.ini")
            return False
        
        if not REQUESTS_AVAILABLE:
            self.logger.error("requests non disponibile")
            return False
        
        # Verifica che il bot sia valido
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Token bot non valido: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Errore verifica bot: {e}")
            return False
        
        self.is_running = True
        self.polling_thread = threading.Thread(target=self.polling_loop, daemon=True)
        self.polling_thread.start()
        
        self.logger.info("Bot Telegram avviato (versione semplice)")
        return True
    
    def stop_bot(self):
        """Ferma il bot Telegram"""
        if self.is_running:
            self.is_running = False
            self.logger.info("Bot Telegram fermato")
    
    def is_bot_running(self) -> bool:
        """Verifica se il bot è in esecuzione"""
        return self.is_running and self.polling_thread and self.polling_thread.is_alive()


if __name__ == "__main__":
    # Test del bot
    logging.basicConfig(level=logging.INFO)
    
    manager = TelegramBotManagerSimple()
    token = manager.get_bot_token()
    
    if not token:
        print("Token bot non configurato. Aggiungi in config.ini:")
        print("[Telegram]")
        print("bot_token = IL_TUO_TOKEN_QUI")
    else:
        print(f"Token trovato: {token[:10]}...")
        print("Avvio bot...")
        if manager.start_bot():
            print("Bot avviato. Premi Ctrl+C per fermare.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop_bot()
                print("Bot fermato.")
