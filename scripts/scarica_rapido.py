import subprocess
import os
from datetime import datetime

from parametri_db import aggiorna_parametri

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

# Aggiorna il campo 'aggiornamento' nel database
data_odierna = datetime.now().strftime("%d/%m/%Y")
aggiorna_parametri(aggiornamento=data_odierna)

print("Operazioni completate e parametri nel database aggiornati.")