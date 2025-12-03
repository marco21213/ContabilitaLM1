# scripts/trasforma_fatture.py

import json
import configparser

def main():
    # 1. Leggere il file json estratto
    input_file = "fatture_estratte.json"
    output_file = "fatture_trasformate.json"

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            fatture = json.load(f)
    except FileNotFoundError:
        print(f"❌ Errore: il file '{input_file}' non esiste.")
        return

    # 2. Leggere il file di configurazione con le descrizioni
    config = configparser.ConfigParser()
    config.read("fatture_elettroniche.ini", encoding="utf-8")

    # 3. Trasformare i campi
    for fattura in fatture:
        # Sostituire tipo documento
        tipo_doc = fattura.get("tipo_documento")
        if tipo_doc and tipo_doc in config["TipoDocumento"]:
            fattura["tipo_documento"] = config["TipoDocumento"][tipo_doc]

        # Sostituire tipo pagamento per ogni scadenza
        for scadenza in fattura.get("scadenze", []):
            tipo_pag = scadenza.get("tipo_pagamento")
            if tipo_pag and tipo_pag in config["ModalitaPagamento"]:
                scadenza["tipo_pagamento"] = config["ModalitaPagamento"][tipo_pag]

    # 4. Salvare il nuovo json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(fatture, f, ensure_ascii=False, indent=4)

    print(f"✅ File trasformato salvato in '{output_file}'")

if __name__ == "__main__":
    main()
