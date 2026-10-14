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
from core.subirDatosSQL import subir_datos_a_sql
from configuraciones.parametros import (desde_agencia, hasta_agencia)
#-----------------------------
#PROCESO
#-----------------------------
async def encuestas_supervisor_descarga(new_page, fecha_hoy):
    await new_page.reload(wait_until="networkidle",timeout=240000)
    await new_page.wait_for_timeout(1500)
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte encestas por supervisor...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda 
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Reporte de Encuestas")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al resultado con texto exacto buscado
    await new_page.locator(
        'div.search-box-results > div.searchbox-item'
    ).filter(
        has_text="Reporte de Encuestas"
    ).first.click()

    #esperar ventana "propiedades"
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.wait_for_selector('text="Propiedades"', timeout=30000)
    
    #primer elemento a llenar "distribuidor"
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

    # 1. Esperar el contenedor del reporte
    contenedor = new_page.locator('ui-window:has(.ui-window-title:text("Reporte de Encuestas"))')
    await contenedor.wait_for(state="visible", timeout=30_000)
    # 2. Acceder al iframe
    frame = contenedor.frame_locator("iframe")
    # 3. Esperar el botón Generar Archivo
    boton = frame.locator("#Ejecutar")
    await boton.wait_for(state="visible", timeout=30_000)
    # 4. Esperar 1.5 segundos
    await new_page.wait_for_timeout(1500)
    # 5. Generar y descargar el archivo
    async with new_page.expect_download(timeout=600_000) as download_info:
        print("Generando y descargando reporte de encuestas...")
        await boton.click()
    download = await download_info.value
    download_path = await download.path()
    print(f"Reporte descargado: {download_path}")
    # 6. Cerrar el contenedor
    await contenedor.locator(
        ".ui-window-button-close"
    ).click()


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
    if df.empty or (
        "NUR" in df.columns
        and df["NUR"].astype(str).str.strip().eq("TOTALES").all()
    ):
        print("El reporte no contiene registros de detalle.")
        return  
    print("transformando archivo")
    
    #TRANSFORMACIÓN DEL DF
    #llenar la columna fecha con la fecha de hoy
    df['Fecha'] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
    #relllenar caracteres faltantes de codigo de cliente con 0
    df["Codigo"] = df["Codigo"].astype(str).str.zfill(10)
    #Eliminar fila de TOTALES
    df = df[df["NUR"] != "TOTALES"].copy()
    #ordenar columnas y quitar columnas innecesarias
    df=df[["Fecha","Supervisor", "NUR", "Codigo", "Cliente",
        "TipoVisita", "ConVendedor", "SinVendedor"
    ]]

    return df

def encuestas_supervisor_carga_sql(df: pd.DataFrame, schema:str, tabla:str)-> None:
    #llamar a funcion de subida de datos a sql
    subir_datos_a_sql(df=df, schema=schema, tabla=tabla)
    print(f"datos cargado correctamente en " f"{schema}.{tabla}")