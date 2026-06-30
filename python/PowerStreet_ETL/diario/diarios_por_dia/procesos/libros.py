#--------------------
#LIBRERIAS
#--------------------
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import text
import asyncio
import shutil
#------------------------
#IMPORTS
#------------------------
from configuraciones.conexion_sql import motor
from core.normalizacion_texto import normalizar_texto
from configuraciones.parametros import desde_agencia, hasta_agencia 

#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def libros(new_page):
    #vaciar primero toda la tabla de libros 
    with motor.begin() as conn:
        conn.execute(text("""
            TRUNCATE TABLE PowerStreet.Libros
        """))
    print("✅ Tabla Libros vaciada.")

    for agencia in range(desde_agencia, hasta_agencia+1):
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
        await new_page.wait_for_timeout(1000)#espera 1 segundo
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
        print("Archivo descargado en ruta temporal:", download_path)

        # Copiarlo a un temporal
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as temp_file:
            shutil.copy(download_path, temp_file.name)
            temp_path = temp_file.name

        # Leer archivo
        df = pd.read_csv(
            temp_path,
            header=None,
            sep="\t",
            encoding="utf-8"
        )

        print("Archivo obtenido!!")
        print(df.head())

        print("transformando archivo y subiendo archivo")
        
        #TRANSFORMACION DEL DF
        #eliminar columnas "unnamed"
        df = df.dropna(axis=1, how="all")
        # Convierte cadenas vacías o con solo espacios a NaN
        df = df.replace(r'^\s*$', np.nan, regex=True)
        titulos = [str(i) for i in range(len(df.columns))]
        df.columns=titulos

        """
        #Ruta en Windows para guardar pruebas de df
        ruta_salida = r"D:\Descargas\resultado_Libros.xlsx"
        # Escribir a Excel para revisar resultados
        df.to_excel(ruta_salida, index=False)
        print(f"Archivo guardado en: {ruta_salida}")
        """

        #conectar a SQL y subir datos
        df=df.applymap(normalizar_texto)#normalizar texto del df principal
        #probar que la conexión sea exitosa e insertar datos
        #también verifica si los datos con la fecha ya existen
        with motor.begin() as conn:
            # ✓ Probar conexión
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexión exitosa:", result.scalar())

            # ✓ Obtener columnas reales de SQL, EXCLUYENDO LA COLUMNA ID
            sql_column_query = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'PowerStreet' 
                AND TABLE_NAME = 'Libros'
                AND COLUMNPROPERTY(OBJECT_ID('PowerStreet.Libros'), COLUMN_NAME, 'IsIdentity') = 0
                ORDER BY ORDINAL_POSITION;
            """)
            sql_column_result = conn.execute(sql_column_query).fetchall()
            sql_columns = [row[0] for row in sql_column_result]

            if len(df.columns) != len(sql_columns):
                raise ValueError(f"❌ El DataFrame tiene {len(df.columns)} columnas "
                                f"pero la tabla SQL tiene {len(sql_columns)}.")

            df.columns = sql_columns
            print("✅ Columnas renombradas correctamente.") 
            #Insertar datos
            df.to_sql(
                name='Libros',
                con=conn,
                schema='PowerStreet',
                if_exists='append',
                index=False,
                chunksize=500
            )
            print("✅ Datos insertados correctamente.")
