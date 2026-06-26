#--------------------
#LIBRERIAS
#--------------------
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import text
#------------------------
#IMPORTS
#------------------------
from configuraciones.conexion_sql import motor
from core.normalizacion_texto import normalizar_texto

#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def libros(new_page):
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
    await new_page.fill('input[id$="__variable_3_element"]', "8")  # valor fijo
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
    
    import shutil
    from pathlib import Path
    
    # Esperar la descarga
    async with new_page.expect_download(timeout=600_000) as download_info:
        print("Obteniendo archivo, tardará varios segundos...")
        await boton.click()

    download = await download_info.value

    #cerrar ui-window-bar
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo
    
    # Obtener la ruta del archivo descargado por Playwright
    download_path = await download.path()
    print("Archivo descargado en ruta temporal:", download_path)
    
    # Copiarlo a un archivo temporal válido con extensión .xls
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as temp_file:
        shutil.copy(download_path, temp_file.name)
        temp_path = temp_file.name  # Guardar ruta para leer después
    
    # Leer el archivo con pandas
    df = pd.read_csv(temp_path, sep='\t', encoding='utf-8')
    print("Archivo obtenido!!")
    print(df.head())
    
    print("transformando archivo y subiendo archivo")
    
    #EL ARCHIVO TIENE UNA COLUMNA ADICIONAL LLAMADA Unnamed: 12, será eliminada
    df.drop(columns=['Unnamed: 12'], inplace=True)
    titulos = [str(i) for i in range(len(df.columns))]
    df.columns=titulos
    
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
        conn.execute(text("TRUNCATE TABLE PowerStreet.Libros"))#reiniciar conteo de columna id 
        # ✓ Insertar datos
        df.to_sql(
            name='Libros',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            index=False,
            chunksize=500
        )
        print("✅ Datos insertados correctamente.")

        #Eliminar duplicados basándose en Cliente + Orden
        sql_delete_duplicados = text("""
            DELETE L
            FROM PowerStreet.Libros AS L
            JOIN (
                SELECT 
                    Id,
                    ROW_NUMBER() OVER (
                        PARTITION BY Cliente, Orden 
                        ORDER BY Id DESC     
                    ) AS rn
                FROM PowerStreet.Libros
            ) AS x
                ON L.Id = x.Id
            WHERE x.rn > 1;
        """)

        result = conn.execute(sql_delete_duplicados)
        print(f"✅ Se eliminaron {result.rowcount if result.rowcount != -1 else 'un número desconocido de'} registros duplicados por Cliente.")
        conn.execute(text("TRUNCATE TABLE PowerStreet.UX"))