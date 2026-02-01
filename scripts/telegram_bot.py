"""
Bot Telegram per ricevere appunti e salvarli nel database.
"""
import os
import sys
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Optional

# Aggiungi il percorso per importare i moduli
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from parametri_db import get_db_path
from config_loader import load_config

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Crea classi stub per evitare errori
    Update = None
    ContextTypes = type('ContextTypes', (), {'DEFAULT_TYPE': None})()
    Application = None
    CommandHandler = None
    MessageHandler = None
    filters = type('filters', (), {})()
    print("[WARNING] python-telegram-bot non disponibile. Installa con: pip install python-telegram-bot")


class TelegramBotManager:
    """Gestisce il bot Telegram per ricevere appunti"""
    
    def __init__(self, config_path: Optional[str] = None):
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot non disponibile. Installa con: pip install python-telegram-bot==21.0.1")
        
        self.config_path = config_path or os.path.join(os.path.dirname(current_dir), 'config.ini')
        self.config = load_config()
        self.db_path = get_db_path(self.config_path)
        self.application = None
        self.bot_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /start"""
        await update.message.reply_text(
            "🤖 Bot Appunti Attivo!\n\n"
            "Invia un messaggio e verrà salvato come appunto.\n"
            "Usa /help per vedere i comandi disponibili."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /help"""
        await update.message.reply_text(
            "📝 Comandi disponibili:\n\n"
            "/start - Avvia il bot\n"
            "/help - Mostra questo messaggio\n"
            "/status - Verifica lo stato del bot\n\n"
            "Invia qualsiasi messaggio per salvarlo come appunto."
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /status"""
        await update.message.reply_text("✅ Bot attivo e funzionante!")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i messaggi ricevuti"""
        if not update.message or not update.message.text:
            return
        
        message_text = update.message.text
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name
        
        # Salva l'appunto
        if self.save_appunto_from_telegram(message_text, user_id, username):
            await update.message.reply_text("✅ Appunto salvato con successo!")
        else:
            await update.message.reply_text("❌ Errore nel salvataggio dell'appunto.")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce le foto ricevute"""
        if not update.message or not update.message.photo:
            return
        
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name
        caption = update.message.caption or "Immagine da Telegram"
        
        # Per ora salviamo solo la caption, le immagini potrebbero essere scaricate in futuro
        if self.save_appunto_from_telegram(caption, user_id, username):
            await update.message.reply_text("✅ Appunto con immagine salvato!")
        else:
            await update.message.reply_text("❌ Errore nel salvataggio.")
    
    def start_bot(self) -> bool:
        """Avvia il bot Telegram in un thread separato"""
        if self.is_running:
            return False
        
        token = self.get_bot_token()
        if not token:
            self.logger.error("Token bot non configurato in config.ini")
            return False
        
        if not TELEGRAM_AVAILABLE:
            self.logger.error("python-telegram-bot non disponibile")
            return False
        
        def run_bot():
            try:
                # Crea l'applicazione
                self.application = Application.builder().token(token).build()
                
                # Aggiungi handlers
                self.application.add_handler(CommandHandler("start", self.start_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.add_handler(CommandHandler("status", self.status_command))
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
                
                # Avvia il bot
                self.is_running = True
                self.logger.info("Bot Telegram avviato")
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
                
            except Exception as e:
                self.logger.error(f"Errore nel bot Telegram: {e}")
                self.is_running = False
        
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        
        return True
    
    def stop_bot(self):
        """Ferma il bot Telegram"""
        if self.application and self.is_running:
            try:
                self.application.stop()
                self.is_running = False
                self.logger.info("Bot Telegram fermato")
            except Exception as e:
                self.logger.error(f"Errore nella chiusura del bot: {e}")
    
    def is_bot_running(self) -> bool:
        """Verifica se il bot è in esecuzione"""
        return self.is_running


if __name__ == "__main__":
    # Test del bot
    logging.basicConfig(level=logging.INFO)
    
    manager = TelegramBotManager()
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
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop_bot()
                print("Bot fermato.")
