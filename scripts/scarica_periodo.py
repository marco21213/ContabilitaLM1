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
subprocess.run(["python", os.path.join(scripts_path, "scarfec32.py")])
subprocess.run(["python", os.path.join(scripts_path, "rinomina.py"), "--no-stampa"])

print("PORCA BESTIA, IL DOWNLOAD E ANDATO A BUON FINE.")