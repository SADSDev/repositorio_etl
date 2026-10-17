#vaciar tablas de sql antes de subir datos

#-------------------------------------------
#LIBRERIAS
#-------------------------------------------
from sqlalchemy import text
import pandas as pd

#--------------------------
#IMPORTS
#-------------------------
from configuraciones.conexion_sql import motor

#--------------------------------------------
#Proceso de subida de datos
#--------------------------------------------
def vaciar_tabla_sql(schema: str, tabla: str):
    with motor.begin() as conn:
        conn.execute(text(f"""
            DELETE FROM {schema}.{tabla}
        """))

    print(f"✅ Tabla {schema}.{tabla} vaciada.")
