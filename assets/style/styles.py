# File: assets/style/styles.py

class Style:
    # Colori
    BACKGROUND_COLOR = "#cfe3ee"
    WHITE = "#ffffff"
    MENU_HEADER_BG = "#2B579A"
    MENU_HEADER_FG = "#ffffff"
    
    # Dimensioni
    WINDOW_PADDING = 20
    CONTENT_PADDING = 15
    SECTIONS_SPACING = 5
    LOGO_SIZE = (180, 60)  # Logo più largo ma meno alto
    TOP_BAR_HEIGHT = 65    # Altezza ridotta della barra superiore
    ICON_SIZE = (35, 35)   # Icone leggermente più piccole per proporzionarle al nuovo logo
    
    # Font
    HEADER_FONT = ("Arial", 12, "bold")
    MENU_ITEM_FONT = ("Arial", 11)
    
    # Bordi e forme
    BORDER_RADIUS = 15
    
    # Configurazioni dei widget
    FRAME_CONFIG = {
        'bg': WHITE,
        'relief': 'flat',
        'padx': CONTENT_PADDING,
        'pady': CONTENT_PADDING
    }
    
    MENU_HEADER_CONFIG = {
        'bg': MENU_HEADER_BG,
        'fg': MENU_HEADER_FG,
        'font': HEADER_FONT,
        'pady': 10
    }
    
    MENU_BUTTON_CONFIG = {
        'bg': WHITE,
        'fg': '#000000',
        'font': MENU_ITEM_FONT,
        'relief': 'flat',
        'anchor': 'w',
        'pady': 5
    }
