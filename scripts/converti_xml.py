import os
import subprocess
import shutil
import configparser
from datetime import datetime
import base64
import tempfile
import platform
from asn1crypto import cms, util

class P7MConverter:
    def __init__(self, openssl_path):
        self.openssl_path = openssl_path
        
    def setup_conversion(self, base_dir):
        self.errore_dir = os.path.join(base_dir, "errori")
        self.log_file_path = os.path.join(base_dir, "conversione_log.txt")
        os.makedirs(self.errore_dir, exist_ok=True)

    def log_message(self, message):
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] {message}\n")

    def extract_using_asn1crypto(self, input_file):
        """Tenta di estrarre l'XML usando asn1crypto."""
        try:
            with open(input_file, 'rb') as f:
                content = f.read()
                
            # Prova prima come DER
            try:
                signed_data = cms.ContentInfo.load(content).native['content']
                if 'encap_content_info' in signed_data:
                    xml_content = signed_data['encap_content_info']['content']
                    if isinstance(xml_content, bytes):
                        return xml_content.decode('utf-8', errors='ignore')
            except:
                pass
                
            # Se fallisce, prova come PEM
            try:
                pem_content = base64.b64decode(content)
                signed_data = cms.ContentInfo.load(pem_content).native['content']
                if 'encap_content_info' in signed_data:
                    xml_content = signed_data['encap_content_info']['content']
                    if isinstance(xml_content, bytes):
                        return xml_content.decode('utf-8', errors='ignore')
            except:
                pass
                
            return None
        except Exception as e:
            self.log_message(f"Errore nell'estrazione con asn1crypto: {str(e)}")
            return None

    def try_extract_content(self, input_file):
        """Tenta di estrarre il contenuto usando OpenSSL ASN1parse con parsing migliorato."""
        try:
            cmd = [
                self.openssl_path,
                "asn1parse",
                "-inform", "DER",
                "-in", input_file,
                "-i"  # Aggiunto per una migliore indentazione
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None
                
            lines = result.stdout.split('\n')
            content_lines = []
            xml_started = False
            xml_content = ""
            
            for line in lines:
                if 'OCTET STRING' in line:
                    content = line.split(':')[-1].strip()
                    if '<?xml' in content or '<' in content:
                        xml_started = True
                        xml_content = content
                    elif xml_started:
                        xml_content += content
                elif xml_started and not ('OCTET STRING' in line):
                    xml_started = False
                    if xml_content:
                        content_lines.append(xml_content)
                        xml_content = ""

            if content_lines:
                return '\n'.join(content_lines)
            return None
            
        except Exception as e:
            self.log_message(f"Errore nell'estrazione del contenuto: {str(e)}")
            return None

    def convert_p7m_to_xml(self, directory):
        """Converte i file P7M in XML utilizzando multiple strategie di estrazione."""
        self.setup_conversion(directory)
        
        if not os.path.isdir(directory):
            error_message = f"Errore: la directory '{directory}' non esiste."
            self.log_message(error_message)
            print(error_message)
            return

        converted_count = 0
        error_count = 0

        for file in os.listdir(directory):
            if file.endswith(".p7m"):
                input_file = os.path.join(directory, file)
                output_file = os.path.join(directory, file.replace(".p7m", ".xml"))

                print(f"\nProcesso il file: {file}")
                
                # Prima strategia: usando asn1crypto
                content = self.extract_using_asn1crypto(input_file)
                if content and ('<' in content or '<?xml' in content):
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        os.remove(input_file)
                        converted_count += 1
                        print(f"✓ Conversione riuscita (asn1crypto): {file}")
                        continue
                    except Exception as e:
                        self.log_message(f"Errore nella scrittura del contenuto estratto: {str(e)}")

                # Seconda strategia: usando OpenSSL ASN1parse
                content = self.try_extract_content(input_file)
                if content:
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        os.remove(input_file)
                        converted_count += 1
                        print(f"✓ Conversione riuscita (OpenSSL): {file}")
                        continue
                    except Exception as e:
                        self.log_message(f"Errore nella scrittura del contenuto estratto: {str(e)}")

                # Se entrambe le strategie falliscono
                error_message = f"Nessun metodo di estrazione ha funzionato per {file}"
                self.log_message(error_message)
                shutil.move(input_file, os.path.join(self.errore_dir, file))
                error_count += 1
                print(f"✗ Errore nella conversione: {file}")

        return converted_count, error_count

def find_openssl():
    """Trova il percorso di OpenSSL in modo cross-platform."""
    if platform.system() == 'Windows':
        possible_paths = [
            r'C:\Program Files\OpenSSL-Win64\bin\openssl.exe',
            r'C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe',
            r'C:\OpenSSL-Win64\bin\openssl.exe',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    else:
        # Linux/Mac: cerca nel PATH
        openssl = shutil.which('openssl')
        if openssl:
            return openssl
        # Percorsi comuni Linux
        possible_paths = [
            '/usr/bin/openssl',
            '/usr/local/bin/openssl',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    return None

def main():
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from scripts.parametri_db import get_cartella_emesse, get_cartella_ricevute
        
        cartella_emesse = get_cartella_emesse()
        cartella_ricevute = get_cartella_ricevute()
        
        # Trova OpenSSL in modo cross-platform
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Prova prima dal config, poi cerca automaticamente
        openssl_path = config.get('Parametri', 'openssl_path', fallback=None)
        if not openssl_path or not os.path.exists(openssl_path):
            openssl_path = find_openssl()
        
        if not openssl_path:
            print("ERRORE: OpenSSL non trovato!")
            print("Windows: Installa OpenSSL e configura il percorso in config.ini")
            print("Linux: sudo apt-get install openssl")
            return
        
        print("\nConvertitore P7M -> XML")
        print("-" * 50)
        print(f"OpenSSL Path: {openssl_path}")
        
        converter = P7MConverter(openssl_path)
        
        for directory in [cartella_emesse, cartella_ricevute]:
            if os.path.exists(directory):
                print(f"\nProcesso la cartella: {directory}")
                print("-" * 50)
                converted, errors = converter.convert_p7m_to_xml(directory)
                print(f"\nRiepilogo per {os.path.basename(directory)}:")
                print(f"File convertiti con successo: {converted}")
                print(f"File con errori: {errors}")
            else:
                print(f"\nLa cartella {directory} non esiste.")

        print("\nOperazione completata!")

    except configparser.Error as e:
        print(f"Errore nella lettura del file di configurazione: {str(e)}")
    except Exception as e:
        print(f"Errore imprevisto: {str(e)}")

if __name__ == "__main__":
    main()