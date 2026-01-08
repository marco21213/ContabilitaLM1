#!/bin/bash
# Script di avvio per ContabilitàLM1
# Attiva automaticamente il virtual environment e avvia l'applicazione

cd "$(dirname "$0")"

# Attiva il virtual environment se esiste
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment non trovato. Creazione in corso..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installazione dipendenze..."
    pip install -r requirements.txt 2>/dev/null || pip install tkcalendar pillow reportlab lxml tkinterweb pdfkit asn1crypto
fi

# Verifica che le dipendenze siano installate
python3 -c "import PIL, tkcalendar, requests" 2>/dev/null || {
    echo "Installazione dipendenze mancanti..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install tkcalendar pillow reportlab lxml tkinterweb pdfkit asn1crypto requests pytz clint tqdm
    fi
}

# Avvia l'applicazione
python3 main.py
