import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import configparser

def send_email_with_attachment():
    try:
        # Leggere i parametri dal file config.ini
        config = configparser.ConfigParser()
        config.read("config.ini")
        
        sender_email = config.get("Configurazione", "sender_email")
        sender_password = config.get("Configurazione", "sender_password")
        recipient_email = config.get("Configurazione", "recipient_email")
        body = config.get("Configurazione", "body")

        # Cartella contenente il file
        folder = "ricette"

        # Identificare l'unico file PDF nella cartella
        pdf_files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
        if len(pdf_files) != 1:
            print("Errore: La cartella deve contenere esattamente un file PDF.")
            return

        file_name = pdf_files[0]
        file_path = os.path.join(folder, file_name)

        # Estrarre il soggetto dall'omonimo del file
        subject = os.path.splitext(file_name)[0]

        # Creazione del messaggio
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Corpo dell'email
        msg.attach(MIMEText(body, 'plain'))

        # Allegato
        with open(file_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={file_name}')
        msg.attach(part)

        # Connessione al server SMTP
        with smtplib.SMTP('smtp.linea-emme.com', 587) as server:
            server.starttls()  # Connessione sicura
            server.login(sender_email, sender_password)  # Login
            server.send_message(msg)  # Invio
            print("Email inviata con successo!")

    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")

# Esecuzione dello script
send_email_with_attachment()
