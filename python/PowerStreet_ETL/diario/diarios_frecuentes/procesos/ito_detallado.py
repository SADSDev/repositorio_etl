#--------------------
#LIBRERIAS
#--------------------
import os
import shutil
import tempfile
import pandas as pd
from sqlalchemy import text
import numpy as np
#------------------------
#IMPORTS
#------------------------
from configuraciones.conexion_sql import motor

#-----------------------------
#PROCESO
#-----------------------------

async def ito_detallado(new_page, fecha_hoy):
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte ito al detalle...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda 
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Reporte Cobertura ITO % Geocerca Detalle")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al primer resultado con tabindex="0"
    await new_page.locator('div.searchbox-item[tabindex="0"]').click()
    


    #esperar ventana "propiedades"
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.wait_for_selector('text="Propiedades"', timeout=30000)
    # Esperar que el label de "Agencia" esté presente (más confiable que ID directo)
    #este es el unico label que hay que esperar, cuando se carga este, todo
    #lo demás está cargado
    #nunca se cambia este campo, siempre es el mismo
    await new_page.wait_for_selector('div:has-text("Distribuidor")')
    # Llenar campos de propiedades (input tipo number)
    await new_page.fill('input[id$="__variable_1_element"]', "")
    await new_page.fill('input[id$="__variable_1_element"]', str(fecha_hoy))
    
    await new_page.fill('input[id$="__variable_2_element"]', "")
    await new_page.fill('input[id$="__variable_2_element"]', str(fecha_hoy))

    await new_page.fill('input[id$="__variable_3_element"]', "")
    await new_page.fill('input[id$="__variable_3_element"]', "666126")
    await new_page.wait_for_timeout(1500)
    
    await new_page.fill('input[id$="__variable_4_element"]', "")
    await new_page.fill('input[id$="__variable_4_element"]', "8")

    await new_page.fill('input[id$="__variable_5_element"]', "")
    await new_page.fill('input[id$="__variable_5_element"]', "8")    
    await new_page.wait_for_timeout(1500)
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ver").click()

    #esperar la ventana del reporte y al boton de descarga para descargar
    frame = new_page.frame_locator('iframe[id*="reportView"]')
    btn = frame.locator('button#Ejecutar')
    await btn.wait_for(state='attached')
    await btn.wait_for(state='visible')
    await btn.scroll_into_view_if_needed()
    await new_page.wait_for_timeout(2000)  
    await btn.hover()
    await btn.click()
    print("descargando archivo")
    
    #esperar descarga del archivo
    async with new_page.expect_download(timeout=240000) as download_info:
        download = await download_info.value
        download_path = await download.path()
    
    #cerrar ui-window-bar para los siguientes reportes
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()

    # Crear archivo temporal y copiar contenido allí
    temp_fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(temp_fd)  # Cerrar el descriptor de archivo
    
    # Copiar el archivo descargado al archivo temporal
    shutil.copyfile(download_path, temp_path)
        
    # LEER EL ARCHIVO LIMPIO CON PANDAS
    itodetallado = pd.read_excel(temp_path, engine="openpyxl")
    print(f"Total de registros procesados: {len(itodetallado)}")
    print(itodetallado.head())
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if itodetallado.empty:
        print("Sin registros en este archivo. Proceso terminado.")
        return   
    print("transformando archivo")
    
    #TRANSFORMACIÓN DEL DF
    #Eliminar columnas que no se necesitarán
    itodetallado=itodetallado.drop(columns=["CLO"])
    #Cambiar la agencia a solo el numero
    itodetallado['Agencia']=itodetallado['Agencia'].str[:1]
    #transformar columna nur a ruta
    itodetallado['NUR']="R"+itodetallado['NUR'].str[-2:]
    #cambir la columna de vendedor a solo su clave
    itodetallado['Vendedor']=itodetallado['Vendedor'].str[:4]
    #llenar lacolumna Dia con la fecha de hoy
    itodetallado['Dia'] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
    #LLENAR ESPACIOS EN BLANCO Y "SIN VISITA" CON NULLS
    itodetallado = itodetallado.replace(["", "SIN VISITA"], np.nan)
    
    #subir datos a SQL server 
    with motor.begin() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa:", result.scalar(),"Subiendo datos...")

        # Obtener nombres de columnas exactos desde SQL Server en orden
        sql_column_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = 'ITO_Detallado'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(itodetallado.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(itodetallado.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        itodetallado.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        itodetallado_mov = pd.to_datetime(itodetallado['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.ITO_Detallado
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {'Fecha': itodetallado_mov})
        print(f"✅ Registros con fecha {itodetallado_mov} eliminados.")

        itodetallado.to_sql(
            name='ITO_Detallado',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            chunksize=100,
            method=None,
            index=False
        )
        print("✅ Datos insertados correctamente.")