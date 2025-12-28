# Analisi Migrazione Parametri da config.ini a Database

## Parametri nella sezione [Parametri] di config.ini

1. `cartellaemesse` - Cartella fatture vendita
2. `cartellaricevute` - Cartella fatture acquisti  
3. `cartellastampa` - Cartella stampa
4. `importacquisti` - Cartella import acquisti (con anno/mese)
5. `importavendite` - Cartella import vendite (con anno/mese)
6. `importarapido` - Cartella import rapido

## Stato Migrazione

### ✅ Già migrati al database (letti da `parametri_db.carica_parametri()`)
- `cartellaemesse` - Usato in `scripts/scarfec32.py`
- `cartellaricevute` - Usato in `scripts/scarfec32.py`

### ❌ Ancora da migrare (letti da config.ini)
- `cartellastampa` - Usato in vari file
- `importacquisti` - Usato in `gui/documenti_page_importa.py`
- `importavendite` - Usato in `gui/documenti_page_importa_vendite.py`
- `importarapido` - Usato in `gui/documenti_page.py`

## File da Modificare

### 1. `scripts/parametri_db.py`
**Azione**: Aggiungere funzioni per leggere/scrivere i nuovi parametri cartelle

### 2. `gui/documenti_page_importa.py`
**Parametri usati**: 
- `importacquisti` (riga 618, 823, 879)
- `cartellaricevute` (riga 840) - fallback

**Modifiche necessarie**:
- Sostituire `self.config.get('Parametri', 'importacquisti')` con lettura da database
- Sostituire `self.config.get('Parametri', 'cartellaricevute')` con lettura da database
- Sostituire `self.config.set('Parametri', 'importacquisti', ...)` con scrittura su database

### 3. `gui/documenti_page_importa_vendite.py`
**Parametri usati**:
- `importavendite` (riga 895, 1083, 1137)
- `cartellaemesse` (riga 1100) - fallback

**Modifiche necessarie**:
- Sostituire `self.config.get('Parametri', 'importavendite')` con lettura da database
- Sostituire `self.config.get('Parametri', 'cartellaemesse')` con lettura da database
- Sostituire `self.config.set('Parametri', 'importavendite', ...)` con scrittura su database

### 4. `gui/documenti_page.py`
**Parametri usati**:
- `importarapido` (riga 1194)
- `cartellaricevute` (riga 761) - solo lettura

**Modifiche necessarie**:
- Sostituire `config.get('Parametri', 'importarapido')` con lettura da database
- Sostituire `c.get("Parametri", "cartellaricevute")` con lettura da database

### 5. `gui/config_window.py`
**Parametri usati**:
- `cartellaemesse` (riga 296, 368)
- `cartellaricevute` (riga 297, 369)
- `cartellastampa` (riga 298, 370)

**Modifiche necessarie**:
- Caricare i valori dal database invece che da config.ini
- Salvare i valori nel database invece che in config.ini
- Rimuovere la sezione [Parametri] dal salvataggio

### 6. `scripts/rinomina.py`
**Parametri usati**:
- `cartellaemesse` (riga 252)
- `cartellaricevute` (riga 253)
- `cartellastampa` (riga 254)

**Modifiche necessarie**:
- Sostituire lettura da config.ini con lettura da database

### 7. `scripts/carica_lista_csv.py`
**Parametri usati**:
- `cartellaricevute` (riga 37)

**Modifiche necessarie**:
- Sostituire `config.get("Parametri", "cartellaricevute")` con lettura da database

### 8. `gui/verifica_ft_acquisto_page.py`
**Parametri usati**:
- `cartellaricevute` (riga 690)

**Modifiche necessarie**:
- Sostituire `config.get("Parametri", "cartellaricevute")` con lettura da database

### 9. `gui/fatture_acquisti_page.py`
**Parametri usati**:
- `cartellaricevute` (riga 64)
- `cartellastampa` (riga 69)

**Modifiche necessarie**:
- Sostituire lettura da config.ini con lettura da database

### 10. `gui/fatture_vendita_page.py`
**Parametri usati**:
- `cartellaemesse` (riga 66)

**Modifiche necessarie**:
- Sostituire lettura da config.ini con lettura da database

### 11. `scripts/xml_parser_acquisti.py`
**Parametri usati**:
- `cartellastampa` (riga 23)

**Modifiche necessarie**:
- Sostituire `self.config.get('Parametri', 'cartellastampa')` con lettura da database

### 12. `scripts/xml_parser_vendite.py`
**Parametri usati**:
- `cartellastampa` (riga 23)

**Modifiche necessarie**:
- Sostituire `self.config.get('Parametri', 'cartellastampa')` con lettura da database

### 13. `gui/xml_parser.py`
**Parametri usati**:
- `cartellastampa` (riga 22)

**Modifiche necessarie**:
- Sostituire `self.config.get('Parametri', 'cartellastampa')` con lettura da database

### 14. `gui/mastrino_clienti_page.py`
**Parametri usati**:
- `cartellastampa` (riga 28)

**Modifiche necessarie**:
- Sostituire `config['Parametri']['cartellastampa']` con lettura da database

### 15. `scripts/converti_xml.py`
**Parametri usati**:
- `cartellaemesse` (riga 158)
- `cartellaricevute` (riga 159)

**Modifiche necessarie**:
- Sostituire lettura da config.ini con lettura da database

### 16. `scripts/extract_righe_fattura.py`
**Parametri usati**:
- `cartellaricevute` (riga 246)

**Modifiche necessarie**:
- Sostituire `config.get('Parametri', 'cartellaricevute')` con lettura da database

### 17. `gui/dichiarazioni_page.py`
**Parametri usati**:
- Nessun parametro dalla sezione [Parametri], solo lettura config.ini per altro

**Modifiche necessarie**:
- Nessuna (legge solo per altro)

## Piano di Migrazione

### Fase 1: Estendere parametri_db.py
Aggiungere funzioni per gestire tutti i parametri cartelle:
- `get_cartella_emesse()`
- `get_cartella_ricevute()`
- `get_cartella_stampa()`
- `get_import_acquisti()`
- `get_import_vendite()`
- `get_import_rapido()`
- `set_cartella_emesse(value)`
- `set_cartella_ricevute(value)`
- `set_cartella_stampa(value)`
- `set_import_acquisti(value)`
- `set_import_vendite(value)`
- `set_import_rapido(value)`

### Fase 2: Verificare struttura tabella parametri
Verificare che la tabella `parametri` contenga già i campi:
- `cartellaemesse`
- `cartellaricevute`
- `cartellastampa`
- `importacquisti`
- `importavendite`
- `importarapido`

Se mancano, creare script di migrazione per aggiungerli.

### Fase 3: Modificare tutti i file
Sostituire tutte le letture/scritture da config.ini con chiamate a `parametri_db`.

### Fase 4: Rimuovere sezione [Parametri] da config.ini
Dopo aver verificato che tutto funziona, rimuovere la sezione [Parametri] da config.ini.

## Note

- `scarfec32.py` già usa `carica_parametri()` per leggere `cartellaemesse` e `cartellaricevute` dal database
- Alcuni file usano i parametri come fallback, quindi bisogna gestire anche questi casi
- `importacquisti` e `importavendite` vengono anche scritti (aggiornati) durante l'importazione

