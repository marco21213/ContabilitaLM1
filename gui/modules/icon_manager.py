from PIL import Image, ImageTk
import os

class IconManager:
    def __init__(self, icon_size=(48, 48), icon_color="#1f396a"):
        self.icon_size = icon_size
        self.icon_color = icon_color
    
    def load_icon(self, icon_name):
        """Carica e ridimensiona un'icona."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(current_dir))
        icon_path = os.path.join(project_dir, 'assets', 'icon', icon_name)
        
        if not os.path.exists(icon_path):
            raise FileNotFoundError(f"Icona non trovata: {icon_path}")
        
        image = Image.open(icon_path)
        image = image.resize(self.icon_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    
    def darken_color(self, color):
        """Scura un colore hex."""
        if color.startswith('#'):
            r = max(0, int(color[1:3], 16) - 30)
            g = max(0, int(color[3:5], 16) - 30)
            b = max(0, int(color[5:7], 16) - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color