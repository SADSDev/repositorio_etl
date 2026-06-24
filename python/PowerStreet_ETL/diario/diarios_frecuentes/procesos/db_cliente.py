#--------------------
#LIBRERIAS
#--------------------
import os
import shutil
import tempfile
import pandas as pd
from sqlalchemy import text

#------------------------
#IMPORTS
#------------------------
from configuraciones.conexion_sql import motor

from configuraciones.parametros import (
    meses
)

#-----------------
#proceso de reportes de venta diaria
#----------------
async def dbcliente(new_page, fecha_hoy):    
    #Ahora si, conseguir reportes:
    #abriendo busqueda rápida y buscandolo manualmente
    print("obteniendo reporte dbcliente...")
    await new_page.click('div.quicksearch-btn')
    #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
    await new_page.locator('input.search-box-text').wait_for(state='visible')
    #Escribir el nombre del reporte
    await new_page.locator('input.search-box-text').fill("Interfaz")
    #Esperar que aparezcan resultados en el contenedor
    await new_page.locator('div.search-box-results').wait_for(state='visible')
    #Dar clic al primer resultado con tabindex="0"
    await new_page.locator('div.searchbox-item[tabindex="0"]').click()
    
    #Para este reporte no hay ventana de propiedades, es un archivo
    #que se genera en CSV ingresando solo fecha, sin frecuencia, ni agencia.
    #esperar la ventana del reporte y al boton de descarga para descargar
    frame = new_page.frame_locator('iframe[id*="reportView"]')
    btn = frame.locator('button#Ejecutar')
    await btn.wait_for(state='attached')
    await btn.wait_for(state='visible')
    await btn.scroll_into_view_if_needed()
    await new_page.wait_for_timeout(2000)  
    await btn.hover()
    await btn.click()
    
    #esperar ventana "Parámetros" y llenarla
    await new_page.wait_for_selector('ui-window[visible="true"]', timeout=30000)
    await new_page.screenshot(path="debug_hoy.png")
    await new_page.fill('input[id$="_pValue_DFecha_element"]', "")  # limpiar
    await new_page.fill('input[id$="_pValue_DFecha_element"]', str(fecha_hoy))  # valor dinámico o fijo
    await new_page.fill('input[id$="_pValue_HFecha_element"]', "")  # limpiar
    await new_page.fill('input[id$="_pValue_HFecha_element"]', str(fecha_hoy))  # valor dinámico o fijo
    await new_page.wait_for_timeout(1000)  # espera 1 segundo
    #hacer click en boton para ver el reporte
    await new_page.get_by_role("button", name="Ejecutar").click()
    print("descargando archivo")
    
    #esperar descarga del archivo
    async with new_page.expect_download(timeout=240000) as download_info:
        download = await download_info.value
        download_path = await download.path()
    
    #cerrar modal de aviso de descarga exitosa y cerrar la ventana ui del reporte para futuros reportes
    modal = new_page.locator('.modal-content.ui-modal-alert')#esperar a que aparezca
    await modal.wait_for(state="visible", timeout=180000)#esperar a que aparezca
    await modal.locator('.btn-accept').click()
    await new_page.wait_for_timeout(1000)
    await new_page.locator('.ui-window-bar .ui-window-button-close').click()#ya está visible desde que se ejecutó la descarga, no es necesario esperarlo

    # Crear archivo temporal y copiar contenido allí
    temp_fd, temp_path = tempfile.mkstemp(suffix=".txt")
    os.close(temp_fd)  # Cerrar el descriptor de archivo
    
    # Copiar el archivo descargado al archivo temporal
    shutil.copyfile(download_path, temp_path)
        
    # LEER EL ARCHIVO LIMPIO CON PANDAS
    dbcliente = pd.read_csv(temp_path, sep="\t", engine="python")
    print(f"Total de registros procesados: {len(dbcliente)}")
    print(dbcliente.head())
    
    #revisar si archivo esta vacio si es asi, terminar proceso
    if dbcliente.empty:
        print("Sin ventas registradas en este archivo. Proceso terminado.")
        return
    
    print("transformando archivo")
    #TRANSFORMACIÓN DEL DF
    #renombrar nombres de columnas, no necesario, se renombrarán con la tabla de sql
    #agregar columna fecha_proceso como primer columna y llenarla con el valor de "fecha_hoy"
    # Convertir columna Fecha a datetime para poder subirlo a SQL
    dbcliente['Fecha'] = pd.to_datetime(dbcliente['Fecha'], dayfirst=True, errors='coerce')
    
    #crear columna Operacion con ayuda de CATALOGOS.vendedores en SQL
    #Cargar solo las columnas necesarias de CATALOGOS.Vendedores
    consulta = "SELECT Codigo_de_Vendedor, Agencia FROM CATALOGOS.vendedores"
    df_vendedores = pd.read_sql(consulta, motor)
    #Hacer merge usando la columna vendedor de dbcliente con codigo_de_vendedor de CATALOGOS.Vendedores
    dbcliente = dbcliente.merge(
        df_vendedores,
        how='left',
        left_on='Vendedor',
        right_on='Codigo_de_Vendedor'
    )
    #Al hacer merge, en el pandas trae las dos columnas con las que se trabajó en el df externo
    #solo debemos conservar aquella en la que se aplico la consulta de interés
    #en este caso es agencia, pero se le cambiará el nombre por Operacion
    dbcliente.rename(columns={'Agencia': 'Operacion'}, inplace=True)
    dbcliente.drop(columns=['Codigo_de_Vendedor'], inplace=True)
    # Mover columna 'operación' al índice 0
    col = dbcliente.pop('Operacion')# Extrae la columna
    dbcliente.insert(0, 'Operación', col)#tambien cambia Operacion a Operación
    #agregar columna mes y acomodarla despues de la columna Operacion
    dbcliente['Mes'] = dbcliente['Fecha'].dt.month.apply(lambda x: meses[x-1])
    columnas=dbcliente.columns.to_list()
    indice_Operacion= columnas.index('Operación')
    columnas.insert(indice_Operacion + 1,columnas.pop(columnas.index('Mes')))
    dbcliente=dbcliente[columnas]
    #agregar columna Semana y aomodarla despues de la columna Mes 
    dbcliente['Semana'] = dbcliente['Fecha'].dt.isocalendar().week
    columnas=dbcliente.columns.to_list()
    indice_mes= columnas.index('Mes')
    columnas.insert(indice_mes + 1,columnas.pop(columnas.index('Semana')))
    dbcliente=dbcliente[columnas]
    #Agregarcolumna Ruta y acomodarla después de Semana
    dbcliente['NUR'] = dbcliente['NUR'].astype(str)# Asegurar que todos los NUR sean strings
    dbcliente['RUTA']='R'+ dbcliente['NUR'].astype(str).str[-2:]
    columnas=dbcliente.columns.to_list()
    indice_semana= columnas.index('Semana')
    columnas.insert(indice_semana + 1,columnas.pop(columnas.index('RUTA')))
    dbcliente=dbcliente[columnas]        
    #Agregar columna tipo haciendo merge de nuevo con la columna Ruta 
    #Cargar solo las columnas necesarias de CATALOGOS.Vendedores
    consulta = "SELECT Operacion, Codigo_de_Vendedor FROM CATALOGOS.Vendedores"
    df_vendedores = pd.read_sql(consulta, motor)
    #Hacer merge usando la columna vendedor de dbcliente con codigo_de_vendedor de CATALOGOS.Vendedores
    dbcliente = dbcliente.merge(
        df_vendedores,
        how='left',
        left_on='Vendedor',
        right_on='Codigo_de_Vendedor'
    )
    dbcliente.rename(columns={'Operacion': 'Tipo'}, inplace=True)
    dbcliente.drop(columns=['Codigo_de_Vendedor'], inplace=True)
    columnas=dbcliente.columns.to_list()
    indice_semana= columnas.index('Semana')
    columnas.insert(indice_semana + 1,columnas.pop(columnas.index('Tipo')))
    dbcliente=dbcliente[columnas]
    #otro merge para obtener la Familia del articulo según su codigo
    consulta = "SELECT Codigo, Familia FROM CATALOGOS.Articulos"
    df_vendedores = pd.read_sql(consulta, motor)
    dbcliente = dbcliente.merge(
        df_vendedores,
        how='left',
        left_on='Cod. Articulo',
        right_on='Codigo'
    )
    dbcliente.drop(columns=['Codigo'], inplace=True)
    columnas=dbcliente.columns.to_list()
    indice_ruta= columnas.index('RUTA')
    columnas.insert(indice_ruta + 1,columnas.pop(columnas.index('Familia')))
    dbcliente=dbcliente[columnas]
    #Agregar columna cajetilla haciendo merge con la tabla articulos_completos
    consulta = "SELECT Codigo, Unidades FROM CATALOGOS.Articulos_Completos"
    df_vendedores = pd.read_sql(consulta, motor)
    dbcliente = dbcliente.merge(
        df_vendedores,
        how='left',
        left_on='Cod. Articulo',
        right_on='Codigo'
    )
    dbcliente['Cajetillas']=dbcliente['Unidades']*dbcliente['Cantidad']#SE CREA NUEVA COLUMNA MULTIPLICANDO Unidades y Cantidad
    dbcliente.drop(columns=['Codigo','Unidades'], inplace=True)      
    columnas=dbcliente.columns.to_list()
    indice_familia= columnas.index('Familia')
    columnas.insert(indice_familia + 1,columnas.pop(columnas.index('Cajetillas')))
    dbcliente=dbcliente[columnas]
    #Agregar columna de Distribucion, si Cajetilla es mayor o igual a 3
    #entonces se da el valor 1, sino es 0
    #y acomodarla despues de Cajetillas
    dbcliente['Distribucion'] = (dbcliente['Cajetillas'] >= 3).astype(int)
    columnas=dbcliente.columns.to_list()
    indice_cajetillas= columnas.index('Cajetillas')
    columnas.insert(indice_cajetillas + 1,columnas.pop(columnas.index('Distribucion')))
    dbcliente=dbcliente[columnas]
    
    #redondear datos numericos
    dbcliente["Cantidad"]=dbcliente["Cantidad"].round(3)
    dbcliente["Total"]=dbcliente["Total"].round(3)
    
    
    #subir datos a SQL server 
    with motor.begin() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa:", result.scalar(),"Subiendo datos...")

        # Obtener nombres de columnas exactos desde SQL Server en orden
        sql_column_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'PowerStreet' AND TABLE_NAME = 'DB_Cliente'
            ORDER BY ORDINAL_POSITION
        """)
        sql_column_result = conn.execute(sql_column_query).fetchall()
        sql_columns = [row[0] for row in sql_column_result]
        if len(dbcliente.columns) != len(sql_columns):
            raise ValueError(f"❌ El DataFrame tiene {len(dbcliente.columns)} columnas pero la tabla SQL tiene {len(sql_columns)}.")
        dbcliente.columns = sql_columns#renombrar columnas para que sean iguales a las del df
        print("✅ Columnas renombradas correctamente:")

        dbcliente_mov = pd.to_datetime(dbcliente['Fecha'].iloc[0], dayfirst=True).date()

        sql_delete = text("""
            DELETE FROM PowerStreet.DB_Cliente
            WHERE CONVERT(date, Fecha) = :Fecha
        """)
        conn.execute(sql_delete, {'Fecha': dbcliente_mov})
        print(f"✅ Registros con fecha {dbcliente_mov} eliminados.")

        dbcliente.to_sql(
            name='DB_Cliente',
            con=conn,
            schema='PowerStreet',
            if_exists='append',
            chunksize=20,
            method=None,
            index=False
        )
        print("✅ Datos insertados correctamente.")
