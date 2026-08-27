#--------------------
#LIBRERIAS
#--------------------
import os
import shutil
import tempfile
import pandas as pd
from sqlalchemy import text

#------------------------
#IMPORTS
#------------------------
from configuraciones.conexion_sql import motor

from core.subirDatosSQL import subir_datos_a_sql

#-----------------
#proceso de reportes de venta diaria
#----------------
async def ventas_descarga(new_page, fecha_hoy):    
    #Ahora si, conseguir reportes:
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte de venta diaria...")
    await new_page.reload(wait_until="networkidle",timeout=240000)
    await new_page.wait_for_timeout(1500)
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Interfaz")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al primer resultado con tabindex="0"
    await new_page.locator('div.searchbox-item[tabindex="0"]').click()
    
    #Para este reporte no hay ventana de propiedades, es un archivo
    #que se genera en CSV ingresando solo fecha, sin frecuencia, ni agencia.
    #esperar la ventana del reporte y al boton de descarga para descargar
    frame = new_page.frame_locator('iframe[id*="reportView"]')
    btn = frame.locator('button#Ejecutar')
    await btn.wait_for(state='attached')
    await btn.wait_for(state='visible')
    await btn.scroll_into_view_if_needed()
    await new_page.wait_for_timeout(2000)  
    await btn.hover()
    await btn.click()
    
    #esperar ventana "Parámetros" y llenarla
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.fill('input[id$="_pValue_DFecha_element"]', "")  # limpiar
    await new_page.fill('input[id$="_pValue_DFecha_element"]', str(fecha_hoy))  # valor dinámico o fijo
    await new_page.fill('input[id$="_pValue_HFecha_element"]', "")  # limpiar
    await new_page.fill('input[id$="_pValue_HFecha_element"]', str(fecha_hoy))  # valor dinámico o fijo
    await new_page.wait_for_timeout(1000)  # espera 1 segundo
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ejecutar").click()
    print("descargando archivo")
    
    #esperar descarga del archivo
    async with new_page.expect_download(timeout=240000) as download_info:
        download = await download_info.value
        download_path = await download.path()
    
    #cerrar modal de aviso de descarga exitosa y cerrar la ventana ui del reporte para futuros reportes
    modal = new_page.locator('.modal-content.ui-modal-alert')#esperar a que aparezca
    await modal.wait_for(state="visible", timeout=180000)#esperar a que aparezca
    await modal.locator('.btn-accept').click()
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo

    # Crear archivo temporal y copiar contenido allí
    temp_fd, temp_path = tempfile.mkstemp(suffix=".txt")
    os.close(temp_fd)  # Cerrar el descriptor de archivo
    
    # Copiar el archivo descargado al archivo temporal
    shutil.copyfile(download_path, temp_path)
        
    # LEER EL ARCHIVO LIMPIO CON PANDAS
    df = pd.read_csv(temp_path, sep="\t", engine="python")
    print(f"Total de registros procesados: {len(df)}")
    print(df.head())
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if df.empty:
        print("Sin ventas registradas en este archivo. Proceso terminado.")
        return
    
    print("transformando archivo")
    #TRANSFORMACIÓN DEL DF
    # Convertir columna Fecha a datetime para poder subirlo a SQL
    df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
    #redondear datos numericos
    df["Cantidad"]=df["Cantidad"].round(3)
    df["Total"]=df["Total"].round(3)

    df_final=df
    return df_final
    
def ventas_carga_sql(df: pd.DataFrame, schema:str, tabla:str)-> None:
    #subir datos a SQL server 
    subir_datos_a_sql(df=df,schema=schema, tabla=tabla)
    print(f"datos cargado correctamente en " f"{schema}.{tabla}")