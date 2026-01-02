import tkinter as tk
from tkinter import ttk

class TopBar:
    def __init__(self, parent, icon_manager, commands_dict):
        self.parent = parent
        self.icon_manager = icon_manager
        self.commands = commands_dict
        self.create_top_bar()
    
    def create_top_bar(self):
        top_bar_frame = tk.Frame(self.parent, bg=self.parent.cget('bg'), height=70)
        top_bar_frame.pack(side="top", fill="x", pady=(0, 10))
        top_bar_frame.pack_propagate(False)
        
        icons_container = tk.Frame(top_bar_frame, bg=self.parent.cget('bg'))
        icons_container.pack(side="left", padx=20)
        
        icons_config = []
        
        # Aggiungi i bottoni download solo se i comandi sono disponibili
        if 'fast_download' in self.commands:
            icons_config.append({
                'icon': 'icon-download1.png',
                'text': 'Download Rapido Acquisti',
                'command': self.commands['fast_download']
            })
        if 'select_period' in self.commands:
            icons_config.append({
                'icon': 'icon-download2.png',
                'text': 'Download Periodo',
                'command': self.commands['select_period']
            })
        if 'monthly_purchases' in self.commands:
            icons_config.append({
                'icon': 'icon-download3.png',
                'text': 'Download Mensile Acquisti',
                'command': self.commands['monthly_purchases']
            })
        if 'monthly_sales' in self.commands:
            icons_config.append({
                'icon': 'icon-download4.png',
                'text': 'Download Mensile Vendite',
                'command': self.commands['monthly_sales']
            })
        
        # Aggiungi il bottone Cronologia se il comando è disponibile
        if 'show_history' in self.commands:
            icons_config.append({
                'icon': 'cronologia.png',
                'text': 'Cronologia',
                'command': self.commands['show_history']
            })
        
        # Aggiungi il bottone Info se il comando è disponibile
        if 'show_info' in self.commands:
            icons_config.append({
                'icon': 'info.png',
                'text': 'Info',
                'command': self.commands['show_info']
            })
        
        for config in icons_config:
            self.create_icon_button(icons_container, config)
    
    def create_icon_button(self, parent, config):
        try:
            icon_img = self.icon_manager.load_icon(config['icon'])
            btn_frame = tk.Frame(parent, bg=self.parent.cget('bg'))
            btn_frame.pack(side="left", padx=15)
            
            btn = tk.Button(btn_frame, image=icon_img, bd=0, bg=self.parent.cget('bg'),
                          activebackground=self.parent.cget('bg'), cursor="hand2",
                          command=config['command'])
            btn.image = icon_img
            btn.pack()
            
            label = tk.Label(btn_frame, text=config['text'], font=("Arial", 9, "bold"), 
                           bg=self.parent.cget('bg'), fg=self.icon_manager.icon_color)
            label.pack(pady=(3, 0))
            
        except FileNotFoundError:
            # Fallback per icone mancanti
            btn_frame = tk.Frame(parent, bg=self.parent.cget('bg'))
            btn_frame.pack(side="left", padx=15)
            
            btn = tk.Button(btn_frame, text=config['text'], font=("Arial", 9, "bold"),
                          bg="blue", fg="white", cursor="hand2",
                          command=config['command'], padx=5, pady=2)
            btn.pack()

class DataTable:
    def __init__(self, parent):
        self.parent = parent
        self.create_table()
    
    def create_table(self):
        # Implementazione della tabella dati
        pass

class HtmlViewer:
    def __init__(self, parent):
        self.parent = parent
        self.create_viewer()
    
    def create_viewer(self):
        # Implementazione del visualizzatore HTML
        pass