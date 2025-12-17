"""
Modulo per gestire lo storico dei download rapidi.
Mantiene gli ultimi 10 download in un file JSON.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class DownloadHistory:
    """Gestisce lo storico dei download rapidi."""
    
    def __init__(self, history_file: str = "download_history.json"):
        """
        Inizializza il gestore dello storico.
        
        Args:
            history_file: Percorso del file JSON per lo storico
        """
        self.history_file = history_file
        self.max_downloads = 10
    
    def load_history(self) -> List[Dict]:
        """
        Carica lo storico dal file JSON.
        
        Returns:
            Lista dei download salvati
        """
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('downloads', [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Errore nel caricamento dello storico: {e}")
            return []
    
    def save_history(self, downloads: List[Dict]) -> bool:
        """
        Salva lo storico nel file JSON.
        
        Args:
            downloads: Lista dei download da salvare
            
        Returns:
            True se salvato con successo, False altrimenti
        """
        try:
            data = {
                'downloads': downloads,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except IOError as e:
            print(f"Errore nel salvataggio dello storico: {e}")
            return False
    
    def add_download(self, fatture: List[Dict]) -> bool:
        """
        Aggiunge un nuovo download allo storico.
        
        Args:
            fatture: Lista di dizionari con i dati delle fatture scaricate.
                    Ogni dizionario deve contenere: numero, soggetto, data
        
        Returns:
            True se salvato con successo, False altrimenti
        """
        # Carica lo storico esistente
        downloads = self.load_history()
        
        # Crea il nuovo record
        now = datetime.now()
        new_download = {
            'data': now.strftime('%Y-%m-%d'),
            'ora': now.strftime('%H:%M:%S'),
            'fatture': fatture
        }
        
        # Aggiungi all'inizio della lista (più recente prima)
        downloads.insert(0, new_download)
        
        # Mantieni solo gli ultimi N download
        downloads = downloads[:self.max_downloads]
        
        # Salva lo storico aggiornato
        return self.save_history(downloads)
    
    def get_recent_downloads(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Ottiene i download più recenti.
        
        Args:
            limit: Numero massimo di download da restituire (None = tutti)
        
        Returns:
            Lista dei download più recenti
        """
        downloads = self.load_history()
        if limit:
            return downloads[:limit]
        return downloads
    
    def clear_history(self) -> bool:
        """
        Cancella tutto lo storico.
        
        Returns:
            True se cancellato con successo, False altrimenti
        """
        return self.save_history([])


if __name__ == "__main__":
    # Test del modulo
    history = DownloadHistory("test_history.json")
    
    # Test aggiunta download
    test_fatture = [
        {'numero': '123', 'soggetto': 'Fornitore Test', 'data': '15/01/2024'},
        {'numero': '124', 'soggetto': 'Altro Fornitore', 'data': '15/01/2024'}
    ]
    
    history.add_download(test_fatture)
    
    # Test lettura
    recent = history.get_recent_downloads()
    print(f"Download salvati: {len(recent)}")
    for download in recent:
        print(f"  {download['data']} {download['ora']}: {len(download['fatture'])} fatture")
    
    # Pulisci il file di test
    os.remove("test_history.json")

