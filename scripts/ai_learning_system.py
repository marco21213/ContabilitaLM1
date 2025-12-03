"""
Sistema di apprendimento incrementale per migliorare i match AI.
Salva e utilizza le associazioni verificate dall'utente.
"""
import os
import sys
from typing import Optional, Dict, List
from datetime import datetime

# Aggiungi il percorso per importare db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from db_manager import get_connection


class AILearningSystem:
    """Sistema di apprendimento incrementale per migliorare i match."""
    
    def __init__(self):
        self.conn = get_connection()
    
    def save_verified_association(
        self,
        descrizione_fattura: str,
        descrizione_listino: str,
        listino_id: int,
        verifica_utente: bool,
        confidence_originale: Optional[float] = None,
        codice_articolo_listino: Optional[str] = None
    ) -> bool:
        """
        Salva un'associazione verificata dall'utente.
        
        Args:
            descrizione_fattura: Descrizione dalla fattura
            descrizione_listino: Descrizione dal listino
            listino_id: ID del listino
            verifica_utente: True se match corretto, False se errato
            confidence_originale: Confidence del match AI originale
            codice_articolo_listino: Codice articolo dal listino
            
        Returns:
            True se salvato con successo
        """
        cursor = self.conn.cursor()
        
        try:
            # Usa INSERT OR REPLACE per gestire duplicati
            cursor.execute("""
                INSERT OR REPLACE INTO associazioni_verificate
                (descrizione_fattura, codice_articolo_listino, descrizione_listino, listino_id,
                 verifica_utente, data_verifica, confidence_originale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                descrizione_fattura.strip(),
                codice_articolo_listino,
                descrizione_listino.strip(),
                listino_id,
                1 if verifica_utente else 0,
                datetime.now().date(),
                confidence_originale
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Errore nel salvataggio associazione: {e}")
            self.conn.rollback()
            return False
    
    def get_verified_associations(
        self,
        descrizione_fattura: Optional[str] = None,
        listino_id: Optional[int] = None,
        only_correct: bool = True
    ) -> List[Dict]:
        """
        Ottiene le associazioni verificate.
        
        Args:
            descrizione_fattura: Filtra per descrizione fattura (opzionale)
            listino_id: Filtra per listino (opzionale)
            only_correct: Se True, solo associazioni corrette
            
        Returns:
            Lista di associazioni verificate
        """
        cursor = self.conn.cursor()
        
        sql = "SELECT * FROM associazioni_verificate WHERE 1=1"
        params = []
        
        if descrizione_fattura:
            sql += " AND descrizione_fattura = ?"
            params.append(descrizione_fattura)
        
        if listino_id:
            sql += " AND listino_id = ?"
            params.append(listino_id)
        
        if only_correct:
            sql += " AND verifica_utente = 1"
        
        sql += " ORDER BY data_verifica DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def delete_association(self, association_id: int) -> bool:
        """
        Elimina un'associazione verificata.
        
        Args:
            association_id: ID dell'associazione da eliminare
            
        Returns:
            True se eliminata con successo
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("DELETE FROM associazioni_verificate WHERE id = ?", (association_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Errore nell'eliminazione associazione: {e}")
            self.conn.rollback()
            return False
    
    def get_statistics(self) -> Dict:
        """
        Ottiene statistiche sul sistema di apprendimento.
        
        Returns:
            Dizionario con statistiche
        """
        cursor = self.conn.cursor()
        
        # Totale associazioni
        cursor.execute("SELECT COUNT(*) as total FROM associazioni_verificate")
        total = cursor.fetchone()['total']
        
        # Associazioni corrette
        cursor.execute("""
            SELECT COUNT(*) as correct 
            FROM associazioni_verificate 
            WHERE verifica_utente = 1
        """)
        correct = cursor.fetchone()['correct']
        
        # Associazioni errate
        cursor.execute("""
            SELECT COUNT(*) as wrong 
            FROM associazioni_verificate 
            WHERE verifica_utente = 0
        """)
        wrong = cursor.fetchone()['wrong']
        
        # Media confidence originale
        cursor.execute("""
            SELECT AVG(confidence_originale) as avg_confidence
            FROM associazioni_verificate
            WHERE confidence_originale IS NOT NULL
        """)
        avg_confidence_result = cursor.fetchone()
        avg_confidence = avg_confidence_result['avg_confidence'] if avg_confidence_result['avg_confidence'] else 0.0
        
        # Associazioni per listino
        cursor.execute("""
            SELECT l.nome, COUNT(*) as count
            FROM associazioni_verificate av
            JOIN listini l ON l.id = av.listino_id
            WHERE av.verifica_utente = 1
            GROUP BY l.id, l.nome
            ORDER BY count DESC
        """)
        by_listino = [dict(row) for row in cursor.fetchall()]
        
        return {
            'total': total,
            'correct': correct,
            'wrong': wrong,
            'accuracy_rate': (correct / total * 100) if total > 0 else 0.0,
            'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
            'by_listino': by_listino
        }
    
    def clear_cache_for_description(self, descrizione: str):
        """
        Pulisce la cache per una descrizione (da chiamare dopo aggiornamenti).
        Questo è un placeholder - la cache è gestita in ai_price_matcher.
        """
        # La cache è gestita in AIPriceMatcher, questo è solo un placeholder
        pass
    
    def close(self):
        """Chiude la connessione al database."""
        if self.conn:
            self.conn.close()

