import subprocess
import sys

def run(cmd_list):
    subprocess.check_call(cmd_list)

print("Actualizando pip...")
run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

print("Instalando librerías...")
run([sys.executable, "-m", "pip", "install", "-r", "requisitos.txt"])

print("Instalando navegadores de Playwright...")
run(["playwright", "install"])

print("✅Entorno listo")
