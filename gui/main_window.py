import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import sys
import logging
from typing import Dict, Any, Optional, Callable

# Aggiungi la directory radice del progetto al path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
       sys.path.insert(0, PROJECT_ROOT)
   
from assets.style.styles import Style

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Aggiunta del metodo per disegnare rettangoli arrotondati
tk.Canvas.create_rounded_rectangle = lambda self, x1, y1, x2, y2, radius=25, **kwargs: \
    self.create_polygon(
        x1+radius, y1,
        x2-radius, y1,
        x2, y1,
        x2, y1+radius,
        x2, y2-radius,
        x2, y2,
        x2-radius, y2,
        x1+radius, y2,
        x1, y2,
        x1, y2-radius,
        x1, y1+radius,
        x1, y1,
        smooth=True,
        **kwargs
    )


class IconButton:
    """Classe per gestire i pulsanti delle icone in modo più pulito"""
    def __init__(self, parent, icon_path: str, size: tuple, command: Callable, bg_color: str):
        self.parent = parent
        self.icon_path = icon_path
        self.size = size
        self.command = command
        self.bg_color = bg_color
        
    def create(self) -> Optional[tk.Button]:
        try:
            icon_img = Image.open(self.icon_path).resize(self.size)
            icon_photo = ImageTk.PhotoImage(icon_img)
            button = tk.Button(
                self.parent,
                image=icon_photo,
                bg=self.bg_color,
                bd=0,
                activebackground=self.bg_color,
                command=self.command
            )
            button.image = icon_photo
            return button
        except Exception as e:
            logger.error(f"Errore nel caricamento dell'icona {self.icon_path}: {e}")
            return None


class RoundedFrame(tk.Frame):
    """Frame personalizzato con angoli arrotondati migliorato"""
    def __init__(self, master, radius: int = Style.BORDER_RADIUS, 
                 bg: str = Style.WHITE, **kwargs):
        super().__init__(master, **kwargs)
        self.radius = radius
        self.bg = bg
        
        self.canvas = tk.Canvas(
            self,
            bg=Style.BACKGROUND_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        self.inner_frame = tk.Frame(self.canvas, bg=self.bg)
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, event):
        self.canvas.delete('all')
        width, height = event.width, event.height
        
        # Crea rettangolo arrotondato
        self.canvas.create_rounded_rectangle(
            2, 2, width-2, height-2,
            radius=self.radius,
            fill=self.bg,
            outline=getattr(Style, 'BORDER_COLOR', 'lightgray'),
            width=1
        )
        
        # Posiziona il frame interno
        self.canvas.create_window(
            width//2, height//2,
            window=self.inner_frame,
            width=width-Style.CONTENT_PADDING*2,
            height=height-Style.CONTENT_PADDING*2
        )


class MainWindow:
    """Finestra principale dell'applicazione Contabilità 3B"""
    
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Contabilità 3B")
        self.root.configure(bg=Style.BACKGROUND_COLOR)
        
        # Imposta dimensioni responsive
        self.root.state('zoomed')
        self.root.minsize(1024, 768)
        
        self.current_page: Optional[tk.Widget] = None
        
        self.main_frame = tk.Frame(
            self.root,
            bg=Style.BACKGROUND_COLOR,
            padx=Style.WINDOW_PADDING,
            pady=Style.WINDOW_PADDING
        )
        self.main_frame.pack(fill='both', expand=True)

        self.create_top_bar()
        self.content_frame = tk.Frame(
            self.main_frame, 
            bg=Style.BACKGROUND_COLOR, 
            pady=Style.SECTIONS_SPACING
        )
        self.content_frame.pack(fill='both', expand=True)

        self.create_main_containers()

    def create_top_bar(self) -> None:
        top_bar = tk.Frame(
            self.main_frame, 
            bg=Style.BACKGROUND_COLOR, 
            height=Style.TOP_BAR_HEIGHT
        )
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)

        top_content = tk.Frame(top_bar, bg=Style.BACKGROUND_COLOR)
        top_content.pack(fill='both', expand=True)

        # Logo
        try:
            logo_img = Image.open("assets/icon/logo.png").resize(Style.LOGO_SIZE)
            logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(top_content, image=logo_photo, bg=Style.BACKGROUND_COLOR)
            logo_label.image = logo_photo
            logo_label.pack(side='left')
        except Exception as e:
            logger.error(f"Errore nel caricamento del logo: {e}")
            tk.Label(
                top_content, 
                text="Pando3B", 
                font=("Arial", 20), 
                bg=Style.BACKGROUND_COLOR
            ).pack(side='left')

        # Icone destra
        icons_frame = tk.Frame(top_content, bg=Style.BACKGROUND_COLOR)
        icons_frame.pack(side='right', pady=(Style.TOP_BAR_HEIGHT - Style.ICON_SIZE[1])//2)

        # Icona Home
        home_icon = IconButton(
            icons_frame, 
            "assets/icon/icon1.png", 
            Style.ICON_SIZE, 
            lambda: self.show_page("Home"), 
            Style.BACKGROUND_COLOR
        )
        if home_button := home_icon.create():
            home_button.pack(side='left', padx=5)

        # Icona Configurazione
        config_icon = IconButton(
            icons_frame, 
            "assets/icon/icon2.png", 
            Style.ICON_SIZE, 
            self.open_config_window, 
            Style.BACKGROUND_COLOR
        )
        if config_button := config_icon.create():
            config_button.pack(side='left', padx=5)

        # Icona Utenti
        users_icon = IconButton(
            icons_frame, 
            "assets/icon/icon3.png", 
            Style.ICON_SIZE, 
            self.open_users_window, 
            Style.BACKGROUND_COLOR
        )
        if users_button := users_icon.create():
            users_button.pack(side='left', padx=5)

    def create_main_containers(self) -> None:
        self.side_menu_container = RoundedFrame(
            self.content_frame, 
            bg=Style.BACKGROUND_COLOR, 
            width=200
        )
        self.side_menu_container.pack(side='left', fill='y', padx=(0, Style.SECTIONS_SPACING))
        self.side_menu_container.pack_propagate(False)
        self.create_side_menu(self.side_menu_container.inner_frame)

        self.main_content_container = RoundedFrame(
            self.content_frame, 
            bg=Style.BACKGROUND_COLOR
        )
        self.main_content_container.pack(side='left', fill='both', expand=True)

        # Mostra la homepage all'avvio
        self.show_page("Home")

    def create_side_menu(self, parent: tk.Frame) -> None:
        # Sezione Contabilità
        tk.Label(parent, text="FATTURE", **Style.MENU_HEADER_CONFIG).pack(fill='x')
        menu_items_contabilita = ["Download", "Fatture Acquisto", "Fatture Vendita", "Verifica Ft Acquisto"]

        for item in menu_items_contabilita:
            tk.Button(
                parent,
                text=item,
                command=lambda i=item: self.show_page(i),
                **Style.MENU_BUTTON_CONFIG
            ).pack(fill='x', pady=2)

        # Sezione Laboratorio
        tk.Label(parent, text="CONTABILITA'", **Style.MENU_HEADER_CONFIG).pack(fill='x', pady=(20, 0))
        menu_items_laboratorio = ["Soggetti", "Documenti", "Pagamenti", "Libro Mastro","Dichiarazioni Intento", "Controllo Prezzi"]

        for item in menu_items_laboratorio:
            tk.Button(
                parent,
                text=item,
                command=lambda i=item: self.show_page(i),
                **Style.MENU_BUTTON_CONFIG
            ).pack(fill='x', pady=2)

    def show_page(self, page_name: str) -> None:
        """Mostra la pagina specificata"""
        for widget in self.main_content_container.inner_frame.winfo_children():
            widget.destroy()

        page_config = {
            "Home": {"module": "home_page", "class": "HomePage"},
            "Download": {"module": "download_page", "class": "DownloadPage"},
            "Fatture Acquisto": {"module": "fatture_acquisti_page", "class": "AcquistiMensiliPage"},
            "Fatture Vendita": {"module": "fatture_vendita_page", "class": "VenditeMensiliPage"},
            "Verifica Ft Acquisto": {"module": "verifica_ft_acquisto_page", "class": "VerificaFtAcquistoPage"},
            "Soggetti": {"module": "soggetti_page", "class": "SoggettiApp"},
            "Documenti": {"module": "documenti_page", "class": "VistaScadenzeApp"},
            "Pagamenti": {"module": "pagamenti_page", "class": "PagamentiUnificatiApp"},
            "Libro Mastro": {"module": "libromastro_page", "class": "LibroMastroWindow"},
            "Dichiarazioni Intento": {"module": "dichiarazioni_page", "class": "DichiarazioniIntentoPage"},
            "Controllo Prezzi": {"module": "controllo_prezzi_page", "class": "ControlloPrezziPage"},
        }

        config = page_config.get(page_name)
        if not config:
            self._show_error_page(f"Pagina non trovata: {page_name}")
            return
            
        try:
            module = __import__(config["module"], fromlist=[config["class"]])
            page_class = getattr(module, config["class"])
            self.current_page = page_class(self.main_content_container.inner_frame)
            self.current_page.pack(fill='both', expand=True)
        except ImportError as e:
            self._show_error_page(f"Modulo non trovato per {page_name}: {e}")
        except AttributeError as e:
            self._show_error_page(f"Classe non trovata per {page_name}: {e}")
        except Exception as e:
            self._show_error_page(f"Errore nel caricamento di {page_name}: {e}")

    def _show_error_page(self, message: str) -> None:
        """Mostra una pagina di errore standardizzata"""
        error_frame = tk.Frame(self.main_content_container.inner_frame, bg=Style.WHITE)
        error_frame.pack(fill='both', expand=True)
        
        tk.Label(
            error_frame,
            text="Errore",
            font=("Arial", 24),
            bg=Style.WHITE,
            fg="red"
        ).pack(pady=20)
        
        tk.Label(
            error_frame,
            text=message,
            font=("Arial", 12),
            bg=Style.WHITE,
            fg="darkred",
            wraplength=400
        ).pack(pady=10)

    def open_config_window(self) -> None:
        """Apre la finestra di configurazione"""
        try:
            from config_window import ConfigWindow
            ConfigWindow(self.root)
        except ImportError as e:
            logger.error(f"Errore nell'apertura della finestra di configurazione: {e}")
            self._show_temp_message("Errore nel caricamento della configurazione")

    def open_users_window(self) -> None:
        """Apre la finestra di gestione utenti"""
        try:
            from users_window import UsersWindow
            UsersWindow(self.root)
        except ImportError as e:
            logger.error(f"Errore nell'apertura della finestra utenti: {e}")
            self._show_temp_message("Errore nel caricamento della gestione utenti")

    def _show_temp_message(self, message: str) -> None:
        """Mostra un messaggio temporaneo"""
        temp_win = tk.Toplevel(self.root)
        temp_win.title("Info")
        temp_win.geometry("300x100")
        tk.Label(temp_win, text=message, font=("Arial", 12)).pack(expand=True)
        temp_win.after(3000, temp_win.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()