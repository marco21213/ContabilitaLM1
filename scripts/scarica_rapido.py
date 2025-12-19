import subprocess
import os
from datetime import datetime

from parametri_db import aggiorna_parametri

# Ottieni il percorso della directory corrente dello script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Trova la root del progetto (directory che contiene config.ini)
project_root = os.path.dirname(script_dir)  # Risale dalla cartella scripts alla root
if not os.path.exists(os.path.join(project_root, "config.ini")):
    # Se non trovato, prova nella directory corrente
    project_root = os.getcwd()

# Usa il percorso padre se necessario
scripts_path = os.path.join(project_root, "scripts")

# Verifica l'esistenza del percorso
if not os.path.exists(scripts_path):
    scripts_path = os.path.join(script_dir, "scripts")

print(f"Esecuzione script dalla directory: {project_root}")
print(f"Percorso scripts: {scripts_path}")

# Esegui gli script con la directory di lavoro corretta
print("\n=== Esecuzione speed_download.py ===")
subprocess.run(
    ["python", os.path.join(scripts_path, "speed_download.py")],
    cwd=project_root,
    check=False
)

print("\n=== Esecuzione scarfec32.py ===")
subprocess.run(
    ["python", os.path.join(scripts_path, "scarfec32.py")],
    cwd=project_root,
    check=False
)

print("\n=== Esecuzione rinomina.py ===")
subprocess.run(
    ["python", os.path.join(scripts_path, "rinomina.py")],
    cwd=project_root,
    check=False
)

# Aggiorna il campo 'aggiornamento' nel database
print("\n=== Aggiornamento data aggiornamento ===")
data_odierna = datetime.now().strftime("%d/%m/%Y")
config_path = os.path.join(project_root, "config.ini")
aggiorna_parametri(aggiornamento=data_odierna, config_path=config_path)
print(f"Data aggiornamento impostata a: {data_odierna}")

print("\n✓ Operazioni completate e parametri nel database aggiornati.")