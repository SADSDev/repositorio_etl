#--------------------
#LIBRERIAS
#--------------------
import asyncio

import numpy as np
import pandas as pd
from datetime import date
from playwright.async_api import Page
#------------------------
#IMPORTS
#------------------------
from configuraciones.parametros import (
    desde_agencia,
    hasta_agencia
)

from core.subirDatosSQL import subir_datos_a_sql
from core.vaciarTablaSQL import vaciar_tabla_sql


#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def universo_descarga(
    new_page: Page,
    fecha_hoy: date
):

    dataframes=[]
    for agencia in range(desde_agencia, hasta_agencia+1):
        print(f"obteniendo universo de agencia {agencia}")
        #abriendo busqueda rápida y buscandolo manualmente
        await new_page.click('div.quicksearch-btn')
        #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
        await new_page.locator('input.search-box-text').wait_for(state='visible')
        #Escribir el nombre del reporte
        await new_page.locator('input.search-box-text').fill("Universo de Clientes Excel")
        #Esperar que aparezcan resultados en el contenedors
        await new_page.locator('div.search-box-results').wait_for(state='visible')
        #Dar clic al primer resultado con tabindex="0"
        await new_page.locator('div.searchbox-item[tabindex="0"]').click()
        
        #esperar ventana "propiedades"
        await new_page.wait_for_selector('text="Propiedades"', timeout=30000)

        # Esperar que el label de "Agencia" esté presente (más confiable que ID directo)
        #este es el unico label que hay que esperar, cuando se carga este, todo
        #lo demás está cargado
        #nunca se cambia este campo, siempre es el mismo
        await new_page.wait_for_selector('div:has-text("Agencia")')
        
        # Llenar campo Agencia (input tipo number)
        await new_page.fill('input[id$="__variable_2_element"]', "")  # limpiarpiar
        await new_page.fill('input[id$="__variable_2_element"]', str(agencia))  # valor fijo
        await new_page.wait_for_timeout(2000)#espera 1 segundo
        await new_page.keyboard.press("Tab")
        
        #hacer click en boton para ver el reporte
        await new_page.get_by_role("button", name="Ver").click()
        
        #esperar la ventana del reporte para descargar
        iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
        frame = await iframe_element.content_frame()
        boton = frame.locator('button:has-text("Generar Archivo")')
        await boton.wait_for(state='visible', timeout=30000)
        await boton.scroll_into_view_if_needed()
        await boton.hover()
        print("datos totalmente cargados, listo para descargar")

        
        # Esperar la descarga
        async with new_page.expect_download(timeout=600_000) as download_info:
            print("Obteniendo archivo, este podría tardar varios minutos...")
            await new_page.wait_for_timeout(1500)#espera 1.5 segundos
            await boton.click()

        download = await download_info.value

        #Obtener la ruta del archivo descargado por Playwright
        download_path = await download.path()
        
        #cerrar ui-window-bar
        await new_page.wait_for_timeout(1000)
        await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo
        await new_page.reload()
        await new_page.wait_for_load_state("networkidle", timeout=240000)

        # Leer el archivo con pandas
        df_i = pd.read_csv(download_path, sep='\t', encoding='utf-8')
        print("Archivo obtenido!!")
        print(df_i.head())

        if df_i.empty:
            print("Sin registros de cliente en esta agencia. Pasando a la siguiente.")
            continue   
        print("transformando archivo")
        
        #TRANSFORMACIÓN df_i
        #eliminar columnas "unnamed"
        df_i = df_i.loc[:, ~df_i.columns.str.contains(r"^Unnamed")]
        #relllenar caracteres faltantes de codigo_gln con 0
        df_i["Codigo GLN"] = df_i["Codigo GLN"].astype(str).str.zfill(10)
        #agregar columna de fecha de actualizacion y colocarla despues de Codigo pwst
        df_i["Fecha_Actualizacion"] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
        columnas=df_i.columns.to_list()
        indice_fecha= columnas.index('Codigo Pwst')
        columnas.insert(indice_fecha + 1,columnas.pop(columnas.index('Fecha_Actualizacion')))
        df_i=df_i[columnas]
        #detectar duplicados y quedarse con el que contenga más info
        df_i["score"] = df_i[columnas].notna().sum(axis=1)
        df_i = ( df_i.sort_values("score", ascending=False) 
                .drop_duplicates("Codigo GLN", keep="first")
                .drop(columns="score") )
        dataframes.append(df_i)

    if not dataframes:
        return pd.DataFrame()

    df_final = pd.concat(dataframes, ignore_index=True)

    return df_final

def universo_carga_sql(
    df: pd.DataFrame,
    schema: str,
    tabla: str
) -> None:

    if df is None or df.empty:
        raise RuntimeError(
            "El DataFrame de Universo está vacío. "
            "No se vaciará ni cargará la tabla."
        )

    vaciar_tabla_sql(schema=schema, tabla=tabla)

    subir_datos_a_sql(df=df,schema=schema, tabla=tabla)

    print(f"Universo cargado correctamente en "f"{schema}.{tabla}.")    