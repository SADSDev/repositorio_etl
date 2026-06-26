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
from configuraciones.parametros import (desde_agencia, hasta_agencia)
#-----------------------------
#PROCESO
#-----------------------------
async def fullfillment_pedidos(new_page, fecha_hoy):
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte ito al detalle...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda 
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Reporte Fulfillment PMM")
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
    await new_page.fill('input[id$="__variable_1_element"]', "666126")
    await new_page.wait_for_timeout(1500)

    await new_page.fill('input[id$="__variable_2_element"]', "")
    await new_page.fill('input[id$="__variable_2_element"]', str(desde_agencia))

    await new_page.fill('input[id$="__variable_3_element"]', "")
    await new_page.fill('input[id$="__variable_3_element"]', str(hasta_agencia))    

    await new_page.fill('input[id$="__variable_4_element"]', "")
    await new_page.fill('input[id$="__variable_4_element"]', str(fecha_hoy))
    
    await new_page.fill('input[id$="__variable_5_element"]', "")
    await new_page.fill('input[id$="__variable_5_element"]', str(fecha_hoy))
    await new_page.wait_for_timeout(1500)
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ver").click()

    #esperar la ventana del reporte para descargar
    iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
    frame = await iframe_element.content_frame()
    await frame.wait_for_selector("tr.column-header", timeout=180000)
    print("datos totalmente cargados, listo para descargar")
    
    async with new_page.expect_download(timeout=240000) as download_info:
        await new_page.locator('ui-toolbarbutton[title="Exportar a \'XLS\'"]').click()


    download = await download_info.value
    download_path = await download.path() #espera a que se complete la descarga
    #cerrar ui-window-bar para los siguientes reportes
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()

     
    # Crear archivo temporal y copiar contenido allí
    temp_fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(temp_fd)  # Cerrar el descriptor de archivo
    
    # Copiar el archivo descargado al archivo temporal
    shutil.copyfile(download_path, temp_path)
        
    # LEER EL ARCHIVO LIMPIO CON PANDAS
    fullfillment = pd.read_excel(temp_path, engine="openpyxl")
    print(f"Total de registros procesados: {len(fullfillment)}")
    print(fullfillment.head())
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if fullfillment.empty:
        print("Sin registros en este archivo. Proceso terminado.")
        return   
    print("transformando archivo")
    
    #TRANSFORMACIÓN DEL DF
    #llenar la columna fecha con la fecha de hoy
    fullfillment['Fecha'] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
    #reemplazar todos los "" con nan
    fullfillment = fullfillment.replace([""], np.nan)
    
    
    #subir datos a SQL server 
    with motor.begin() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa:", result.scalar(),"Subiendo datos...")

        # Obtener nombres de columnas exactos desde SQL Server en orden
        sql_column_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = 'Fullfillment_Pedidos_PMM'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(fullfillment.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(fullfillment.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        fullfillment.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        fullfillment_mov = pd.to_datetime(fullfillment['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.Fullfillment_Pedidos_PMM
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {'Fecha': fullfillment_mov})
        print(f"✅ Registros con fecha {fullfillment_mov} eliminados.")

        fullfillment.to_sql(
            name='Fullfillment_Pedidos_PMM',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            chunksize=100,
            method=None,
            index=False
        )
        print("✅ Datos insertados correctamente.")
