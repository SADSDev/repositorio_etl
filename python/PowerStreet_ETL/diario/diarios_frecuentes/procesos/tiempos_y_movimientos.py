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

from configuraciones.parametros import (
    meses,
    dias
)

#-----------------------------------
#PROCESO
#-----------------------------------
async def tiempos(new_page,fecha_hoy):
    #Ahora si, conseguir reportes:
    #tiempos y movimientos---------------------------------------------
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte de tiempos y movimientos...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Detalle de Vendedores en PDV por Agencia")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al primer resultado con tabindex="0"
    await new_page.locator('div.searchbox-item[tabindex="0"]').click()
    
    #esperar ventana "propiedades" por si las moscas xd
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.wait_for_selector('text="Propiedades"', timeout=30000)

    # Esperar que el label de "Agencia" esté presente (más confiable que ID directo)
    #este es el unico label que hay que esperar, cuando se carga este, todo
    #lo demás está cargado
    #nunca se cambia este campo, siempre es el mismo
    await new_page.wait_for_selector('div:has-text("Agencia")')
    # Llenar campo Agencia (input tipo number)
    
    await new_page.fill('input[id$="__variable_2_element"]', "")  # limpiarpiar
    await new_page.fill('input[id$="__variable_2_element"]', "8")  # valor fijo
    await new_page.wait_for_timeout(1000)#espera 1 segundo
    # Llenar campo Fecha (input tipo text con fecha ISO)
    
    await new_page.fill('input[id$="__variable_3_element"]', "")  # limpiar
    await new_page.fill('input[id$="__variable_3_element"]', str(fecha_hoy))  # valor dinámico o fijo
    # Esperar un momento a que la web procese los cambios antes de hacer clic
    await new_page.wait_for_timeout(1000)  # espera 1 segundo
    
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ver").click()
    
    #esperar la ventana del reporte para descargar
    iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
    frame = await iframe_element.content_frame()
    await frame.wait_for_selector("tr.column-header")
    
    print("datos totalmente cargados, listo para descargar")
    
    
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

    columnas_esperadas = 25 #esto lo sabemos viendo manualmente el archivo, son la cantidad de columnas
    col_direccion = 6  #"Direccion" es la columna 7, pero el conteo empieza desde 0
        
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
    tiempos_y_mov = pd.read_csv(temp_path, encoding="utf-8-sig")
    print(f"Total de registros procesados: {len(tiempos_y_mov)}")
    print("transformando archivo")
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if tiempos_y_mov.empty:
        print("Sin ventas registradas en este archivo. Proceso terminado.")
        return
    
    #TRANSFORMACIÓN DEL DF
    #renombrar nombres de columnas, no necesario, se renombrarán con la tabla de sql
    #agregar columna fecha_proceso como primer columna y llenarla con el valor de "fecha_hoy"
    # Convertir string a objeto datetime
    fecha_hoy_dt = datetime.strptime(fecha_hoy, "%d-%m-%Y")
    fecha_hoy_nueva = fecha_hoy_dt.strftime("%d/%m/%Y")
    tiempos_y_mov.insert(0,'fecha_proceso', fecha_hoy_nueva)#inserta nueva columna en el lugar 1
    #crear columna Ruta
    tiempos_y_mov['Ruta'] = tiempos_y_mov.iloc[:, 1].astype(str).str.extract(r'(R\d{2})')
    #mover columna ruta al inicio extrayendola en una variable y luego insertandola de nuevo
    ruta = tiempos_y_mov.pop('Ruta')
    tiempos_y_mov.insert(0, 'Ruta', ruta)
    #crear columna de Hora_inicio
    tiempos_y_mov['Hora_inicio'] = tiempos_y_mov['Fecha'].astype(str).str.extract(r'(\d{2}:\d{2})')#extract busca cierto patron dado en el paréntesis, leyendo de izquierda a derecha
    #obtener indice de columna "fecha_proceso" para insertar despues de ella la columna Hora
    columnas=tiempos_y_mov.columns.to_list()#crear indice de columnas del df
    indice_fecha_proceso= columnas.index('fecha_proceso')#obtener indice de la columna llamada fecha_proceso
    columnas.insert(indice_fecha_proceso + 1,columnas.pop(columnas.index('Hora_inicio')))
    tiempos_y_mov=tiempos_y_mov[columnas]
    #Crear columna Hora_fin e insertarla después de Hora_inicio
    tiempos_y_mov['Hora_fin'] = tiempos_y_mov['Hora de Final<br> de Visita'].astype(str).str.extract(r'(\d{2}:\d{2})')
    columnas=tiempos_y_mov.columns.to_list()
    indice_hora_inicio= columnas.index('Hora_inicio')
    columnas.insert(indice_hora_inicio + 1,columnas.pop(columnas.index('Hora_fin')))
    tiempos_y_mov=tiempos_y_mov[columnas]
    #Agregar columna de dia_visita y acomodarla después de hora_fin
    #transformar los valores de fecha a date time para operaciones, solo una vez
    tiempos_y_mov['fecha_proceso'] = pd.to_datetime(tiempos_y_mov['fecha_proceso'], format='%d/%m/%Y')
    #Usando dayofweek (Lunes=0, Domingo=6)
    tiempos_y_mov['dia_visita'] = tiempos_y_mov['fecha_proceso'].dt.dayofweek.apply(lambda x: dias[x])
    columnas=tiempos_y_mov.columns.to_list()
    indice_hora_fin= columnas.index('Hora_fin')
    columnas.insert(indice_hora_fin + 1,columnas.pop(columnas.index('dia_visita')))
    tiempos_y_mov=tiempos_y_mov[columnas]
    #agregar columna mes y acomodarla despues de la columna dia_visita
    tiempos_y_mov['mes'] = tiempos_y_mov['fecha_proceso'].dt.month.apply(lambda x: meses[x-1])
    columnas=tiempos_y_mov.columns.to_list()
    indice_dia_visita= columnas.index('dia_visita')
    columnas.insert(indice_dia_visita + 1,columnas.pop(columnas.index('mes')))
    tiempos_y_mov=tiempos_y_mov[columnas]
    #agregar columna semana y aomodarla despues de la columna mes 
    tiempos_y_mov['semana'] = tiempos_y_mov['fecha_proceso'].dt.isocalendar().week
    columnas=tiempos_y_mov.columns.to_list()
    indice_mes= columnas.index('mes')
    columnas.insert(indice_mes + 1,columnas.pop(columnas.index('semana')))
    tiempos_y_mov=tiempos_y_mov[columnas]
    
    #ajustar a date tiem columnas de hora
    tiempos_y_mov['Hora_inicio'] = tiempos_y_mov['Hora_inicio'].apply(
        lambda x: datetime.strptime(x, '%H:%M').time() if isinstance(x, str) else x
    )
    tiempos_y_mov['Hora_fin'] = tiempos_y_mov['Hora_fin'].apply(
        lambda x: datetime.strptime(x, '%H:%M').time() if isinstance(x, str) else x
    )     
    # Reemplazar '??' por 'o' en la columna 'Liquidaci??n'
    tiempos_y_mov['Liquidaci??n'] = tiempos_y_mov['Liquidaci??n'].str.replace('??', 'o', regex=False)
    # Eliminar columnas inútiles
    columnas_a_eliminar = [tiempos_y_mov.columns[i] for i in [9, 16, 17]]  # indice de columnas a eliminar
    tiempos_y_mov = tiempos_y_mov.drop(columns=columnas_a_eliminar)
    
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
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = 'Tiempos_y_Mov'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(tiempos_y_mov.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(tiempos_y_mov.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        tiempos_y_mov.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        fecha_tiempos_y_mov = pd.to_datetime(tiempos_y_mov['Fecha_visita'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.Tiempos_y_Mov
            WHERE CONVERT(date, Fecha_visita) = :Fecha_visita
        """)
        conn.execute(sql_delete, {'Fecha_visita': fecha_tiempos_y_mov})
        print(f"✅ Registros con fecha {fecha_tiempos_y_mov} eliminados.")

        tiempos_y_mov.to_sql(
            name='Tiempos_y_Mov',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            index=False
        )
        print("✅ Datos insertados correctamente.")