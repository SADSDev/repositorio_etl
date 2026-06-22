#----------------------------------------
#LIBRERIAS
#----------------------------------------
import os
import csv
import tempfile
import pandas as pd
from datetime import datetime
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from configuraciones.conexion_sql import motor

#-----------------------------------
#PROCESO
#-----------------------------------
async def combos(new_page,fecha_hoy):
    #Ahora si, conseguir reportes:
    #tiempos y movimientos---------------------------------------------
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte de combos")
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
    
    # Esperar el inicio de la descarga
    async with new_page.expect_download(timeout=240000) as download_info:
        await new_page.locator('ui-toolbarbutton[title="Exportar a \'CSV\'"]').click()

    download = await download_info.value
    path = await download.path() #espera a que se complete la descarga

    #cerrar ui-window-bar
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo

    # Crear archivo temporal reparado
    temp_fd, temp_path = tempfile.mkstemp(suffix=".csv")
    os.close(temp_fd)

    columnas_esperadas = 9 #esto lo sabemos viendo manualmente el archivo, son la cantidad de columnas
    col_direccion = 2  #"Direccion" es la columna 7, pero el conteo empieza desde 0

    # REPARACIÓN DE CSV
    with open(path, encoding="utf-8-sig") as infile, open(temp_path, "w", newline='', encoding="utf-8-sig") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for i, row in enumerate(reader):
            if i == 0:
                writer.writerow(row)
                continue

            if len(row) == columnas_esperadas:
                writer.writerow(row)
            elif len(row) > columnas_esperadas:
                exceso = len(row) - columnas_esperadas
                direccion = row[col_direccion]
                for _ in range(exceso):
                    direccion += ',' + row.pop(col_direccion + 1)
                row[col_direccion] = direccion
                writer.writerow(row)
            else:
                print(f"[!] Línea {i+1} con columnas insuficientes ({len(row)}). Omitida.")

    # LEER EL ARCHIVO LIMPIO CON PANDAS
    df = pd.read_csv(temp_path, encoding="utf-8-sig")
    print(f"Total de registros procesados: {len(df)}")
    print("transformando archivo y subiendo archivo...")        
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if df.empty:
        print("Sin combos registradas en este archivo. Proceso terminado.")
        return        
    
    #Transformación del df
    #agregar columna Fecha
    fecha_hoy_date = datetime.strptime(fecha_hoy, "%d-%m-%Y").date()
    df.insert(0, "Fecha", fecha_hoy_date)
    
    #Agregar columna de Vendedor haciendo merge con CATALOGOS.Vendedores[Nur]
    #crear columna Operacion con ayuda de CATALOGOS.vendedores en SQL
    #Cargar solo las columnas necesarias de CATALOGOS.Vendedores
    consulta = "SELECT Codigo_de_Vendedor, Nur FROM CATALOGOS.vendedores"
    df_vendedores = pd.read_sql(consulta, motor)
    #Haciendo el merge:
    df = df.merge(
        df_vendedores,
        how='left',
        left_on='NUR',
        right_on='Nur'
    )
    #Eliminatr columna traida de la tabla de CATALOGOS, "Nur"
    df.drop(columns=['Nur'], inplace=True)
    #reacomodar COLUMNA"Codigo_de_Vendedor" despues de "Fecha"
    columnas=df.columns.to_list()
    indice_Fecha= columnas.index('Fecha')
    columnas.insert(indice_Fecha + 1,columnas.pop(columnas.index('Codigo_de_Vendedor')))
    df=df[columnas]
    
    
    #conectar a SQL y subir datos
    #probar que la conexión sea exitosa e insertar datos
    #también verifica si los datos con la fecha ya existen
    with motor.begin() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa:", result.scalar())

        # Obtener nombres de columnas exactos desde SQL Server en orden
        sql_column_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = 'Combos'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(df.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(df.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        df.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")
        
        #eliminar clientes duplicados
        fecha_df = pd.to_datetime(df['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.Combos
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {'Fecha': fecha_df})
        print(f"✅ Registros con fecha {fecha_df} eliminados.")
    
        
    with motor.begin() as conn:
        df.to_sql(
            name='Combos',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            index=False,
            chunksize=20,
            method=None
        )
        print("✅ Datos insertados correctamente.")
        
    #fin
