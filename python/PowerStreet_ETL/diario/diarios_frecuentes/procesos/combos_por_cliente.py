#----------------------------------------
#LIBRERIAS
#----------------------------------------
import os
import csv
import shutil
import tempfile
import pandas as pd
from datetime import datetime
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from core.subirDatosSQL import subir_datos_a_sql
from configuraciones.conexion_sql import motor
from configuraciones.parametros import (desde_agencia, hasta_agencia)
#-----------------------------------
#PROCESO
#-----------------------------------
async def combos_por_cliente_descarga(new_page,fecha_hoy):

    dataframes=[]
    await new_page.reload(wait_until="networkidle",timeout=240000)
    for agencia in range(desde_agencia, hasta_agencia+1):
        #Ahora si, conseguir reportes:
        #tiempos y movimientos---------------------------------------------
        #abriendo busqueda rápida y buscandolo manualmente
        print(f"obteniendo reporte de combosXcliente de la agencia {agencia}")
        await new_page.wait_for_timeout(1500)
        await new_page.click('div.quicksearch-btn')
        #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
        await new_page.locator('input.search-box-text').wait_for(state='visible')
        #Escribir el nombre del reporte
        await new_page.locator('input.search-box-text').fill("Combos x cliente")
        #Esperar que aparezcan resultados en el contenedors
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
        
        await new_page.fill('input[id$="__variable_3_element"]', "")
        await new_page.fill('input[id$="__variable_3_element"]', str(fecha_hoy))

        await new_page.fill('input[id$="__variable_4_element"]', "")
        await new_page.fill('input[id$="__variable_4_element"]', str(fecha_hoy))
        
        await new_page.fill('input[id$="__variable_2_element"]', "")
        await new_page.fill('input[id$="__variable_2_element"]', "8")
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
        df_i = pd.read_excel(temp_path, engine="openpyxl")
        print(f"Total de registros procesados: {len(df_i)}")
        print(df_i.head())
    
        print("transformando archivo y subiendo archivo...")        
        
        #revisar si archivo esta vacio si es asi, terminar proceso
        if df_i.empty:
            print("Sin combos registradas en este archivo. Proceso terminado.")
            return        
        
        #Transformación del df_i
        #agregar columna Fecha
        fecha_hoy_date = datetime.strptime(fecha_hoy, "%d-%m-%Y").date()
        df_i.insert(0, "Fecha", fecha_hoy_date)

        dataframes.append(df_i)

    if not dataframes:
                return pd.DataFrame()
        
    df_final = pd.concat(dataframes, ignore_index=True)

    return df_final
    

def combos_por_cliente_carga_sql(df: pd.DataFrame, schema:str, tabla:str)-> None:    
    #subir datos a SQL server 
    subir_datos_a_sql(df=df,schema=schema, tabla=tabla)
    print(f"datos cargado correctamente en " f"{schema}.{tabla}") 
