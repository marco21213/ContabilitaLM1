# ANALISI DETTAGLIATA - Importazione Vendite

## FLUSSO PRINCIPALE

### 1. `esegui_importazione()` (riga 847)
- Connette al database
- Trova tutti i file XML nella cartella
- Per ogni file chiama `elabora_file_xml()`

### 2. `elabora_file_xml(file_path)` (riga 732)
**PASSO 1:** Verifica tipo documento (TD01 o TD24)
- Chiama `estrai_tipo_fattura(root)` (riga 105)
- Se non è TD01 o TD24, salta il file

**PASSO 2:** Verifica se è fattura estera (riga 744-746)
- Estrae `IdPaese` da `CessionarioCommittente`
- Se non è 'IT', marca come estera

**PASSO 3:** Inserisce/Recupera il soggetto (CLIENTE) (riga 748)
- Chiama `inserisci_soggetto(root)` ← **QUESTO È IL PUNTO CRITICO**

**PASSO 4:** Verifica se documento esiste già (riga 757)
- Usa `soggetto_id` e `numero_documento`

**PASSO 5:** Inserisce il documento (riga 766)
- Chiama `inserisci_documento(root, soggetto_id)`

**PASSO 6:** Recupera nome cliente per riepilogo (riga 819-822)
- Query: `SELECT ragione_sociale FROM soggetti WHERE id = ?`
- Usa il `soggetto_id` ottenuto al PASSO 3

---

## ANALISI DETTAGLIATA: `inserisci_soggetto(root)` (riga 341)

### FASE 1: Estrazione dati CLIENTE da XML (righe 343-353)
```python
id_paese = estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdPaese', 'IT')
partita_iva = estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice')
codice_fiscale = estrai_testo(root, './/CessionarioCommittente/DatiAnagrafici/CodiceFiscale')
```
✅ **CORRETTO**: Estrae da `CessionarioCommittente` (cliente)

### FASE 2: Verifica soggetto esistente (riga 373)
```python
soggetto_id, tipo_soggetto_esistente = verifica_soggetto_esistente(partita_iva, codice_fiscale)
```
**QUERY (riga 295-302):**
```sql
SELECT id, tipo_soggetto FROM soggetti
WHERE (partita_iva = ? AND partita_iva IS NOT NULL)
OR (codice_fiscale = ? AND codice_fiscale IS NOT NULL)
```

⚠️ **POSSIBILE PROBLEMA**: Se trova un soggetto con stessa P.IVA o CF, lo riutilizza.
- Se quel soggetto è un FORNITORE, viene riutilizzato per il CLIENTE!

### FASE 3: Gestione soggetto esistente (righe 395-428)
- Se `tipo_soggetto_esistente == 'FORNITORE'`:
  - Controlla se la P.IVA coincide con quella del fornitore (noi stessi)
  - Se coincide, crea nuovo cliente
  - Altrimenti, aggiorna a 'ENTRAMBI'
  
⚠️ **PROBLEMA POTENZIALE**: Se un fornitore ha la stessa P.IVA di un cliente, viene riutilizzato!

### FASE 4: Creazione nuovo cliente (righe 430-559)
- Estrae denominazione da `CessionarioCommittente` ✅
- Estrae città, cap, provincia, email da `CessionarioCommittente` ✅
- Crea nuovo record con `tipo_soggetto = 'CLIENTE'` ✅

---

## FUNZIONE `estrai_testo()` (riga 175)

```python
def estrai_testo(self, root, xpath, default=''):
    elemento = root.find(xpath)
    if elemento is not None and elemento.text:
        return elemento.text.strip().upper()  # ← CONVERTE IN MAIUSCOLO
    return default.upper()
```

⚠️ **PROBLEMA**: Converte tutto in MAIUSCOLO!
- Questo potrebbe causare problemi se ci sono confronti case-sensitive
- Ma per P.IVA e CF dovrebbe essere OK

---

## POSSIBILI CAUSE DEL PROBLEMA

### 1. **Soggetto esistente riutilizzato erroneamente**
- Scenario: Esiste un FORNITORE con P.IVA = "12345678901"
- Viene importata una vendita con CLIENTE che ha P.IVA = "12345678901"
- Il sistema trova il fornitore e lo riutilizza
- Anche se viene aggiornato a 'ENTRAMBI', il nome rimane quello del fornitore!

### 2. **Problema nella query di verifica**
- La query cerca per P.IVA O Codice Fiscale
- Se un fornitore ha stesso CF di un cliente, viene riutilizzato

### 3. **Problema nel recupero finale del nome**
- Riga 820: `SELECT ragione_sociale FROM soggetti WHERE id = ?`
- Se il `soggetto_id` è sbagliato (fornitore invece di cliente), recupera nome sbagliato

---

## SOLUZIONE PROPOSTA

### Modifica `verifica_soggetto_esistente()` per le vendite:
- Quando si importa una vendita, NON riutilizzare un FORNITORE
- Creare sempre un nuovo CLIENTE se il soggetto trovato è un FORNITORE
- Oppure verificare anche il `tipo_soggetto` nella query

### Query modificata:
```sql
SELECT id, tipo_soggetto FROM soggetti
WHERE ((partita_iva = ? AND partita_iva IS NOT NULL)
   OR (codice_fiscale = ? AND codice_fiscale IS NOT NULL))
AND tipo_soggetto IN ('CLIENTE', 'ENTRAMBI')  -- Escludi FORNITORI puri
```

---

## TEST DA FARE

1. Verificare nei log [DEBUG] cosa viene estratto
2. Verificare se viene trovato un soggetto esistente
3. Verificare il tipo_soggetto del soggetto trovato
4. Verificare il nome salvato nel database dopo l'importazione
