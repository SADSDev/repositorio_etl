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
from configuraciones.parametros import agencias

from core.normalizacion_texto import normalizar_texto
from core.subirDatosSQL import subir_datos_a_sql
from core.vaciarTablaSQL import vaciar_tabla_sql


#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def libros_descarga(
    new_page: Page,
    fecha_hoy: date
):


    dataframes = []
    for agencia in (agencias):
        print(f"obteniendo Libro de rutas de agencia {agencia}")
        #Ahora si, conseguir reportes:
        #libros---------------------------------------------
        #abriendo busqueda rápida y buscandolo manualmente
        print("obteniendo Libro de rutas...")
        await new_page.click('div.quicksearch-btn')
        #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
        await new_page.locator('input.search-box-text').wait_for(state='visible')
        #Escribir el nombre del reporte
        await new_page.locator('input.search-box-text').fill("Libro de rutas excel")
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
        await new_page.wait_for_selector('div:has-text("Distribuidor")')
        
        # Llenar campo Agencia (input tipo number)
        await new_page.fill('input[id$="__variable_3_element"]', "")  # limpiarpiar
        await new_page.fill('input[id$="__variable_3_element"]', str(agencia))  # valor fijo
        await new_page.wait_for_timeout(2000)#espera 1 segundo
        await new_page.keyboard.press("Tab")
        #hacer click en boton para ver el reporte
        await new_page.get_by_role("button", name="Ver").click()
        
        
        #esperar la ventana del reporte para descargar
        iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
        frame = await iframe_element.content_frame()
        boton = frame.locator('button:has-text("Generar Archivo")')
        await boton.wait_for(state='visible')
        await boton.scroll_into_view_if_needed()
        await boton.hover()    
        print("datos totalmente cargados, listo para descargar")
        
        print("Obteniendo archivo, tardará varios minutos...")
        # Preparar ambas esperas ANTES del clic
        #tarea de descarga
        download_task = asyncio.create_task(
            new_page.wait_for_event("download", timeout=600_000)
        )
        #tarea por si aparece el modal
        modal_task = asyncio.create_task(
            new_page.wait_for_selector(
                "div.modal-content.ui-modal-alert",
                state="visible",
                timeout=600_000
            )
        )
        await new_page.wait_for_timeout(1500)
        await boton.click()

        # Esperar el primer evento que ocurra
        done, pending = await asyncio.wait(
            {download_task, modal_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        # ==========================
        # CASO 1: NO HAY DATOS
        # ==========================
        if modal_task in done:

            print(f"La agencia {agencia} no tiene libro de rutas.")

            # Cancelar la espera de descarga
            download_task.cancel()

            # Cerrar el modal
            await new_page.locator("button.btn-accept").click()

            # Cerrar la ventana del reporte
            await new_page.locator('.ui-window-bar .ui-window-button-close').click()

            # Recargar para dejar limpia la página
            await new_page.wait_for_timeout(1500)
            await new_page.reload()
            await new_page.wait_for_load_state("networkidle", timeout=240000)

            continue

        # ==========================
        # CASO 2: HUBO DESCARGA
        # ==========================
        modal_task.cancel()

        download = await download_task

        # Cerrar la ventana del reporte
        await new_page.wait_for_timeout(1000)
        await new_page.locator('.ui-window-bar .ui-window-button-close').click()

        await new_page.reload()
        await new_page.wait_for_load_state("networkidle", timeout=240000)

        # Obtener ruta del archivo descargado
        download_path = await download.path()

        if download_path is None:
            raise RuntimeError(
                f"No se pudo obtener el archivo "
                f"de la agencia {agencia}."
            )

        # Leer archivo
        df_i = pd.read_csv(
            download_path,
            header=None,
            sep="\t",
            encoding="utf-8"
        )

        print("Archivo obtenido!!")
        print("transformando archivo y subiendo archivo")
        
        #TRANSFORMACION DEL df_i
        #eliminar columnas "unnamed"
        df_i = df_i.dropna(axis=1, how="all")
        # Convierte cadenas vacías o con solo espacios a NaN
        df_i = df_i.replace(r'^\s*$', np.nan, regex=True)
        #pasa primer fila como titulos de columnas
        titulos = [str(i) for i in range(len(df_i.columns))]
        df_i.columns=titulos
        #agregar columna de fecha de actualizacion y colocarla después de Orden
        df_i.insert(4, "Fecha_Actualizacion", pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce'))
        #agregar columna de agencia y agregarla como primer columna
        df_i.insert(0, "Agencia", agencia)
        
        print(df_i.head())
        dataframes.append(df_i)

    if not dataframes:
        return pd.DataFrame()

    
    df_final = pd.concat(dataframes, ignore_index=True)

    #df_final.to_excel("libro_rutas.xlsx", index=False)
    return df_final

def libros_carga_sql(
    df: pd.DataFrame,
    schema: str,
    tabla: str
) -> None:

    if df is None or df.empty:
        raise RuntimeError(
            "El DataFrame de Libros está vacío. "
            "No se vaciará ni cargará la tabla."
        )

    vaciar_tabla_sql(schema=schema, tabla=tabla)

    subir_datos_a_sql(df=df, schema=schema, tabla=tabla)

    print( f"Libros cargado correctamente en " f"{schema}.{tabla}.")