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
from PowerStreet_ETL.diario.diarios_frecuentes.core.subirDatosSQL import subir_datos_a_sql
from PowerStreet_ETL.configuraciones.parametros import (desde_agencia, hasta_agencia)

#-----------------------------
#PROCESO
#-----------------------------

async def ito_detallado_descarga(new_page, fecha_hoy):
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte ito al detalle...")
    await new_page.reload(wait_until="networkidle",timeout=240000)
    await new_page.wait_for_timeout(1500)
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda 
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Reporte Cobertura ITO % Geocerca Detalle V2")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al resultado con texto exacto buscado
    await new_page.locator(
        'div.search-box-results > div.searchbox-item'
    ).filter(
        has_text="Reporte Cobertura ITO % Geocerca Detalle"
    ).first.click()
    

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
    await new_page.fill('input[id$="__variable_4_element"]', str(desde_agencia))

    await new_page.fill('input[id$="__variable_5_element"]', "")
    await new_page.fill('input[id$="__variable_5_element"]', str(hasta_agencia))    
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
    df = pd.read_excel(temp_path, engine="openpyxl")
    print(f"Total de registros procesados: {len(df)}")
    print(df.head())
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if df.empty:
        print("Sin registros en este archivo. Proceso terminado.")
        return   
    print("transformando archivo")
    
    #TRANSFORMACIÓN DEL DF
    #llenar lacolumna Dia con la fecha de hoy
    df['Dia'] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
    #LLENAR ESPACIOS EN BLANCO Y "SIN VISITA" CON NULLS
    df = df.replace(["", "SIN VISITA"], np.nan)
    #agregar columna de FechaCarga
    df["FechaCarga"] = pd.Timestamp.now()

    
    return df

def ito_detallado_carga_sql(df: pd.DataFrame, schema:str, tabla:str)-> None:
    #subir datos a SQL server 
    subir_datos_a_sql(df=df,schema=schema, tabla=tabla)
    print(f"datos cargado correctamente en " f"{schema}.{tabla}")
