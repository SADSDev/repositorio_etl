#--------------------
#LIBRERIAS
#--------------------
import tempfile
from pathlib import Path
import pandas as pd
from sqlalchemy import text
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
async def universo(new_page, fecha_hoy):
    #vaciar primero toda la tabla de catalogos 
    with motor.begin() as conn:
        conn.execute(text("""
            TRUNCATE TABLE PowerStreet.Universo_Clientes
        """))
    print("✅ Tabla Universo_Clientes vaciada.")

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
        await new_page.wait_for_timeout(1000)#espera 1 segundo
        
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
        print("Archivo descargado en ruta temporal:", download_path)
        
        #cerrar ui-window-bar
        await new_page.wait_for_timeout(1000)
        await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo
        await new_page.reload()

        # Copiarlo a un archivo temporal válido con extensión .xls
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as temp_file:
            shutil.copy(download_path, temp_file.name)
            temp_path = temp_file.name  # Guardar ruta para leer después
        
        # Leer el archivo con pandas
        df = pd.read_excel(temp_path, engine="openpyxl")
        print("Archivo obtenido!!")
        print(df.head())

        if df.empty:
            print("Sin registros de cliente en esta agencia. Pasando a la siguiente.")
            continue   
        print("transformando archivo")
        
        #TRANSFORMACIÓN DF
        #eliminar columnas "unnamed"
        df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]
        #relllenar caracteres faltantes de codigo_gln con 0
        df["Codigo GLN"] = df["Codigo GLN"].astype(str).str.zfill(10)
        #agregar columna de fecha de actualizacion y colocarla despues de Codigo pwst
        df["Fecha_Actualizacion"] = pd.to_datetime(fecha_hoy, dayfirst=True, errors='coerce')
        columnas=df.columns.to_list()
        indice_fecha= columnas.index('Codigo Pwst')
        columnas.insert(indice_fecha + 1,columnas.pop(columnas.index('Fecha_Actualizacion')))
        df=df[columnas]
        #detectar duplicados y quedarse con el que contenga más info
        df["score"] = df[columnas].notna().sum(axis=1)
        df = ( df.sort_values("score", ascending=False) 
                .drop_duplicates("Codigo GLN", keep="first")
                .drop(columns="score") )
        """
        #Ruta absoluta en Windows para guardar pruebas de df
        ruta_salida = r"D:\Descargas\resultado_UX.xlsx"
        # Escribir a Excel para revisar resultados
        df.to_excel(ruta_salida, index=False)
        print(f"Archivo guardado en: {ruta_salida}")
        """

        #conectar a SQL y subir datos
        #también verifica si los datos con la fecha ya existen
        with motor.begin() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexión exitosa:", result.scalar())

            #Obtener columnas reales de SQL, EXCLUYENDO LA COLUMNA ID
            sql_column_query = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'PowerStreet' 
                AND TABLE_NAME = 'Universo_Clientes'
                ORDER BY ORDINAL_POSITION;
            """)
            sql_column_result = conn.execute(sql_column_query).fetchall()
            sql_columns = [row[0] for row in sql_column_result]

            if len(df.columns) != len(sql_columns):
                raise ValueError(f"❌ El DataFrame tiene {len(df.columns)} columnas "
                                f"pero la tabla SQL tiene {len(sql_columns)}.")

            df.columns = sql_columns
            print("✅ Columnas renombradas correctamente.")

            #subir datos 
            df.to_sql(
                name='Universo_Clientes',
                con=conn,
                schema='PowerStreet',
                if_exists='append',
                index=False,
                chunksize=500
            )
            print("✅ Datos insertados correctamente.")


            