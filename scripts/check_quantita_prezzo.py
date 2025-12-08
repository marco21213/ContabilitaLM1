# check_quantita_prezzo.py
import xml.etree.ElementTree as ET

def check_quantita_prezzo(root):
    """
    Controlla solo le righe articolo che hanno UnitaMisura.
    Ignora le righe descrittive (senza Quantita, PrezzoUnitario, UnitaMisura).
    """

    problemi = []

    # Trova tutte le linee
    linee = root.findall(".//DettaglioLinee")

    for linea in linee:
        numero = linea.findtext("NumeroLinea", "?")

        unita_misura = linea.findtext("UnitaMisura", "").strip()

        # ❌ Se non c'è unità di misura → riga descrittiva → IGNORA
        if not unita_misura:
            continue

        # Legge valori
        quantita = linea.findtext("Quantita", "0").replace(",", ".")
        prezzo = linea.findtext("PrezzoUnitario", "0").replace(",", ".")

        try:
            quantita = float(quantita)
        except:
            quantita = 0

        try:
            prezzo = float(prezzo)
        except:
            prezzo = 0

        # Controllo solo sulle righe significative
        if quantita <= 0 or prezzo <= 0:
            problemi.append({
                "linea": numero,
                "quantita": quantita,
                "prezzo": prezzo,
                "unità": unita_misura,
                "messaggio": (
                    f"Linea {numero} (UM: {unita_misura}) — "
                    f"Quantità={quantita}, Prezzo={prezzo}"
                )
            })

    return problemi
