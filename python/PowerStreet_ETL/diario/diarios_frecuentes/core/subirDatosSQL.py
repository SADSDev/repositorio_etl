#subir datos a SQL server 

#------------------
#LIBRERIAS
#---------------------
from sqlalchemy import text
import pandas as pd

#--------------------------
#IMPORTS
#-------------------------
from configuraciones.conexion_sql import motor

#--------------------------------------------
#Proceso de subida de datos
#--------------------------------------------
def subir_datos_a_sql(df: pd.DataFrame,
    schema: str,
    tabla: str)-> pd.DataFrame:
    with motor.begin() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa:", result.scalar(),"Subiendo datos...")

        # Obtener nombres de columnas exactos desde SQL Server en orden
        sql_column_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tabla
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(
            sql_column_query,
            dict(schema=schema, tabla=tabla)
        ).fetchall()        
        sql_columns = [row[0] for row in sql_column_result]
        if len(df.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(df.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        df.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        df_mov = pd.to_datetime(df['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text(f"""
            DELETE FROM {schema}.{tabla}
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {"Fecha": df_mov})
        print(f"✅ Registros con fecha {df_mov} eliminados.")

        df.to_sql(
            name=tabla,
            con=conn,
            schema=schema,
            if_exists='append',
            chunksize=20,
            method=None,
            index=False
        )
        print("✅ Datos insertados correctamente.")