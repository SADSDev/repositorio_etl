#-----------------------------------------------------------------------
#LIBRERIAS
#-----------------------------------------------------------------------
import os
from pathlib import Path
from dotenv import load_dotenv


ruta_env = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=ruta_env)
#--------------------------------------------------------------
#PARAMETROS
#--------------------------------------------------------------
def variable_obligatoria(nombre: str) -> str:
    valor = os.getenv(nombre)

    if valor is None or valor == "":
        raise RuntimeError(
            f"No existe la variable de entorno obligatoria: {nombre}"
        )

    return valor

# PowerStreet
usuariops = variable_obligatoria("USERPS")
contraseñaps = variable_obligatoria("PASSWORDPS")
urlpowerstreet = variable_obligatoria("URLPOWERSTREET")


# SQL Server
servidor = variable_obligatoria("SERVER")
bd = variable_obligatoria("DATABASE")
usuario = variable_obligatoria("USER")
contraseña = variable_obligatoria("PASSWORD")
schema = variable_obligatoria("SCHEMA")


# Agencias
try:
    desde_agencia = int(variable_obligatoria("DESDEAGENCIA"))
    hasta_agencia = int(variable_obligatoria("HASTAAGENCIA"))

    excluir_agencias = [
        int(x) for x in os.getenv("EXCLUIR_AGENCIAS", "").split(",")
        if x.strip()
    ]

    agencias = [
        agencia
        for agencia in range(desde_agencia, hasta_agencia + 1)
        if agencia not in excluir_agencias
    ]

except ValueError as error:
    raise RuntimeError(
        "DESDEAGENCIA y HASTAAGENCIA deben ser números enteros."
    ) from error

if desde_agencia > hasta_agencia:
    raise RuntimeError(
        "DESDEAGENCIA no puede ser mayor que HASTAAGENCIA."
    )