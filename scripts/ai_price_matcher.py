"""
Classe principale per il matching AI tra prodotti in fattura e listini prezzi.
Utilizza sentence-transformers per embeddings semantici.
"""
import os
import sys
from typing import List, Dict, Optional, Tuple
import numpy as np
from pathlib import Path

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from db_manager import get_connection

# Import lazy delle librerie AI per evitare errori di caricamento DLL
AI_AVAILABLE = False
_SentenceTransformer = None
_cosine_similarity = None

def _try_import_ai():
    """Tenta di importare le librerie AI. Gestisce errori di DLL su Windows."""
    global AI_AVAILABLE, _SentenceTransformer, _cosine_similarity
    
    if AI_AVAILABLE:
        return True
    
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        _SentenceTransformer = SentenceTransformer
        _cosine_similarity = cosine_similarity
        AI_AVAILABLE = True
        return True
    except ImportError as e:
        AI_AVAILABLE = False
        print(f"⚠️  Librerie AI non installate: {e}")
        print("   Installare con: pip install sentence-transformers scikit-learn torch")
        return False
    except OSError as e:
        # Errore di caricamento DLL (Windows)
        AI_AVAILABLE = False
        print(f"⚠️  Errore nel caricamento librerie AI (DLL): {e}")
        print("   Potrebbe essere necessario reinstallare PyTorch o le Visual C++ Redistributables")
        return False
    except Exception as e:
        # Altri errori (es. memoria, permessi, ecc.)
        AI_AVAILABLE = False
        print(f"⚠️  Errore nell'inizializzazione librerie AI: {e}")
        return False


class AIPriceMatcher:
    """Classe per il matching AI tra descrizioni prodotti."""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Inizializza il matcher AI.
        
        Args:
            model_name: Nome del modello sentence-transformers da usare
        """
        self.model_name = model_name
        self.model = None
        self.embedding_cache = {}  # Cache per embeddings già calcolati
        
        # Inizializza connessione database (gestisce errori)
        try:
            self.conn = get_connection()
        except Exception as e:
            print(f"⚠️  Errore nella connessione al database: {e}")
            self.conn = None
        
        # Tenta di importare le librerie AI (lazy import)
        if _try_import_ai():
            try:
                print(f"Caricamento modello AI: {model_name}...")
                self.model = _SentenceTransformer(model_name)
                print("✅ Modello caricato con successo!")
            except OSError as e:
                # Errore di caricamento DLL
                print(f"⚠️  Errore nel caricamento del modello (DLL): {e}")
                print("   Il sistema funzionerà senza AI, solo con matching testuale.")
                self.model = None
            except Exception as e:
                print(f"⚠️  Errore nel caricamento del modello: {e}")
                print("   Il sistema funzionerà senza AI, solo con matching testuale.")
                self.model = None
        else:
            print("⚠️  AI non disponibile. Usando solo matching testuale.")
            self.model = None
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Ottiene l'embedding per un testo.
        
        Args:
            text: Testo da processare
            
        Returns:
            Array numpy con l'embedding o None se AI non disponibile
        """
        if not self.model or not text:
            return None
        
        # Usa cache se disponibile
        text_key = text.lower().strip()
        if text_key in self.embedding_cache:
            return self.embedding_cache[text_key]
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            self.embedding_cache[text_key] = embedding
            return embedding
        except Exception as e:
            print(f"Errore nel calcolo embedding: {e}")
            return None
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcola la similarità semantica tra due testi.
        
        Args:
            text1: Primo testo
            text2: Secondo testo
            
        Returns:
            Score di similarità tra 0 e 1
        """
        if not self.model:
            # Fallback: similarità testuale semplice
            return self._textual_similarity(text1, text2)
        
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        if emb1 is None or emb2 is None:
            return self._textual_similarity(text1, text2)
        
        # Calcola cosine similarity
        if _cosine_similarity is None:
            return self._textual_similarity(text1, text2)
        
        try:
            similarity = _cosine_similarity([emb1], [emb2])[0][0]
            return float(similarity)
        except Exception as e:
            print(f"⚠️  Errore nel calcolo similarity: {e}")
            return self._textual_similarity(text1, text2)
    
    def _textual_similarity(self, text1: str, text2: str) -> float:
        """
        Calcola una similarità testuale semplice (fallback).
        
        Args:
            text1: Primo testo
            text2: Secondo testo
            
        Returns:
            Score di similarità tra 0 e 1
        """
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        # Se identici
        if text1_lower == text2_lower:
            return 1.0
        
        # Conta parole comuni
        words1 = set(text1_lower.split())
        words2 = set(text2_lower.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard similarity
        if union:
            return len(intersection) / len(union)
        return 0.0
    
    def find_best_match(
        self, 
        descrizione_fattura: str,
        listino_id: Optional[int] = None,
        codice_articolo: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Trova il miglior match per una descrizione fattura nel listino.
        
        Args:
            descrizione_fattura: Descrizione del prodotto dalla fattura
            listino_id: ID del listino da cercare (None = tutti i listini attivi)
            codice_articolo: Codice articolo dalla fattura (se disponibile)
            
        Returns:
            Dizionario con i dati del match o None se non trovato
        """
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        # Prima controlla se esiste un'associazione verificata
        if self._check_verified_association(descrizione_fattura, listino_id):
            verified = self._get_verified_association(descrizione_fattura, listino_id)
            if verified:
                return {
                    'riga_listino_id': verified['riga_listino_id'],
                    'descrizione_listino': verified['descrizione_listino'],
                    'prezzo_listino': verified['prezzo_listino'],
                    'codice_articolo_listino': verified.get('codice_articolo_listino'),
                    'confidence': 1.0,  # Associazione verificata = confidence massima
                    'source': 'verified'
                }
        
        # Se c'è un codice articolo, prova prima il matching esatto
        if codice_articolo:
            exact_match = self._find_by_codice_articolo(codice_articolo, listino_id)
            if exact_match:
                # Calcola anche la similarità semantica
                similarity = self.calculate_similarity(
                    descrizione_fattura,
                    exact_match['descrizione']
                )
                return {
                    'riga_listino_id': exact_match['id'],
                    'descrizione_listino': exact_match['descrizione'],
                    'prezzo_listino': exact_match['prezzo'],
                    'codice_articolo_listino': exact_match.get('codice_articolo'),
                    'confidence': max(0.9, similarity),  # Almeno 0.9 se codice corrisponde
                    'source': 'codice_articolo'
                }
        
        # Cerca nel listino
        if listino_id:
            sql = """
                SELECT id, descrizione, prezzo, codice_articolo, unita_misura
                FROM righe_listino
                WHERE listino_id = ?
            """
            params = (listino_id,)
        else:
            sql = """
                SELECT rl.id, rl.descrizione, rl.prezzo, rl.codice_articolo, rl.unita_misura
                FROM righe_listino rl
                JOIN listini l ON l.id = rl.listino_id
                WHERE l.attivo = 1
            """
            params = ()
        
        cursor.execute(sql, params)
        righe_listino = cursor.fetchall()
        
        if not righe_listino:
            return None
        
        # Calcola similarità per ogni riga
        best_match = None
        best_score = 0.0
        
        for riga in righe_listino:
            similarity = self.calculate_similarity(
                descrizione_fattura,
                riga['descrizione']
            )
            
            if similarity > best_score:
                best_score = similarity
                best_match = {
                    'riga_listino_id': riga['id'],
                    'descrizione_listino': riga['descrizione'],
                    'prezzo_listino': riga['prezzo'],
                    'codice_articolo_listino': riga.get('codice_articolo'),
                    'unita_misura': riga.get('unita_misura'),
                    'confidence': similarity,
                    'source': 'ai_semantic'
                }
        
        return best_match if best_score > 0.3 else None  # Soglia minima
    
    def _check_verified_association(
        self, 
        descrizione_fattura: str, 
        listino_id: Optional[int]
    ) -> bool:
        """Verifica se esiste un'associazione verificata."""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        
        if listino_id:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM associazioni_verificate
                WHERE descrizione_fattura = ? 
                AND listino_id = ?
                AND verifica_utente = 1
            """, (descrizione_fattura, listino_id))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM associazioni_verificate
                WHERE descrizione_fattura = ?
                AND verifica_utente = 1
            """, (descrizione_fattura,))
        
        result = cursor.fetchone()
        return result['count'] > 0 if result else False
    
    def _get_verified_association(
        self, 
        descrizione_fattura: str, 
        listino_id: Optional[int]
    ) -> Optional[Dict]:
        """Ottiene l'associazione verificata."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        if listino_id:
            cursor.execute("""
                SELECT av.descrizione_listino, av.listino_id,
                       rl.id as riga_listino_id, rl.prezzo as prezzo_listino,
                       rl.codice_articolo as codice_articolo_listino
                FROM associazioni_verificate av
                JOIN righe_listino rl ON rl.descrizione = av.descrizione_listino 
                    AND rl.listino_id = av.listino_id
                WHERE av.descrizione_fattura = ?
                AND av.listino_id = ?
                AND av.verifica_utente = 1
                ORDER BY av.data_verifica DESC
                LIMIT 1
            """, (descrizione_fattura, listino_id))
        else:
            cursor.execute("""
                SELECT av.descrizione_listino, av.listino_id,
                       rl.id as riga_listino_id, rl.prezzo as prezzo_listino,
                       rl.codice_articolo as codice_articolo_listino
                FROM associazioni_verificate av
                JOIN righe_listino rl ON rl.descrizione = av.descrizione_listino 
                    AND rl.listino_id = av.listino_id
                WHERE av.descrizione_fattura = ?
                AND av.verifica_utente = 1
                ORDER BY av.data_verifica DESC
                LIMIT 1
            """, (descrizione_fattura,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def _find_by_codice_articolo(
        self, 
        codice_articolo: str, 
        listino_id: Optional[int]
    ) -> Optional[Dict]:
        """Trova una riga listino per codice articolo."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        if listino_id:
            cursor.execute("""
                SELECT id, descrizione, prezzo, codice_articolo, unita_misura
                FROM righe_listino
                WHERE codice_articolo = ? AND listino_id = ?
            """, (codice_articolo, listino_id))
        else:
            cursor.execute("""
                SELECT rl.id, rl.descrizione, rl.prezzo, rl.codice_articolo, rl.unita_misura
                FROM righe_listino rl
                JOIN listini l ON l.id = rl.listino_id
                WHERE rl.codice_articolo = ? AND l.attivo = 1
            """, (codice_articolo,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def compare_prices(
        self, 
        prezzo_fattura: float, 
        prezzo_listino: float, 
        tolleranza_percentuale: float = 2.0
    ) -> Dict:
        """
        Confronta i prezzi e determina lo stato.
        
        Args:
            prezzo_fattura: Prezzo dalla fattura
            prezzo_listino: Prezzo dal listino
            tolleranza_percentuale: Tolleranza percentuale per differenze accettabili
            
        Returns:
            Dizionario con risultati del confronto
        """
        if prezzo_listino == 0:
            return {
                'differenza': prezzo_fattura,
                'percentuale_diff': 100.0,
                'stato': 'DA_VERIFICARE'
            }
        
        differenza = prezzo_fattura - prezzo_listino
        percentuale_diff = (differenza / prezzo_listino) * 100
        
        if abs(percentuale_diff) <= tolleranza_percentuale:
            stato = 'OK'
        elif abs(percentuale_diff) <= tolleranza_percentuale * 2:
            stato = 'DA_VERIFICARE'
        else:
            stato = 'DISCREPANZA'
        
        return {
            'differenza': differenza,
            'percentuale_diff': percentuale_diff,
            'stato': stato
        }
    
    def close(self):
        """Chiude la connessione al database."""
        if self.conn:
            self.conn.close()

