#----------------------------------------
#LIBRERIAS
#----------------------------------------
import os
import tempfile
import numpy as np
import pandas as pd
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from configuraciones.conexion_sql import motor

#-----------------------------------
#PROCESO
#-----------------------------------
async def cp(new_page,fecha_hoy):
    #Ahora si, conseguir reportes:
    #tiempos y movimientos---------------------------------------------
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte 1c1p...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Listado y estatus de Ordenes por Fecha V3.0")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al primer resultado con tabindex="0"
    await new_page.locator('div.searchbox-item[tabindex="0"]').click()
    
    #esperar ventana "propiedades" 
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.wait_for_selector('text="Propiedades"', timeout=30000)

    # Esperar que el label de "Distribuidor" esté presente (más confiable que ID directo)
    #este es el unico label que hay que esperar, cuando se carga este, todo
    #lo demás está cargado
    #nunca se cambia este campo, siempre es el mismo
    await new_page.wait_for_selector('div:has-text("Distribuidor")')
    # Llenar campos de Agencias (input tipo number)

    await new_page.fill('input[id$="__variable_2_element"]', "")  # limpiarpiar
    await new_page.fill('input[id$="__variable_2_element"]', "8")  # valor fijo
    await new_page.fill('input[id$="__variable_3_element"]', "")  
    await new_page.fill('input[id$="__variable_3_element"]', "8")
    await new_page.wait_for_timeout(1000)#espera 1 segundo
    # Llenar campos de Fecha (input tipo text con fecha ISO)

    await new_page.fill('input[id$="__variable_4_element"]', "")  # limpiar
    await new_page.fill('input[id$="__variable_4_element"]', str(fecha_hoy))  # valor dinámico o fijo
    await new_page.fill('input[id$="__variable_5_element"]', "")  
    await new_page.fill('input[id$="__variable_5_element"]', str(fecha_hoy))  # valor dinámico o fijo
    # Esperar un momento a que la web procese los cambios antes de hacer clic
    await new_page.wait_for_timeout(1000)  # espera 1 segundo
    
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ver").click()
    
    
    #esperar la ventana del reporte para descargar
    iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
    frame = await iframe_element.content_frame()
    await frame.wait_for_selector("tr.column-header", timeout=180000)
    
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

    # LEER EL ARCHIVO LIMPIO CON PANDAS
    cp = pd.read_csv(path, encoding="utf-8-sig")
    print(f"Total de registros procesados: {len(cp)}")
    print(cp.head())
    print("transformando archivo")
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if cp.empty:
        print("Sin cp registrados en este archivo. Proceso terminado.")
        return
    
    #TRANSFORMACIÓN DEL DF
    #Agregar columna de porcentaje con condicion de manejo de errores
    #insertarla en el primer lugar del df
    cp['porcentaje'] = np.where(
        (cp['Total<br>Paquetes<br>Pedido'] == 0) | (cp['Total<br>Paquetes<br>Pedido'].isna()),
        0,
        cp['Total<br>Paquetes<br>Entregado'] / cp['Total<br>Paquetes<br>Pedido']
    )
    cp['porcentaje']=cp['porcentaje'].round(4)
    cp.insert(0, 'porcentaje', cp.pop('porcentaje'))
    #convertir columna Fecha a date tiem para pasar a SQL 
    cp['Fecha'] = pd.to_datetime(cp['Fecha'], dayfirst=True, errors='coerce')
    #limpiar columna status documento y status pedido para dejar caracteres simples
    cp['Status documento'] = cp['Status documento'].str.extract(r'<b>(.*?)</b>')#extrae lo que esta entre los caracteres <b>""<b>
    cp['Status pedido'] = cp['Status pedido'].str.extract(r'<b>(.*?)</b>')
    #limpiar columna de motivo de rechazo
    cp['Motivo<br>Rechazo'] = cp['Motivo<br>Rechazo'].where(cp['Motivo<br>Rechazo'].isnull(), cp['Motivo<br>Rechazo'].astype(str).str.replace('??', 'Ó', regex=False))
    cp["Motivo<br>Rechazo"] = cp["Motivo<br>Rechazo"].replace('', 'NA')

    #redondear columnas con valor float para poder subirlas a SQL
    float_cols = cp.select_dtypes(include='float')
    cp[float_cols.columns] = float_cols.round(4)

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
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = '1c1p'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(cp.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(cp)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        cp.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        fecha_cp = pd.to_datetime(cp['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.[1c1p]
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {'Fecha': fecha_cp})
        print(f"✅ Registros con fecha {fecha_cp} eliminados.")

        cp.to_sql(
            name='1c1p',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            index=False
        )
        print("✅ Datos insertados correctamente.")
