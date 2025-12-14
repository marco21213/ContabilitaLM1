import sqlite3
import xml.etree.ElementTree as ET
import configparser
import os
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading


class ImportaFattureXML:
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
            
    def get_prossimo_codice_soggetto(self):
        """Ottiene il prossimo codice soggetto disponibile"""
        self.cursor.execute("""
            SELECT codice_soggetto FROM soggetti 
            WHERE codice_soggetto LIKE 'F%' 
            ORDER BY codice_soggetto DESC LIMIT 1
        """)
        
        result = self.cursor.fetchone()
        if result:
            ultimo_codice = result[0]
            numero = int(ultimo_codice[1:]) + 1
        else:
            numero = 1
            
        return f"F{numero:04d}"
    
    def get_tipo_documento_mapping(self, tipo_xml):
        """Ottiene la mappatura del tipo documento dal config"""
        try:
            return self.config.get('TipoDocumento Fornitori', tipo_xml).upper()
        except:
            return tipo_xml.upper()
    
    def get_segno_documento(self, tipo_xml):
        """Ottiene il segno del documento dal config"""
        try:
            return self.config.get('SegnoDocumento Fornitori', tipo_xml).upper()
        except:
            return '+'
    
    def get_tipo_pagamento(self, codice_pagamento):
        """Ottiene il tipo di pagamento dal config"""
        try:
            return self.config.get('Pagamenti', codice_pagamento).upper()
        except:
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
    
    def verifica_soggetto_esistente(self, partita_iva, codice_fiscale):
        """Verifica se un soggetto esiste già nel database"""
        query = """
            SELECT id, tipo_soggetto FROM soggetti 
            WHERE (partita_iva = ? AND partita_iva != '') 
            OR (codice_fiscale = ? AND codice_fiscale != '')
        """
        self.cursor.execute(query, (partita_iva, codice_fiscale))
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
        """Inserisce un nuovo soggetto o recupera quello esistente"""
        id_paese = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdPaese', 'IT')
        
        if id_paese and id_paese != 'IT':
            return None, True
        
        partita_iva = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice')
        codice_fiscale = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/CodiceFiscale')
        
        # Estrai tipo_fattura e tipo_pagamento
        tipo_fattura = self.estrai_tipo_fattura(root)
        
        # Estrai modalità pagamento dal primo DettaglioPagamento
        modalita_pagamento_xml = self.estrai_testo(root, './/DatiPagamento/DettaglioPagamento/ModalitaPagamento', '')
        tipo_pagamento_id = self.get_tipo_pagamento_id(modalita_pagamento_xml) if modalita_pagamento_xml else None
        
        soggetto_id, tipo_soggetto_esistente = self.verifica_soggetto_esistente(partita_iva, codice_fiscale)
        
        if soggetto_id:
            # Se il soggetto esiste già, gestiamo il tipo_soggetto
            if tipo_soggetto_esistente == 'CLIENTE':
                # Se era cliente, aggiorniamo a 'ENTRAMBI'
                self.aggiorna_tipo_soggetto(soggetto_id, 'ENTRAMBI')
                self.log(f"  Aggiornato tipo_soggetto a 'ENTRAMBI' per soggetto esistente (ID: {soggetto_id})")
            elif tipo_soggetto_esistente == 'FORNITORE':
                # Se era già fornitore, non facciamo nulla
                pass
            elif tipo_soggetto_esistente == 'ENTRAMBI':
                # Se era già entrambi, non facciamo nulla
                pass
            
            # Aggiorna tipo_fattura e tipo_pagamento se disponibili
            if tipo_fattura or tipo_pagamento_id:
                self.aggiorna_tipo_fattura_pagamento(soggetto_id, tipo_fattura, tipo_pagamento_id)
            
            return soggetto_id, False
        
        denominazione = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione')
        if denominazione:
            ragione_sociale = denominazione
        else:
            cognome = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/Anagrafica/Cognome')
            nome = self.estrai_testo(root, './/CedentePrestatore/DatiAnagrafici/Anagrafica/Nome')
            ragione_sociale = f"{cognome} {nome}".strip()
        
        citta = self.estrai_testo(root, './/CedentePrestatore/Sede/Comune')
        cap = self.estrai_testo(root, './/CedentePrestatore/Sede/CAP')
        provincia = self.estrai_testo(root, './/CedentePrestatore/Sede/Provincia')
        email = self.estrai_testo(root, './/CedentePrestatore/Contatti/Email')
        
        codice_soggetto = self.get_prossimo_codice_soggetto()
        
        # Costruisci la query INSERT includendo tipo_fattura e tipo_pagamento
        # Verifica se le colonne esistono nella tabella
        try:
            self.cursor.execute("PRAGMA table_info(soggetti)")
            colonne = [col[1] for col in self.cursor.fetchall()]
            has_tipo_fattura = 'tipo_fattura' in colonne
            has_tipo_pagamento = 'tipo_pagamento' in colonne
        except Exception:
            has_tipo_fattura = False
            has_tipo_pagamento = False
        
        if has_tipo_fattura and has_tipo_pagamento:
            query = """
                INSERT INTO soggetti 
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale, 
                 partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, ragione_sociale, 'FORNITORE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_fattura, tipo_pagamento_id
            ))
        elif has_tipo_fattura:
            query = """
                INSERT INTO soggetti 
                (codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale, 
                 partita_iva, citta, cap, provincia, email, tipo_fattura)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                codice_soggetto, ragione_sociale, 'FORNITORE', codice_fiscale,
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
                codice_soggetto, ragione_sociale, 'FORNITORE', codice_fiscale,
                partita_iva, citta, cap, provincia, email, tipo_pagamento_id
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
                codice_soggetto, ragione_sociale, 'FORNITORE', codice_fiscale,
                partita_iva, citta, cap, provincia, email
            ))
        
        return self.cursor.lastrowid, False
    
    def aggiorna_tipo_fattura_pagamento(self, soggetto_id, tipo_fattura, tipo_pagamento_id):
        """Aggiorna tipo_fattura e tipo_pagamento per un soggetto esistente."""
        try:
            # Verifica se le colonne esistono
            self.cursor.execute("PRAGMA table_info(soggetti)")
            colonne = [col[1] for col in self.cursor.fetchall()]
            has_tipo_fattura = 'tipo_fattura' in colonne
            has_tipo_pagamento = 'tipo_pagamento' in colonne
            
            if not has_tipo_fattura and not has_tipo_pagamento:
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
            
            if updates:
                params.append(soggetto_id)
                query = f"UPDATE soggetti SET {', '.join(updates)} WHERE id = ?"
                self.cursor.execute(query, params)
        except Exception as e:
            # Ignora errori se le colonne non esistono o altri problemi
            self.log(f"  ⚠ Errore aggiornamento tipo_fattura/pagamento: {str(e)}")
    
    def inserisci_documento(self, root, soggetto_id):
        """Inserisce un nuovo documento"""
        tipo_doc_xml = self.estrai_testo(root, './/DatiGeneraliDocumento/TipoDocumento')
        numero_documento = self.estrai_testo(root, './/DatiGeneraliDocumento/Numero')
        
        if self.verifica_documento_esistente(soggetto_id, numero_documento):
            return None
        
        tipo_documento = self.get_tipo_documento_mapping(tipo_doc_xml)
        segno = self.get_segno_documento(tipo_doc_xml)
        
        data_documento_str = self.estrai_testo(root, './/DatiGeneraliDocumento/Data')
        if data_documento_str:
            try:
                data_obj = datetime.strptime(data_documento_str, '%Y-%m-%d')
                data_documento = data_obj.strftime('%d/%m/%Y')
            except ValueError:
                data_documento = ''
        else:
            data_documento = ''
        
        data_registrazione = datetime.now().strftime('%d/%m/%Y')
        totale = self.estrai_testo(root, './/DatiGeneraliDocumento/ImportoTotaleDocumento')
        
        # CALCOLA L'IMPONIBILE TOTALE
        imponibile_totale = self.calcola_imponibile_totale(root)
        
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
        """Inserisce le scadenze del documento"""
        dettagli_pagamento = root.findall('.//DatiPagamento/DettaglioPagamento')
        
        if dettagli_pagamento:
            for idx, dettaglio in enumerate(dettagli_pagamento, 1):
                data_scadenza_str = self.estrai_testo(dettaglio, 'DataScadenzaPagamento')
                
                if data_scadenza_str:
                    try:
                        data_obj = datetime.strptime(data_scadenza_str, '%Y-%m-%d')
                        data_scadenza = data_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        data_scadenza = datetime.now().strftime('%d/%m/%Y')
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
        else:
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
            
            soggetto_id, is_estera = self.inserisci_soggetto(root)
            
            if is_estera:
                self.fatture_estere += 1
                return True
            
            if soggetto_id is None:
                return False
            
            documento_id = self.inserisci_documento(root, soggetto_id)
            
            if documento_id is None:
                return True
            
            self.inserisci_scadenze(root, documento_id)
            
            self.conn.commit()
            self.fatture_elaborate += 1
            
            return True
            
        except Exception as e:
            self.log(f"✗ Errore: {os.path.basename(file_path)} - {str(e)}")
            self.conn.rollback()
            return False
    
    def esegui_importazione(self):
        """Esegue l'importazione di tutti i file XML"""
        self.log("="*60)
        self.log("IMPORTAZIONE FATTURE XML")
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


class ImportaDocumentoWindow(tk.Toplevel):
    def __init__(self, parent, db_path, cartella_base):
        super().__init__(parent)
        
        self.parent = parent
        self.db_path = db_path
        self.cartella_base = cartella_base
        self.callback_success = None
        
        self.title("Importazione Fatture XML")
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
        
        # Centra la finestra
        self.center_window()
        
    def estrai_anno_mese_da_config(self):
        """Estrae anno e mese dal percorso nel config.ini"""
        try:
            percorso = self.config.get('Parametri', 'importacquisti')
            parti = percorso.replace('\\', '/').split('/')
            
            # Prende gli ultimi due elementi (anno e mese)
            if len(parti) >= 2:
                anno = parti[-2]
                mese = parti[-1]
                return anno, mese
        except:
            pass
        
        # Default: anno e mese correnti
        now = datetime.now()
        return str(now.year), f"{now.month:02d}"
    
    def center_window(self):
        """Centra la finestra sullo schermo"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        # Frame principale
        main_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Titolo
        title_label = tk.Label(
            main_frame,
            text="Importazione Fatture Fornitori da XML",
            font=('Arial', 14, 'bold'),
            bg="#FFFFFF",
            fg="#333333"
        )
        title_label.pack(pady=(0, 20))
        
        # Frame selezione periodo
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
        
        # Riga anno
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
        
        # Riga mese
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
        
        # Imposta il valore iniziale corretto
        for i, (cod, nome) in enumerate(mesi):
            if cod == self.mese_corrente:
                mese_combo.current(i)
                break
        
        # Info percorso
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
        
        # Aggiorna percorso quando cambiano anno o mese
        anno_combo.bind('<<ComboboxSelected>>', lambda e: self.aggiorna_percorso())
        mese_combo.bind('<<ComboboxSelected>>', lambda e: self.aggiorna_percorso())
        
        # Area di testo per i messaggi
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
        
        # Frame pulsanti
        button_frame = tk.Frame(main_frame, bg="#FFFFFF")
        button_frame.pack(fill="x")
        
        # Pulsante Importa
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
        
        # Pulsante Chiudi
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
        
        # Messaggio iniziale
        self.aggiungi_messaggio("Pronto per l'importazione.")
        self.aggiungi_messaggio("Seleziona anno e mese, poi clicca su 'Avvia Importazione'.\n")
    
    def get_percorso_completo(self):
        """Costruisce il percorso completo in base a anno e mese selezionati"""
        try:
            percorso_base = self.config.get('Parametri', 'importacquisti')
            # Rimuovi gli ultimi due livelli (anno e mese)
            parti = percorso_base.replace('\\', '/').split('/')
            if len(parti) >= 2:
                base = '/'.join(parti[:-2])
            else:
                base = percorso_base
            
            anno = self.anno_var.get()
            mese = self.mese_var.get().split(' - ')[0] if ' - ' in self.mese_var.get() else self.mese_var.get()
            
            return f"{base}/{anno}/{mese}".replace('/', '\\')
        except:
            return "Percorso non disponibile"
    
    def aggiorna_percorso(self):
        """Aggiorna la label con il percorso corrente"""
        self.percorso_label.config(text=self.get_percorso_completo())
    
    def aggiorna_config_ini(self):
        """Aggiorna il file config.ini con il nuovo percorso"""
        try:
            nuovo_percorso = self.get_percorso_completo()
            self.config.set('Parametri', 'importacquisti', nuovo_percorso)
            
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            
            return True
        except Exception as e:
            self.aggiungi_messaggio(f"✗ Errore aggiornamento config.ini: {str(e)}")
            return False
    
    def aggiungi_messaggio(self, messaggio, end='\n'):
        """Aggiunge un messaggio all'area di testo"""
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, messaggio + end)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')
        self.update_idletasks()
    
    def set_callback_success(self, callback):
        """Imposta la callback da chiamare dopo l'importazione"""
        self.callback_success = callback
    
    def avvia_importazione(self):
        """Avvia l'importazione in un thread separato"""
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
        
        # Verifica che la cartella esista
        if not os.path.exists(percorso_xml):
            self.aggiungi_messaggio(f"✗ ERRORE: La cartella non esista:")
            self.aggiungi_messaggio(f"  {percorso_xml}\n")
            self.btn_importa.config(state='normal')
            return
        
        def esegui():
            try:
                importatore = ImportaFattureXML(
                    self.db_path,
                    percorso_xml,
                    self.config_path,
                    callback=self.aggiungi_messaggio
                )
                importatore.esegui_importazione()
                
                # Chiama la callback per aggiornare la tabella principale
                if self.callback_success:
                    self.after(0, self.callback_success)
                    
            except Exception as e:
                self.aggiungi_messaggio(f"\n✗ ERRORE CRITICO: {str(e)}")
            finally:
                self.after(0, lambda: self.btn_importa.config(state='normal'))
        
        thread = threading.Thread(target=esegui, daemon=True)
        thread.start()