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
from PowerStreet_ETL.configuraciones.parametros import agencias

from PowerStreet_ETL.diario.diarios_por_dia.core.subirDatosSQL import subir_datos_a_sql
from PowerStreet_ETL.diario.diarios_por_dia.core.vaciarTablaSQL import vaciar_tabla_sql


#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def universo_descarga(
    new_page: Page,
    fecha_hoy: date
):

    dataframes=[]
    for agencia in (agencias):
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
        await new_page.wait_for_timeout(1500)#espera 1.5 segundo
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
        await new_page.wait_for_timeout(2000)#espera 1.5 segundos
        await new_page.keyboard.press("Tab")
        #hacer click en boton para ver el reporte
        await new_page.get_by_role("button", name="Ver").click()

        # 1. Esperar el contenedor del reporte
        contenedor = new_page.locator('ui-window:has(.ui-window-title:text("Universo de clientes Excel"))')
        await contenedor.wait_for(state="visible", timeout=30_000)
        # 2. Acceder al iframe
        iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
        frame = await iframe_element.content_frame()
        # 3. Esperar el botón Generar Archivo
        boton = frame.locator('button:has-text("Generar Archivo")')
        await boton.wait_for(state="visible", timeout=30_000)
        await boton.scroll_into_view_if_needed()
        await boton.hover()
        print("datos totalmente cargados, listo para descargar") 
        # 4. Esperar 1.5 segundos
        await new_page.wait_for_timeout(1500)
        # 5. Generar y descargar el archivo
        async with new_page.expect_download(timeout=800_000) as download_info:
            await new_page.wait_for_timeout(1500)#espera 1.5 segundos
            await boton.click()
            print("Obteniendo archivo, este podría tardar varios minutos...")
        download = await download_info.value
        download_path = await download.path()
        print(f"Reporte descargado: {download_path}")
            

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

        # 6. Cerrar el contenedor y recargar página
        await contenedor.locator(
            ".ui-window-button-close"
        ).click()
        await new_page.reload()
        await new_page.wait_for_load_state("networkidle", timeout=240000)


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
