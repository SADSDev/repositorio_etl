#----------------------------------------
#LIBRERIAS
#----------------------------------------
import os
import csv
import re
import tempfile
import shutil
import pandas as pd
from datetime import datetime
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from core.subirDatosSQL import subir_datos_a_sql
from configuraciones.parametros import desde_agencia, hasta_agencia

#-----------------------------------
#PROCESO
#-----------------------------------
async def indicadores(new_page,fecha_hoy):
    for agencia in range(desde_agencia, hasta_agencia+1):
        #Ahora si, conseguir reportes:
        #tiempos y movimientos---------------------------------------------
        #abriendo busqueda rápida y buscandolo manualmente
        print(f"obteniendo reporte de indicadores de la agencia {agencia}")
        await new_page.click('div.quicksearch-btn')
        #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
        await new_page.locator('input.search-box-text').wait_for(state='visible')
        #Escribir el nombre del reporte
        await new_page.locator('input.search-box-text').fill("Seguimiento indicadores DZ - NUR")
        #Esperar que aparezcan resultados en el contenedors
        await new_page.locator('div.search-box-results').wait_for(state='visible')
        #Dar clic al primer resultado con tabindex="0"
        await new_page.locator('div.searchbox-item[tabindex="0"]').first.click()
        
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
        await new_page.fill('input[id$="__variable_2_element"]', str(agencia))

        await new_page.fill('input[id$="__variable_3_element"]', "")
        await new_page.fill('input[id$="__variable_3_element"]', "PM01")
        await new_page.wait_for_timeout(1500)

        await new_page.fill('input[id$="__variable_4_element"]', "")
        await new_page.fill('input[id$="__variable_4_element"]', "PM01")
        
        await new_page.fill('input[id$="__variable_5_element"]', "")
        await new_page.fill('input[id$="__variable_5_element"]', str(fecha_hoy))

        await new_page.fill('input[id$="__variable_6_element"]', "")
        await new_page.fill('input[id$="__variable_6_element"]', str(fecha_hoy))
        await new_page.wait_for_timeout(1500)
        
        #hacer click en boton para ver el reporte
        await new_page.get_by_role("button", name="Ver").click()
        
        
        #esperar la ventana del reporte para descargar
        iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
        frame = await iframe_element.content_frame()
        await frame.wait_for_selector("tr.column-header", timeout=180000)
        
        print("datos totalmente cargados, listo para descargar")
        
        # Esperar el inicio de la descarga
        async with new_page.expect_download(timeout=240000) as download_info:
            await new_page.locator('ui-toolbarbutton[title="Exportar a \'CSV\'"]').click()

        download = await download_info.value
        download_path = await download.path() #espera a que se complete la descarga

        #cerrar ui-window-bar
        await new_page.wait_for_timeout(1000)
        await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo

        # Crear archivo temporal reparado
        temp_fd, temp_path = tempfile.mkstemp(suffix=".csv")
        os.close(temp_fd)

        #copiar archivo temporal
        shutil.copyfile(download_path, temp_path)

        # LEER EL ARCHIVO LIMPIO CON PANDAS
        df = pd.read_csv(temp_path, encoding="utf-8-sig")
        print(df.head(10))
        print("transformando archivo y subiendo archivo...")        
        
        #revisar si archivo esta vacio si es asi, terminar proceso
        if df.empty:
            print(f"sin registros de indicadores en la agencia {agencia}, pasando a la sig...")
            continue        
        
        #TRANSFORMACION DEL DF
        #agregar columna Fecha y colocarla después de Agencia
        df['Fecha']=pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
        columnas=df.columns.to_list()
        indice_fecha= columnas.index('Agencia')
        columnas.insert(indice_fecha + 1,columnas.pop(columnas.index('Fecha')))
        df=df[columnas]
        #redondear todas las columnas numericas
        cols_num = df.select_dtypes(include="number").columns
        df[cols_num] = df[cols_num].round(2)
     
        
        #subir datos a SQL server 
        subir_datos_a_sql(df,schema='PowerStreet', tabla='Seguimiento_Indicadores')