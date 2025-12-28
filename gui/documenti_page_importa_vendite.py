import sqlite3
import xml.etree.ElementTree as ET
import configparser
import os
import re
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import sys
sys.path.append("scripts")
from parametri_db import get_import_vendite, get_cartella_emesse, set_import_vendite


class ImportaFattureVenditaXML:
    def __init__(self, db_path, xml_folder, config_path, callback=None):
        self.db_path = db_path
        self.xml_folder = xml_folder
        self.config_path = config_path

        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

        self.conn = None
        self.cursor = None

        # Callback per aggiornare la GUI
        self.callback = callback

        # Statistiche
        self.fatture_elaborate = 0
        self.fatture_estere = 0
        self.file_con_errori = []
        # Dati delle fatture importate per il riepilogo
        self.fatture_importate = []
        # Fatture con dichiarazione d'intento riconosciuta
        self.fatture_con_di = []

    def log(self, messaggio, end='\n'):
        """Invia un messaggio alla GUI"""
        if self.callback:
            self.callback(messaggio, end)

    def connetti_db(self):
        """Connette al database SQLite"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def disconnetti_db(self):
        """Chiude la connessione al database"""
        if self.conn:
            self.conn.close()

    def get_prossimo_codice_soggetto(self, tipo='cliente'):
        """Ottiene il prossimo codice soggetto disponibile.
        Usa prefisso 'C' per clienti e 'F' per fornitori.
        """
        prefisso = 'C' if tipo == 'cliente' else 'F'
        self.cursor.execute(f"""
            SELECT codice_soggetto FROM soggetti
            WHERE codice_soggetto LIKE '{prefisso}%'
            ORDER BY codice_soggetto DESC LIMIT 1
        """)

        result = self.cursor.fetchone()
        if result:
            ultimo_codice = result[0]
            try:
                numero = int(ultimo_codice[1:]) + 1
            except Exception:
                numero = 1
        else:
            numero = 1

        return f"{prefisso}{numero:04d}"

    def get_tipo_documento_mapping(self, tipo_xml):
        """Ottiene la mappatura del tipo documento dal config (se presente)."""
        try:
            return self.config.get('TipoDocumento Clienti', tipo_xml).upper()
        except Exception:
            try:
                return self.config.get('TipoDocumento Fornitori', tipo_xml).upper()
            except Exception:
                return tipo_xml.upper()

    def get_segno_documento(self, tipo_xml):
        """Ottiene il segno del documento dal config"""
        try:
            return self.config.get('SegnoDocumento Clienti', tipo_xml).upper()
        except Exception:
            try:
                return self.config.get('SegnoDocumento Fornitori', tipo_xml).upper()
            except Exception:
                return '+'

    def get_tipo_pagamento(self, codice_pagamento):
        """Ottiene il tipo di pagamento dal config"""
        try:
            return self.config.get('Pagamenti', codice_pagamento).upper()
        except Exception:
            return codice_pagamento.upper()
    
    def estrai_tipo_fattura(self, root):
        """Estrae e normalizza il tipo di fattura dal XML.
        Restituisce TD01, TD24 o None se non valido.
        """
        tipo_doc_raw = self.estrai_testo(root, './/DatiGenerali/DatiGeneraliDocumento/TipoDocumento', '')
        
        if not tipo_doc_raw:
            return None
        
        # Normalizza: rimuovi spazi e converti in maiuscolo
        tipo_doc = tipo_doc_raw.strip().upper()
        
        # Se inizia con TD24 (anche con testo dopo), normalizza a TD24
        if tipo_doc.startswith('TD24'):
            return 'TD24'
        elif tipo_doc == 'TD01':
            return 'TD01'
        else:
            # Tipo documento non supportato
            return None
    
    def verifica_spese_bancarie(self, root):
        """Verifica se nell'XML sono presenti spese bancarie.
        Le spese bancarie hanno:
        - TipoCessionePrestazione = "AC"
        - Descrizione = "Spese Bancarie" (case-insensitive)
        
        Restituisce "SI" se presenti, "NO" altrimenti.
        """
        try:
            # Trova tutte le linee
            linee = root.findall(".//DettaglioLinee")
            
            for linea in linee:
                # Estrai TipoCessionePrestazione e Descrizione
                tipo_cessione = linea.findtext("TipoCessionePrestazione", "").strip()
                descrizione = linea.findtext("Descrizione", "").strip()
                
                # Verifica se è una spesa bancaria
                # TipoCessionePrestazione deve essere "AC" e Descrizione deve contenere "Spese Bancarie"
                # Controllo case-insensitive per la descrizione
                if tipo_cessione == "AC" and "spese bancarie" in descrizione.lower():
                    return "SI"
            
            return "NO"
        except Exception as e:
            # In caso di errore, restituisci "NO"
            self.log(f"  ⚠ Errore nel controllo spese bancarie: {str(e)}")
            return "NO"
    
    def get_tipo_pagamento_id(self, codice_pagamento):
        """Ottiene l'id del tipo_pagamento dalla tabella tipo_pagamento usando il codice.
        Restituisce l'id se trovato, None altrimenti.
        """
        if not codice_pagamento:
            return None
        
        try:
            query = """
                SELECT id FROM tipo_pagamento
                WHERE codice = ?
            """
            self.cursor.execute(query, (codice_pagamento.upper(),))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            # Se la tabella non esiste o c'è un errore, logga e restituisci None
            self.log(f"  ⚠ Errore nel recupero tipo_pagamento: {str(e)}")
            return None

    def estrai_testo(self, root, xpath, default=''):
        """Estrae testo da un nodo XML e converte in maiuscolo"""
        elemento = root.find(xpath)
        if elemento is not None and elemento.text:
            return elemento.text.strip().upper()
        return default.upper()

    def normalizza_numero_fattura(self, numero):
        """Normalizza il numero della fattura assicurando almeno 4 cifre numeriche.
        Esempi: '14/A' -> '0014/A', '115/A' -> '0115/A', '14' -> '0014'
        """
        if not numero:
            return numero
        
        # Trova la parte numerica all'inizio del numero
        match = re.match(r'^(\d+)(.*)$', numero)
        if match:
            parte_numerica = match.group(1)
            parte_testuale = match.group(2)
            # Pad left della parte numerica a 4 cifre
            parte_numerica_normalizzata = parte_numerica.zfill(4)
            return parte_numerica_normalizzata + parte_testuale
        # Se non c'è una parte numerica, restituisci il numero originale
        return numero

    def calcola_imponibile_totale(self, root):
        """Calcola il totale imponibile sommando tutti i DatiRiepilogo"""
        totale_imponibile = 0.0
        
        # Trova tutti i nodi ImponibileImporto
        nodi_imponibile = root.findall('.//DatiRiepilogo/ImponibileImporto')
        
        for nodo in nodi_imponibile:
            if nodo.text:
                try:
                    imponibile = float(nodo.text.strip())
                    totale_imponibile += imponibile
                except ValueError:
                    # Se c'è un errore di conversione, continua con gli altri valori
                    continue
        
        return totale_imponibile
    
    def verifica_dichiarazione_intento(self, root):
        """
        Verifica se la fattura è agganciabile a una dichiarazione d'intento.
        Cerca nei nodi DatiRiepilogo con AliquotaIVA = 0.00 e Natura che inizia con N3.
        Esclude N3.1 che non è una dichiarazione d'intento.
        
        Returns:
            True se trovata una dichiarazione d'intento, False altrimenti
        """
        try:
            # Cerca nei DatiRiepilogo
            riepiloghi = root.findall('.//DatiRiepilogo')
            
            for riepilogo in riepiloghi:
                # Estrai AliquotaIVA e Natura
                aliquota_iva_text = riepilogo.findtext('AliquotaIVA', '').strip()
                natura = riepilogo.findtext('Natura', '').strip()
                
                # Verifica se è una dichiarazione d'intento
                # Condizioni: AliquotaIVA = 0.00 e Natura inizia con N3. ma NON è N3.1
                try:
                    aliquota_iva = float(aliquota_iva_text) if aliquota_iva_text else None
                except (ValueError, TypeError):
                    continue
                
                # Verifica condizioni per dichiarazione d'intento
                # Escludi N3.1 che non è una dichiarazione d'intento
                if (aliquota_iva == 0.00 and 
                    natura and 
                    natura.upper().startswith('N3.') and 
                    natura.upper() != 'N3.1'):
                    # Trovata una dichiarazione d'intento
                    return True
            
            return False
            
        except Exception as e:
            # In caso di errore, restituisci False
            self.log(f"  ⚠ Errore verifica dichiarazione d'intento: {str(e)}")
            return False
    
    def estrai_imponibile_dichiarazione_intento(self, root):
        """
        Estrae l'imponibile dalla dichiarazione d'intento.
        Cerca nei DatiRiepilogo con AliquotaIVA = 0.00 e Natura N3.x (escluso N3.1).
        
        Returns:
            ImponibileImporto se trovato, 0.0 altrimenti
        """
        try:
            riepiloghi = root.findall('.//DatiRiepilogo')
            
            for riepilogo in riepiloghi:
                aliquota_iva_text = riepilogo.findtext('AliquotaIVA', '').strip()
                natura = riepilogo.findtext('Natura', '').strip()
                imponibile_text = riepilogo.findtext('ImponibileImporto', '').strip()
                
                try:
                    aliquota_iva = float(aliquota_iva_text) if aliquota_iva_text else None
                    imponibile = float(imponibile_text) if imponibile_text else 0.0
                except (ValueError, TypeError):
                    continue
                
                # Verifica condizioni per dichiarazione d'intento (escluso N3.1)
                if (aliquota_iva == 0.00 and 
                    natura and 
                    natura.upper().startswith('N3.') and 
                    natura.upper() != 'N3.1'):
                    return imponibile
            
            return 0.0
        except Exception as e:
            self.log(f"  ⚠ Errore estrazione imponibile DI: {str(e)}")
            return 0.0

    def verifica_soggetto_esistente(self, partita_iva, codice_fiscale):
        """Verifica se un soggetto esiste già nel database"""
        query = """
            SELECT id, tipo_soggetto FROM soggetti
            WHERE (partita_iva = ? AND partita_iva IS NOT NULL)
            OR (codice_fiscale = ? AND codice_fiscale IS NOT NULL)
        """
        self.cursor.execute(query, (partita_iva, codice_fiscale))
        result = self.cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)

    def verifica_soggetto_estero_esistente(self, ragione_sociale, citta):
        """Verifica se un cliente estero esiste già nel database basandosi su ragione_sociale e città.
        Questo controllo è necessario per clienti esteri che non hanno partita IVA o codice fiscale.
        """
        if not ragione_sociale:
            return None, None
        
        # Verifica se esiste un soggetto con stessa ragione_sociale e città, 
        # senza partita IVA (quindi estero)
        query = """
            SELECT id, tipo_soggetto FROM soggetti
            WHERE UPPER(ragione_sociale) = UPPER(?)
            AND partita_iva IS NULL
            AND (citta IS NULL OR UPPER(citta) = UPPER(?))
        """
        self.cursor.execute(query, (ragione_sociale, citta if citta else ''))
        result = self.cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)

    def aggiorna_tipo_soggetto(self, soggetto_id, nuovo_tipo):
        """Aggiorna il tipo_soggetto per gestire 'entrambi'"""
        query = """
            UPDATE soggetti 
            SET tipo_soggetto = ? 
            WHERE id = ?
        """
        self.cursor.execute(query, (nuovo_tipo.upper(), soggetto_id))

    def verifica_documento_esistente(self, soggetto_id, numero_documento):
        """Verifica se un documento esiste già"""
        query = """
            SELECT id FROM documenti
            WHERE soggetto_id = ? AND numero_documento = ?
        """
        self.cursor.execute(query, (soggetto_id, numero_documento))
        return self.cursor.fetchone() is not None

    def inserisci_soggetto(self, root):
        """Inserisce un nuovo soggetto o recupera quello esistente (cliente)."""
        id_paese = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdPaese', 'IT')

        partita_iva = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice')
        codice_fiscale = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/CodiceFiscale')

        # Se il paese è estero, impostiamo partita_iva a None per evitare duplicati
        if id_paese and id_paese != 'IT':
            partita_iva = None

        # Converti stringhe vuote in None (NULL nel database)
        partita_iva = partita_iva if partita_iva else None
        codice_fiscale = codice_fiscale if codice_fiscale else None

        # Estrai tipo_fattura e tipo_pagamento
        tipo_fattura = self.estrai_tipo_fattura(root)
        
        # Estrai modalità pagamento dal primo DettaglioPagamento
        modalita_pagamento_xml = self.estrai_testo(root, './/DatiPagamento/DettaglioPagamento/ModalitaPagamento', '')
        tipo_pagamento_id = self.get_tipo_pagamento_id(modalita_pagamento_xml) if modalita_pagamento_xml else None
        
        # Verifica presenza spese bancarie
        spese_bancarie = self.verifica_spese_bancarie(root)

        soggetto_id, tipo_soggetto_esistente = self.verifica_soggetto_esistente(partita_iva, codice_fiscale)
    
        # Se non trovato con partita IVA/codice fiscale E è un cliente estero (entrambi NULL),
        # verifica anche con ragione_sociale + città
        if not soggetto_id and partita_iva is None and codice_fiscale is None:
            # Prima recupera ragione_sociale e città per il controllo
            denominazione_temp = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione')
            if not denominazione_temp:
                cognome_temp = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Cognome')
                nome_temp = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Nome')
                denominazione_temp = f"{cognome_temp} {nome_temp}".strip()
            
            citta_temp = self.estrai_testo(root, './/CessionarioCommittente/Sede/Comune')
            citta_temp = citta_temp if citta_temp else None
            
            # Verifica se esiste già un cliente estero con stessa ragione_sociale e città
            soggetto_id, tipo_soggetto_esistente = self.verifica_soggetto_estero_esistente(denominazione_temp, citta_temp)
        
        if soggetto_id:
            # Se il soggetto esiste già, gestiamo il tipo_soggetto
            if tipo_soggetto_esistente == 'FORNITORE':
                # Se era fornitore, aggiorniamo a 'ENTRAMBI'
                self.aggiorna_tipo_soggetto(soggetto_id, 'ENTRAMBI')
                self.log(f"  Aggiornato tipo_soggetto a 'ENTRAMBI' per soggetto esistente (ID: {soggetto_id})")
            elif tipo_soggetto_esistente == 'CLIENTE':
                # Se era già cliente, non facciamo nulla
                pass
            elif tipo_soggetto_esistente == 'ENTRAMBI':
                # Se era già entrambi, non facciamo nulla
                pass
            
            # Aggiorna tipo_fattura, tipo_pagamento e spese_bancarie se disponibili
            if tipo_fattura or tipo_pagamento_id or spese_bancarie:
                self.aggiorna_tipo_fattura_pagamento(soggetto_id, tipo_fattura, tipo_pagamento_id, spese_bancarie)
            
            return soggetto_id, False

        denominazione = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione')
        if not denominazione:
            cognome = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Cognome')
            nome = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/Anagrafica/Nome')
            denominazione = f"{cognome} {nome}".strip()

        citta = self.estrai_testo(root, './/CessionarioCommittente/Sede/Comune')
        cap = self.estrai_testo(root, './/CessionarioCommittente/Sede/CAP')
        provincia = self.estrai_testo(root, './/CessionarioCommittente/Sede/Provincia')
        email = self.estrai_testo(root, './/CessionarioCommittente/Contatti/Email')

        # Converti stringhe vuote in None anche per gli altri campi
        citta = citta if citta else None
        cap = cap if cap else None
        provincia = provincia if provincia else None
        email = email if email else None

        codice_soggetto = self.get_prossimo_codice_soggetto(tipo='cliente')

        # Costruisci la query INSERT includendo tipo_fattura, tipo_pagamento e spese_bancarie
        # Verifica se le colonne esistono nella tabella
        try:
            self.cursor.execute("PRAGMA table_info(soggetti)")
            colonne = [col[1] for col in self.cursor.fetchall()]
            has_tipo_fattura = 'tipo_fattura' in colonne
            has_tipo_pagamento = 'tipo_pagamento' in colonne
            has_spese_bancarie = 'spese_bancarie' in colonne
        except Exception:
            has_tipo_fattura = False
            has_tipo_pagamento = False
            has_spese_bancarie = False

        if has_tipo_fattura and has_tipo_pagamento and has_spese_bancarie:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento, spese_bancarie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento_id, spese_bancarie
            ))
        elif has_tipo_fattura and has_tipo_pagamento:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento_id
            ))
        elif has_tipo_fattura and has_spese_bancarie:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_fattura, spese_bancarie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_fattura, spese_bancarie
            ))
        elif has_tipo_pagamento and has_spese_bancarie:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_pagamento, spese_bancarie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_pagamento_id, spese_bancarie
            ))
        elif has_tipo_fattura:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_fattura)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_fattura
            ))
        elif has_tipo_pagamento:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, tipo_pagamento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_pagamento_id
            ))
        elif has_spese_bancarie:
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email, spese_bancarie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, spese_bancarie
            ))
        else:
            # Fallback alla query originale se le colonne non esistono
            query = """
                INSERT INTO soggetti
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale,
                 partita_iva, citta, cap, provincia, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, denominazione, 'CLIENTE', codice_fiscale,
                partita_iva, citta, cap, provincia, email
            ))

        return self.cursor.lastrowid, False
    
    def aggiorna_tipo_fattura_pagamento(self, soggetto_id, tipo_fattura, tipo_pagamento_id, spese_bancarie=None):
        """Aggiorna tipo_fattura, tipo_pagamento e spese_bancarie per un soggetto esistente."""
        try:
            # Verifica se le colonne esistono
            self.cursor.execute("PRAGMA table_info(soggetti)")
            colonne = [col[1] for col in self.cursor.fetchall()]
            has_tipo_fattura = 'tipo_fattura' in colonne
            has_tipo_pagamento = 'tipo_pagamento' in colonne
            has_spese_bancarie = 'spese_bancarie' in colonne
            
            if not has_tipo_fattura and not has_tipo_pagamento and not has_spese_bancarie:
                return
            
            # Costruisci la query UPDATE dinamicamente
            updates = []
            params = []
            
            if has_tipo_fattura and tipo_fattura:
                updates.append("tipo_fattura = ?")
                params.append(tipo_fattura)
            
            if has_tipo_pagamento and tipo_pagamento_id:
                updates.append("tipo_pagamento = ?")
                params.append(tipo_pagamento_id)
            
            if has_spese_bancarie and spese_bancarie:
                updates.append("spese_bancarie = ?")
                params.append(spese_bancarie)
            
            if updates:
                params.append(soggetto_id)
                query = f"UPDATE soggetti SET {', '.join(updates)} WHERE id = ?"
                self.cursor.execute(query, params)
        except Exception as e:
            # Ignora errori se le colonne non esistono o altri problemi
            self.log(f"  ⚠ Errore aggiornamento tipo_fattura/pagamento/spese_bancarie: {str(e)}")

    def inserisci_documento(self, root, soggetto_id):
        """Inserisce un nuovo documento (fattura vendita)"""
        tipo_doc_xml = self.estrai_testo(root, './/DatiGeneraliDocumento/TipoDocumento')
        numero_documento_raw = self.estrai_testo(root, './/DatiGeneraliDocumento/Numero')
        
        # Normalizza il numero della fattura (almeno 4 cifre)
        numero_documento = self.normalizza_numero_fattura(numero_documento_raw)

        if self.verifica_documento_esistente(soggetto_id, numero_documento):
            return None

        tipo_documento = self.get_tipo_documento_mapping(tipo_doc_xml)
        segno = self.get_segno_documento(tipo_doc_xml)

        data_documento_str = self.estrai_testo(root, './/DatiGeneraliDocumento/Data')
        if data_documento_str:
            try:
                data_obj = datetime.strptime(data_documento_str, '%Y-%m-%d')
                data_documento = data_obj.strftime('%d/%m/%Y')
            except Exception:
                data_documento = data_documento_str
        else:
            data_documento = ''

        data_registrazione = datetime.now().strftime('%d/%m/%Y')
        totale = self.estrai_testo(root, './/DatiGeneraliDocumento/ImportoTotaleDocumento')
        
        # CALCOLA L'IMPONIBILE TOTALE
        imponibile_totale = self.calcola_imponibile_totale(root)
        
        # Verifica se la fattura è agganciabile a una dichiarazione d'intento
        ha_dichiarazione_intento = self.verifica_dichiarazione_intento(root)
        
        # Determina il valore per id_dichiarazione_intento:
        # - 1 se agganciabile (valore provvisorio)
        # - NULL se aliquota normale
        id_dichiarazione_intento = 1 if ha_dichiarazione_intento else None
        
        # Verifica se esiste la colonna id_dichiarazione_intento
        try:
            self.cursor.execute("PRAGMA table_info(documenti)")
            colonne = [col[1] for col in self.cursor.fetchall()]
            has_dichiarazione_field = "id_dichiarazione_intento" in colonne
        except:
            has_dichiarazione_field = False
        
        if has_dichiarazione_field:
            query = """
                INSERT INTO documenti
                (soggetto_id, tipo_documento, segno, numero_documento,
                 data_documento, data_registrazione, totale, importo_imponibile, id_dichiarazione_intento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                soggetto_id, tipo_documento, segno, numero_documento,
                data_documento, data_registrazione, totale, imponibile_totale, id_dichiarazione_intento
            ))
        else:
            query = """
                INSERT INTO documenti
                (soggetto_id, tipo_documento, segno, numero_documento,
                 data_documento, data_registrazione, totale, importo_imponibile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                soggetto_id, tipo_documento, segno, numero_documento,
                data_documento, data_registrazione, totale, imponibile_totale
            ))

        return self.cursor.lastrowid

    def inserisci_scadenze(self, root, documento_id):
        """Inserisce le scadenze del documento e crea la Ri.Ba. quando il tipo pagamento è RIBA."""
        dettagli_pagamento = root.findall('.//DatiPagamento/DettaglioPagamento')

        if dettagli_pagamento:
            for idx, dettaglio in enumerate(dettagli_pagamento, 1):
                data_scadenza_str = self.estrai_testo(dettaglio, 'DataScadenzaPagamento')

                if data_scadenza_str:
                    try:
                        data_obj = datetime.strptime(data_scadenza_str, '%Y-%m-%d')
                        data_scadenza = data_obj.strftime('%d/%m/%Y')
                    except Exception:
                        data_scadenza = data_scadenza_str
                else:
                    data_scadenza = datetime.now().strftime('%d/%m/%Y')

                modalita_pagamento = self.estrai_testo(dettaglio, 'ModalitaPagamento')
                tipo_pagamento = self.get_tipo_pagamento(modalita_pagamento)
                importo_scadenza = self.estrai_testo(dettaglio, 'ImportoPagamento')

                query = """
                    INSERT INTO scadenze
                    (id_documento, numero_rata, data_scadenza, tipo_pagamento, importo_scadenza)
                    VALUES (?, ?, ?, ?, ?)
                """

                self.cursor.execute(query, (
                    documento_id, idx, data_scadenza, tipo_pagamento, importo_scadenza
                ))

                scadenza_id = self.cursor.lastrowid

                # Se il tipo pagamento è RIBA -> crea la riba associata
                if tipo_pagamento and tipo_pagamento.strip().upper() == 'RIBA':
                    try:
                        self.cursor.execute("""
                            INSERT INTO riba (scadenza_id, data_scadenza, importo, stato)
                            VALUES (?, ?, ?, 'Da emettere')
                        """, (scadenza_id, data_scadenza, importo_scadenza))
                    except Exception:
                        # ignora errori se la tabella riba non esiste o struttura diversa
                        pass

        else:
            # Caso senza dettagliPagamento -> singola scadenza
            data_scadenza = datetime.now().strftime('%d/%m/%Y')
            tipo_pagamento = 'BONIFICO'
            importo_scadenza = self.estrai_testo(root, './/DatiGeneraliDocumento/ImportoTotaleDocumento')

            query = """
                INSERT INTO scadenze
                (id_documento, numero_rata, data_scadenza, tipo_pagamento, importo_scadenza)
                VALUES (?, ?, ?, ?, ?)
            """

            self.cursor.execute(query, (
                documento_id, 1, data_scadenza, tipo_pagamento, importo_scadenza
            ))

            scadenza_id = self.cursor.lastrowid
            # no riba per default

    def elabora_file_xml(self, file_path):
        """Elabora un singolo file XML"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Verifica il tipo di fattura - salta se non è TD01 o TD24
            tipo_fattura = self.estrai_tipo_fattura(root)
            if tipo_fattura is None:
                self.log(f"  ⚠ Tipo documento non supportato - File saltato: {os.path.basename(file_path)}")
                return True  # Restituisce True perché non è un errore, solo un file da saltare

            # Verifica se è una fattura estera (prima di inserire il soggetto)
            id_paese = self.estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdPaese', 'IT')
            is_estera = (id_paese and id_paese != 'IT')

            soggetto_id, _ = self.inserisci_soggetto(root)

            if soggetto_id is None:
                return False

            # Verifica se il documento esiste già (anche per fatture estere)
            numero_documento_raw = self.estrai_testo(root, './/DatiGeneraliDocumento/Numero')
            numero_documento = self.normalizza_numero_fattura(numero_documento_raw)
            
            if self.verifica_documento_esistente(soggetto_id, numero_documento):
                # Documento già presente, salta
                if is_estera:
                    self.fatture_estere += 1
                    self.log(f"  ⚠ Fattura estera già presente: {numero_documento} per soggetto ID {soggetto_id} - Saltata")
                else:
                    self.log(f"  ⚠ Fattura già presente: {numero_documento} per soggetto ID {soggetto_id} - Saltata")
                return True

            documento_id = self.inserisci_documento(root, soggetto_id)

            if documento_id is None:
                return True
            
            # Estrai dati documento per il log e per le dichiarazioni d'intento
            numero_documento_raw = self.estrai_testo(root, './/DatiGeneraliDocumento/Numero')
            numero_documento = self.normalizza_numero_fattura(numero_documento_raw)
            data_documento_str = self.estrai_testo(root, './/DatiGeneraliDocumento/Data')
            if data_documento_str:
                try:
                    data_obj = datetime.strptime(data_documento_str, '%Y-%m-%d')
                    data_documento = data_obj.strftime('%d/%m/%Y')
                except Exception:
                    data_documento = data_documento_str
            else:
                data_documento = ''
            
            # Se è stata riconosciuta una dichiarazione d'intento, salva i dati
            if self.verifica_dichiarazione_intento(root):
                # Estrai l'imponibile dalla dichiarazione d'intento
                imponibile_di = self.estrai_imponibile_dichiarazione_intento(root)
                
                self.log(f"  ✓ Dichiarazione d'intento riconosciuta per fattura {numero_documento}")
                
                # Salva i dati per la finestra di selezione
                self.fatture_con_di.append({
                    'documento_id': documento_id,
                    'soggetto_id': soggetto_id,
                    'numero_documento': numero_documento,
                    'data_documento': data_documento,
                    'imponibile': imponibile_di
                })

            # Inserisce scadenze (e eventuali riba)
            self.inserisci_scadenze(root, documento_id)

            self.conn.commit()
            self.fatture_elaborate += 1
            
            # Raccogli dati della fattura per il riepilogo
            numero_documento_raw = self.estrai_testo(root, './/DatiGeneraliDocumento/Numero')
            numero_documento = self.normalizza_numero_fattura(numero_documento_raw)
            data_documento_str = self.estrai_testo(root, './/DatiGeneraliDocumento/Data')
            if data_documento_str:
                try:
                    data_obj = datetime.strptime(data_documento_str, '%Y-%m-%d')
                    data_documento = data_obj.strftime('%d/%m/%Y')
                except Exception:
                    data_documento = data_documento_str
            else:
                data_documento = ''
            
            # Recupera nome cliente dal database
            self.cursor.execute("SELECT ragione_sociale FROM soggetti WHERE id = ?", (soggetto_id,))
            cliente_row = self.cursor.fetchone()
            cliente = cliente_row[0] if cliente_row else ''
            
            totale = self.estrai_testo(root, './/DatiGeneraliDocumento/ImportoTotaleDocumento')
            try:
                totale_float = float(totale) if totale else 0.0
            except (ValueError, TypeError):
                totale_float = 0.0
            
            self.fatture_importate.append({
                'numero': numero_documento,
                'data': data_documento,
                'cliente': cliente,
                'totale': totale_float,
                'soggetto_id': soggetto_id,
                'documento_id': documento_id
            })

            return True

        except Exception as e:
            self.log(f"✗ Errore: {os.path.basename(file_path)} - {str(e)}")
            if self.conn:
                self.conn.rollback()
            return False

    def esegui_importazione(self):
        """Esegue l'importazione di tutti i file XML"""
        self.log("="*60)
        self.log("IMPORTAZIONE FATTURE VENDITA XML")
        self.log("="*60)
        self.log("")

        try:
            self.connetti_db()
        except Exception as e:
            self.log(f"✗ ERRORE: Impossibile connettersi al database")
            self.log(f"  {str(e)}")
            return

        xml_files = list(Path(self.xml_folder).glob('*.xml'))

        if not xml_files:
            self.log(f"⚠ Nessun file XML trovato nella cartella:")
            self.log(f"  {self.xml_folder}")
            self.disconnetti_db()
            return

        self.log(f"📁 Trovati {len(xml_files)} file XML da elaborare")
        self.log("")

        for xml_file in xml_files:
            nome_file = xml_file.name

            if self.elabora_file_xml(xml_file):
                self.log(f"Elaborazione: {nome_file}... ✓")
            else:
                self.log(f"Elaborazione: {nome_file}... ✗")
                self.file_con_errori.append(nome_file)

        self.disconnetti_db()

        # Riepilogo
        self.log("")
        self.log("="*60)
        self.log("RIEPILOGO IMPORTAZIONE")
        self.log("="*60)
        self.log(f"✓ Fatture elaborate con successo: {self.fatture_elaborate}")

        if self.fatture_estere > 0:
            self.log(f"⚠ Fatture estere (saltate): {self.fatture_estere}")

        if self.file_con_errori:
            self.log(f"\n✗ File con errori ({len(self.file_con_errori)}):")
            for file_errore in self.file_con_errori:
                self.log(f"  • {file_errore}")
        else:
            self.log("\n✓ Nessun errore rilevato")

        self.log("="*60)
        self.log("\n🎉 Importazione completata!")


class ImportaDocumentoVenditeWindow(tk.Toplevel):
    def __init__(self, parent, db_path, cartella_base):
        super().__init__(parent)

        self.parent = parent
        self.db_path = db_path
        self.cartella_base = cartella_base
        self.callback_success = None

        self.title("Importazione Fatture XML - Vendite")
        self.geometry("750x600")
        self.resizable(True, True)
        self.transient(parent)

        # Leggi config.ini
        self.config_path = "config.ini"
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

        # Estrai anno e mese correnti dal percorso config
        self.anno_corrente, self.mese_corrente = self.estrai_anno_mese_da_config()

        self.create_widgets()
        self.center_window()

    def estrai_anno_mese_da_config(self):
        """Estrae anno e mese dal percorso nel database (parametro importvendite)."""
        try:
            percorso = get_import_vendite()
            if percorso:
                parti = percorso.replace('\\', '/').split('/')

                if len(parti) >= 2:
                    anno = parti[-2]
                    mese = parti[-1]
                    return anno, mese
        except Exception:
            pass

        now = datetime.now()
        return str(now.year), f"{now.month:02d}"

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        title_label = tk.Label(
            main_frame,
            text="Importazione Fatture Clienti da XML",
            font=('Arial', 14, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 20))

        periodo_frame = tk.LabelFrame(
            main_frame,
            text="Seleziona Periodo",
            font=('Arial', 11, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=15,
            pady=15
        )
        periodo_frame.pack(fill="x", pady=(0, 15))

        anno_frame = tk.Frame(periodo_frame, bg="#FFFFFF")
        anno_frame.pack(fill="x", pady=5)

        tk.Label(
            anno_frame,
            text="Anno:",
            font=('Arial', 10),
            bg="#FFFFFF",
            width=10,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        self.anno_var = tk.StringVar(value=self.anno_corrente)
        anno_combo = ttk.Combobox(
            anno_frame,
            textvariable=self.anno_var,
            values=[str(y) for y in range(2020, 2031)],
            state="readonly",
            width=15,
            font=('Arial', 10)
        )
        anno_combo.pack(side="left")

        mese_frame = tk.Frame(periodo_frame, bg="#FFFFFF")
        mese_frame.pack(fill="x", pady=5)

        tk.Label(
            mese_frame,
            text="Mese:",
            font=('Arial', 10),
            bg="#FFFFFF",
            width=10,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        mesi = [
            ("01", "Gennaio"), ("02", "Febbraio"), ("03", "Marzo"),
            ("04", "Aprile"), ("05", "Maggio"), ("06", "Giugno"),
            ("07", "Luglio"), ("08", "Agosto"), ("09", "Settembre"),
            ("10", "Ottobre"), ("11", "Novembre"), ("12", "Dicembre")
        ]

        self.mese_var = tk.StringVar(value=self.mese_corrente)
        mese_combo = ttk.Combobox(
            mese_frame,
            textvariable=self.mese_var,
            values=[f"{cod} - {nome}" for cod, nome in mesi],
            state="readonly",
            width=25,
            font=('Arial', 10)
        )
        mese_combo.pack(side="left")

        for i, (cod, nome) in enumerate(mesi):
            if cod == self.mese_corrente:
                mese_combo.current(i)
                break

        info_frame = tk.Frame(main_frame, bg="#F5F5F5", padx=10, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))

        tk.Label(
            info_frame,
            text="📁 Percorso attuale:",
            font=('Arial', 9, 'bold'),
            bg="#F5F5F5",
            fg="#555555"
        ).pack(anchor="w")

        self.percorso_label = tk.Label(
            info_frame,
            text=self.get_percorso_completo(),
            font=('Arial', 9),
            bg="#F5F5F5",
            fg="#666666",
            wraplength=650,
            justify="left"
        )
        self.percorso_label.pack(anchor="w", pady=(5, 0))

        anno_combo.bind('<<ComboboxSelected>>', lambda e: self.aggiorna_percorso())
        mese_combo.bind('<<ComboboxSelected>>', lambda e: self.aggiorna_percorso())

        text_frame = tk.LabelFrame(
            main_frame,
            text="Log Importazione",
            font=('Arial', 11, 'bold'),
            bg="#FFFFFF",
            fg="#333333",
            padx=10,
            pady=10
        )
        text_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=80,
            height=15,
            font=('Courier', 9),
            state='disabled',
            bg="#FAFAFA"
        )
        self.text_area.pack(fill="both", expand=True)

        button_frame = tk.Frame(main_frame, bg="#FFFFFF")
        button_frame.pack(fill="x")

        self.btn_importa = tk.Button(
            button_frame,
            text="▶ Avvia Importazione",
            command=self.avvia_importazione,
            bg="#4CAF50",
            fg="white",
            font=('Arial', 11, 'bold'),
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        self.btn_importa.pack(side="left", padx=(0, 10))

        btn_chiudi = tk.Button(
            button_frame,
            text="✖ Chiudi",
            command=self.destroy,
            bg="#f44336",
            fg="white",
            font=('Arial', 11, 'bold'),
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        btn_chiudi.pack(side="right")

        self.aggiungi_messaggio("Pronto per l'importazione (Vendite).")
        self.aggiungi_messaggio("Seleziona anno e mese, poi clicca su 'Avvia Importazione'.\n")

    def get_percorso_base(self):
        """Ottiene il percorso base, verificando se esiste e usando fallback se necessario"""
        try:
            # Prova prima a leggere dal database
            percorso_base = get_import_vendite()
            if percorso_base:
                parti = percorso_base.replace('\\', '/').split('/')
                if len(parti) >= 2:
                    base = '/'.join(parti[:-2])
                else:
                    base = percorso_base
                
                # Verifica se il percorso base esiste
                if base and os.path.exists(base):
                    return base
            
            # Se non esiste, prova a usare cartella_base come fallback
            if self.cartella_base and os.path.exists(self.cartella_base):
                return self.cartella_base
            
            # Prova anche a leggere cartellaemesse dal database come fallback
            try:
                cartella_emesse = get_cartella_emesse()
                if cartella_emesse and os.path.exists(cartella_emesse):
                    return cartella_emesse
            except Exception:
                pass
            
            # Se tutto fallisce, restituisci comunque il percorso dal database
            # (l'utente vedrà l'errore quando proverà a importare)
            return base if base else None
            
        except Exception:
            # Fallback a cartella_base se disponibile
            if self.cartella_base and os.path.exists(self.cartella_base):
                return self.cartella_base
            return None

    def get_percorso_completo(self):
        """Costruisce il percorso completo in base a anno e mese selezionati"""
        try:
            base = self.get_percorso_base()
            if not base:
                return "Percorso non disponibile"

            anno = self.anno_var.get()
            mese = self.mese_var.get().split(' - ')[0] if ' - ' in self.mese_var.get() else self.mese_var.get()

            percorso_completo = os.path.join(base, anno, mese)
            return percorso_completo
        except Exception:
            return "Percorso non disponibile"

    def aggiorna_percorso(self):
        self.percorso_label.config(text=self.get_percorso_completo())

    def aggiorna_config_ini(self):
        try:
            nuovo_percorso = self.get_percorso_completo()
            set_import_vendite(nuovo_percorso)
            return True
        except Exception as e:
            self.aggiungi_messaggio(f"✗ Errore aggiornamento database: {str(e)}")
            return False

    def aggiungi_messaggio(self, messaggio, end='\n'):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, messaggio + end)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')
        self.update_idletasks()

    def set_callback_success(self, callback):
        self.callback_success = callback

    def avvia_importazione(self):
        self.btn_importa.config(state='disabled')

        # Pulisci log
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state='disabled')

        # Aggiorna config.ini
        if not self.aggiorna_config_ini():
            self.btn_importa.config(state='normal')
            return

        percorso_xml = self.get_percorso_completo()

        if not os.path.exists(percorso_xml):
            self.aggiungi_messaggio(f"✗ ERRORE: La cartella non esiste:")
            self.aggiungi_messaggio(f"  {percorso_xml}\n")
            self.btn_importa.config(state='normal')
            return

        def esegui():
            try:
                importatore = ImportaFattureVenditaXML(
                    self.db_path,
                    percorso_xml,
                    self.config_path,
                    callback=self.aggiungi_messaggio
                )
                importatore.esegui_importazione()
                
                # Se ci sono fatture con dichiarazione d'intento, mostra la finestra di selezione
                if importatore.fatture_con_di:
                    self.after(0, lambda: self.mostra_finestra_dichiarazioni_intento(
                        importatore.fatture_con_di, importatore.db_path
                    ))

                if self.callback_success:
                    self.after(0, self.callback_success)

            except Exception as e:
                self.aggiungi_messaggio(f"\n✗ ERRORE CRITICO: {str(e)}")
            finally:
                self.after(0, lambda: self.btn_importa.config(state='normal'))

        thread = threading.Thread(target=esegui, daemon=True)
        thread.start()
    
    def mostra_finestra_dichiarazioni_intento(self, fatture_con_di, db_path):
        """Mostra la finestra per agganciare le fatture alle dichiarazioni d'intento"""
        from gui.documenti_page_aggancia_dichiarazioni import AgganciaDichiarazioniWindow
        AgganciaDichiarazioniWindow(self, db_path, fatture_con_di)