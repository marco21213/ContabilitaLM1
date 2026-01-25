"""
Script per inizializzare tutte le tabelle del database all'avvio dell'applicazione.
Garantisce che tutte le tabelle necessarie siano create automaticamente.
"""
import os
import sys

# Aggiungi il percorso per importare i moduli
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def init_all_database_tables():
    """Inizializza tutte le tabelle del database necessarie per l'applicazione"""
    try:
        # Inizializza tabella appunti
        try:
            from init_appunti_database import init_appunti_tables
            init_appunti_tables()
        except Exception as e:
            print(f"[WARNING] Errore inizializzazione tabelle appunti: {e}")
        
        # Inizializza tabelle laboratorio (se necessario)
        try:
            from init_laboratorio_database import init_laboratorio_tables
            init_laboratorio_tables()
        except Exception as e:
            print(f"[WARNING] Errore inizializzazione tabelle laboratorio: {e}")
        
        # Inizializza tabelle AI (se necessario)
        try:
            from init_ai_database import init_ai_tables
            init_ai_tables()
        except Exception as e:
            print(f"[WARNING] Errore inizializzazione tabelle AI: {e}")
        
        print("[INFO] Inizializzazione tabelle database completata")
        return True
        
    except Exception as e:
        print(f"[ERROR] Errore durante l'inizializzazione delle tabelle: {e}")
        return False


if __name__ == "__main__":
    print("Inizializzazione di tutte le tabelle del database...")
    init_all_database_tables()
    print("Completato!")
