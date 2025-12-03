import os
from fpdf import FPDF
from docx import Document

# Percorso della sottocartella RICETTE
cartella_ricette = "RICETTE"

# Controlla se la cartella esiste
if not os.path.exists(cartella_ricette):
    print(f"La cartella '{cartella_ricette}' non esiste. Creala e inserisci i file .docx.")
else:
    # Lista di file .docx nella cartella
    file_docx = [f for f in os.listdir(cartella_ricette) if f.endswith(".docx")]
    
    if not file_docx:
        print("Non ci sono file .docx nella cartella RICETTE.")
    else:
        for file in file_docx:
            file_path = os.path.join(cartella_ricette, file)
            pdf_path = os.path.join(cartella_ricette, file.replace(".docx", ".pdf"))

            # Leggi il contenuto del file .docx
            document = Document(file_path)
            contenuto = []
            for paragraph in document.paragraphs:
                contenuto.append(paragraph.text)

            # Creazione del file PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            for linea in contenuto:
                pdf.multi_cell(0, 10, linea)

            # Salva il PDF
            pdf.output(pdf_path)
            print(f"Creato: {pdf_path}")

            # Rimuove il file .docx originale
            os.remove(file_path)
            print(f"Eliminato: {file_path}")

        print("Conversione completata per tutti i file .docx in PDF.")
