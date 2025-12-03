import subprocess
import os
from configparser import ConfigParser
from datetime import datetime

# Ottieni il percorso della directory corrente dello script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Usa il percorso padre se necessario
scripts_path = os.path.join(os.path.dirname(script_dir), "scripts")

# Verifica l'esistenza del percorso
if not os.path.exists(scripts_path):
    scripts_path = os.path.join(script_dir, "scripts")

# Esegui gli script
subprocess.run(["python", os.path.join(scripts_path, "speed_download.py")])
subprocess.run(["python", os.path.join(scripts_path, "scarfec32.py")])
subprocess.run(["python", os.path.join(scripts_path, "rinomina.py")])

# Resto del codice invariato
config_path = "config.ini"
config = ConfigParser()
config.read(config_path)

data_odierna = datetime.now().strftime("%d/%m/%Y")
if 'Profilo' not in config:
    config.add_section('Profilo')
config['Profilo']['aggiornamento'] = data_odierna

with open(config_path, "w") as config_file:
    config.write(config_file)

print("Operazioni completate e file config.ini aggiornato.")