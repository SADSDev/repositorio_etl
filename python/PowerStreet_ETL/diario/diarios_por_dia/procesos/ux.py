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
from configuraciones.parametros import desde_agencia

#-----------------
#proceso de reporte de Universo Global de clientes
#----------------
async def ux(new_page):
        
        #Ahora si, conseguir reportes:
        #tiempos y movimientos---------------------------------------------
        #abriendo busqueda rápida y buscandolo manualmente
        print("obteniendo Catalogo UX...")
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
        await new_page.fill('input[id$="__variable_2_element"]', str(desde_agencia))  # valor fijo
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

        import shutil
        from pathlib import Path
        
        # Esperar la descarga
        async with new_page.expect_download(timeout=600_000) as download_info:
            print("Obteniendo archivo, este podría tardar varios minutos...")
            await boton.click()

        download = await download_info.value

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
        
        #OBTENCION DEL REPORTE SECUNDARIO, "Clientes con perfil de crédito"
        print("obteniendo perfiles de crédito...")
        await new_page.click('span.ui-window-button-close')
        await new_page.wait_for_timeout(2000)
        await new_page.click('div.quicksearch-btn')
        #Esperar a que aparezca la barra de búsqueda (opcional pero recomendable)
        await new_page.locator('input.search-box-text').wait_for(state='visible')
        #Escribir el nombre del reporte
        await new_page.locator('input.search-box-text').fill("Clientes con perfil crédito")
        #Esperar que aparezcan resultados en el contenedors
        await new_page.locator('div.search-box-results').wait_for(state='visible')
        #Dar clic al resultado que contenga el nombre exacto del reporte buscado
        await new_page.locator('div.searchbox-item', has_text="Reportes SODISA").click()
        
        #esperar ventana "propiedades"
        await new_page.wait_for_selector('text="Propiedades"', timeout=30000)

        # Esperar que el label de "Agencia" esté presente (más confiable que ID directo)
        #este es el unico label que hay que esperar, cuando se carga este, todo
        #lo demás está cargado
        #nunca se cambia este campo, siempre es el mismo
        await new_page.wait_for_selector('div:has-text("Desde Agencia")')
        
        # Llenar campos "Desde Agencia" y "hasta Agencia" (input tipo number)
        await new_page.fill('input[id$="__variable_2_element"]', "")  # limpiar
        await new_page.fill('input[id$="__variable_2_element"]', "8")  # valor fijo
        await new_page.fill('input[id$="__variable_3_element"]', "")  # limpiar
        await new_page.fill('input[id$="__variable_3_element"]', "8")  # valor fijo
        await new_page.wait_for_timeout(1000)#espera 1 segundo
        
        #hacer click en boton para ver el reporte
        await new_page.get_by_role("button", name="Ver").click()
        
        
        #esperar la ventana del reporte para descargar
        iframe_element = await new_page.wait_for_selector('iframe[id*="reportView"]')
        frame = await iframe_element.content_frame()
        await frame.wait_for_selector(
            'table.report-data-table',
            timeout=90000
        )


        
        print("datos totalmente cargados, listo para descargar documento auxiliar")

        import shutil
        from pathlib import Path
        
        async with new_page.expect_download() as download_info:
            await new_page.locator('ui-toolbarbutton[title="Exportar a \'CSV\'"]').click()
        print("descarga iniciada")

        #este df no requiere ninguna reparación o proceso antes de la lectura del archivo
        #por lo que se puede descargar directamente
        download = await download_info.value
        path = await download.path() #espera a que se complete la descarga
        print("descarga completa")

        df2 = pd.read_csv(
            path,
            sep=",",
            encoding="utf-8",
            engine="python",
            on_bad_lines="skip"
        )
        print("Archivo obtenido!!")
        #convertir columnas string a numero
        df2['Limite de<BR>Credito'] = pd.to_numeric(df2['Limite de<BR>Credito'], errors='coerce')
        df2['Limite de<BR>Credito'] = df2['Limite de<BR>Credito'].round(0)
        df2['Linea de<BR>Credito asignado'] = pd.to_numeric(df2['Linea de<BR>Credito asignado'], errors='coerce')
        df2['Linea de<BR>Credito asignado'] = df2['Linea de<BR>Credito asignado'].round(0)
        #reemplazar caracteres especiales
        df2['Potencial'] = df2['Potencial'].str.replace('Cr\?\?dito', 'Credito', regex=True)
        df2['Potencial'] = df2['Potencial'].str.replace('d\?\?as', 'dias', regex=True)
        df2['Telefono'] = df2['Telefono'].str.replace('Cr\?\?dito', 'Credito', regex=True)
        df2['Telefono'] = df2['Telefono'].str.replace('d\?\?as', 'dias', regex=True)
        df2['Colonia'] = df2['Colonia'].str.replace('Cr\?\?dito', 'Credito', regex=True)
        df2['Colonia'] = df2['Colonia'].str.replace('d\?\?as', 'dias', regex=True)
        #reemplazar registros de limite de credito=0 con registros de linea de credito asignado
        df2.loc[df2['Limite de<BR>Credito'] == 0,'Limite de<BR>Credito'] = df2.loc[df2['Limite de<BR>Credito'] == 0,'Linea de<BR>Credito asignado']
        #reemplazar registros de limite de credito que contienen Alguna letra alfabetica(la que sea) con registros de "Perfil"
        df2.loc[df2['Limite de<BR>Credito'].astype(str).str.contains('[A-Za-z]', na=False), 'Limite de<BR>Credito'] = df2.loc[df2['Limite de<BR>Credito'].astype(str).str.contains('[A-Za-z]', na=False), 'Perfil']
        #reemplazar registros de limite de credito cuyos registros en "linea de credito asignado" esten vacios(na) con los registros de "Perfil"
        df2.loc[df2['Linea de<BR>Credito asignado'].isna(), 'Limite de<BR>Credito'] = df2.loc[df2['Linea de<BR>Credito asignado'].isna(), 'Perfil']
        #reemplazar registros de telefono que no contengan la palabra credito con con los registros de "Potencial" 
        df2.loc[~df2['Telefono'].str.contains('Credito', case=False, na=False), 'Telefono'] = df2.loc[~df2['Telefono'].str.contains('Credito', case=False, na=False), 'Potencial']    
        #reemplazar los registros de Telefono cuyos registros en "linea de credito asignado" sean na con los registros de Colonia
        df2.loc[df2['Linea de<BR>Credito asignado'].isna(), 'Telefono'] = df2.loc[df2['Linea de<BR>Credito asignado'].isna(), 'Colonia']
        #rremplazar los registros de telefono cuyos registros en Colonia contengan la palabra "credito"
        df2.loc[df2['Colonia'].astype(str).str.contains('credito', case=False, na=False), 'Telefono'] = df2.loc[df2['Colonia'].astype(str).str.contains('credito', case=False, na=False), 'Colonia']
        #reemplazar filas de registros de clientes con credito 0 para que su codigo de cliente coincida con la columna corresp
        df2.loc[df2['Agencia'].str.len() < 10, 'Agencia'] = df2.loc[df2['Agencia'].str.len() < 10, 'Rutas']
        print(f"✓ Reemplazados registros de Codigo de cliente con valores de Rutas")
        #borrar columnas que no ocuparemos,este df2 solo se usará parahacer un join   
        df2 = df2[['Agencia','C??digo<BR>Usuario', 'Telefono','Potencial', 'Limite de<BR>Credito']]
        print(df2.columns.tolist())
        print(df2.head())
        
        #hay algunos registros en la columna agencia que siguen sin tener el id del cliente,
        #usaremos la columna 'C??digo<BR>Usuario' que contiene la dirección de los clientes problema para hacer un join
        #de dirección-cliente y poder conseguir todos los id
        #funcion normalizadora de textos


        with motor.begin() as conn:
            # Obtener el mapeo de direcciones a códigos
            sql_query = text("""
                SELECT Codigo_GLN, Direccion
                FROM PowerStreet.UX
                WHERE Direccion IS NOT NULL
            """)
            
            result = conn.execute(sql_query)
            # Convertir resultado a DataFrame
            df_direcciones = pd.DataFrame(result.fetchall(), columns=['Codigo_GLN', 'Direccion'])
        
        df2['C??digo<BR>Usuario'] = df2['C??digo<BR>Usuario'].apply(normalizar_texto)
        df_direcciones['Direccion'] = df_direcciones['Direccion'].apply(normalizar_texto)
        #merge
        df2_completo = pd.merge(
            df2,
            df_direcciones,
            left_on='C??digo<BR>Usuario',
            right_on='Direccion',
            how='left',  # LEFT JOIN para mantener todos los registros de df2
            indicator=True
        )
        #limpieza final del df2
        #cuando la columna codigo_gln no este vacia, copiar esos valores a la columna agencia
        df2_completo.loc[df2_completo['Codigo_GLN'].notna(), 'Agencia'] = df2_completo.loc[df2_completo['Codigo_GLN'].notna(), 'Codigo_GLN']
        
        df2_completo.loc[~df2_completo['Potencial'].str.contains('credito', case=False, na=False),'Potencial'] = np.nan
        #aqui se van a modificar dos registros especificos de clientes que no tenian id al descargar el archivo
        #inicial y por lo tanto se tuvieron que buscar sus id de forma manual
        df2_completo.loc[df2_completo['Agencia'].str.contains('ABARROTES LAS TORRES', case=False, na=False),'Agencia'] = 'VDZ0011538'
        df2_completo.loc[df2_completo['Agencia'].str.contains('ABARROTES EMY', case=False, na=False),'Agencia'] = 'MKD7350745'
        #BORRAR COLUMNAS INUTILES Y pasar una vez mas la columna limite de credito a numero 
        df2_completo = df2_completo[['Agencia','Telefono', 'Limite de<BR>Credito']]
        df2_completo['Limite de<BR>Credito'] = pd.to_numeric(df2_completo['Limite de<BR>Credito'], errors='coerce')
        df2_completo['Limite de<BR>Credito'] = df2_completo['Limite de<BR>Credito'].round(0)
        #las columnas en df2_completo se llaman igual que en el df, se cambiarán los nombres para evitar confusiones
        df2_completo = df2_completo.rename(columns={'Agencia': 'Agenciadf2','Telefono':'tipo_de_credito','Limite de<BR>Credito':'linea'})

        # Ruta absoluta en Windows para guardar pruebas de df2_completo
        #ruta_salida = r"C:\Users\Usuario\Downloads\resultado2.xlsx"
        #df2_completo.to_excel(ruta_salida, index=False)
        #print(f"Archivo guardado en: {ruta_salida}")

        #TRANSFORMACION DEL ARCHIVO del ux
        print("transformando archivo y subiendo archivo")
        #EL ARCHIVO TIENE UNA COLUMNA ADICIONAL LLAMADA Unnamed:, será eliminada
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        #Mover columna "Codigo GLN" al segundo lugar
        col = df.pop("Codigo GLN")
        df.insert(1, "Codigo GLN", col)
        #Crear y agregar columna Ruta, debe de ser la primera
        df['Ruta'] = "R" + df['NUR'].astype(str).str[-2:]
        col = df.pop("Ruta")
        df.insert(0, "Ruta", col)
        #Crear y agregar columna reev, debe ir después de Codigo GLN
        with motor.begin() as conn:
            #obtener catalogos de reev, visitable etpm y visitable merch solo trayendo la columna de REEEV
            sql_query="""
                SELECT Ejecutivo, Codigo_REEV
                FROM CATALOGOS.REEV    
            """
            result1 = conn.execute(text(sql_query))
            df_reev = pd.DataFrame(result1.fetchall(),columns=['Cliente', 'REEV'])
            
            sql_query2="""
                SELECT Codigo_ISMS
                FROM CATALOGOS.Visitable_ETPM    
            """
            result2 = conn.execute(text(sql_query2))
            df_etpm = pd.DataFrame(result2.fetchall(),columns=['Codigo_ISMS'])
            
            sql_query3="""
                SELECT Codigo_REEV
                FROM CATALOGOS.UX_Merch    
            """
            result3 = conn.execute(text(sql_query3))
            df_merch = pd.DataFrame(result3.fetchall(),columns=['Codigo_REEV'])

        #aplicar normalización de texto a los df
        #df=df.applymap(normalizar_texto)#normalizar texto del df principal
        df_reev = df_reev.applymap(normalizar_texto)
        df_etpm = df_etpm.applymap(normalizar_texto)
        df_merch = df_merch.applymap(normalizar_texto)
        #rellenar espacios vacios en los codigos de clientes que tienen menos de 10 caracteres
        

        df_reev['Cliente'] = (
            df_reev['Cliente']
                .astype(str)
                .str.strip()
                .str.zfill(10)
        )
        df_etpm['Codigo_ISMS'] = (
            df_etpm['Codigo_ISMS']
                .astype(str)
                .str.strip()
                .str.zfill(10)
        )
        #hacer mergeS con ux(df) para traer la columna de codigo reev, codigo isms, tipo de credito y linea de credito
        df = (
            df
            .merge(df_reev, left_on='Codigo GLN', right_on='Cliente', how='left')
            .drop(columns=['Cliente'])
            .merge(df_etpm, left_on='Codigo GLN', right_on='Codigo_ISMS', how='left')
            #.drop(columns=['Codigo_ISMS'])
            .merge(df_merch, left_on='REEV', right_on='Codigo_REEV', how='left')
            .drop(columns=['Codigo_REEV'])
            .merge(df2_completo, left_on='Codigo GLN', right_on='Agenciadf2', how='left')
            .drop(columns=['Agenciadf2'])
        )

        #borrar columnas resultantes del merge y la repetida de df_reev "Cliente"
        #insertar columna REEV despues de Codigo GLN
        col = df.pop("REEV")
        df.insert(2, "REEV", col)
        #columna visitable_etpm: si la columna Codigo_ISMS no es na => 1, si no = 0
        df['visitable_etpm'] = df['Codigo_ISMS'].notna().astype(int)
        col = df.pop("visitable_etpm")
        df.insert(3, "visitable_etpm", col)
        df = df.drop(columns=['Codigo_ISMS'])
        #columna visitable_merch: si la columna REEV no es na => 1, si no = 0
        df['visitable_merch'] = df['REEV'].notna().astype(int)
        col = df.pop("visitable_merch")
        df.insert(4, "visitable_merch", col)
        #acomodar columnas tipo_de_credito y linea despues de la columna visitable_merch (indice 5)
        col = df.pop("tipo_de_credito")
        df.insert(5, "tipo_de_credito", col)
        col=df.pop("linea")
        df.insert(6,"linea",col)
        #reacomodar ultimas columnas
        col = df.pop("Codigo GLN")
        df.insert(1, "Codigo GLN", col)
        col = df.pop("distribuidor")
        df.insert(7, "distribuidor", col)
            

        #eliminar columna "correoelectronico", está de más
        df = df.drop(columns=['correoelectronico'])

        # Ruta absoluta en Windows para guardar pruebas de df
        #ruta_salida = r"C:\Users\Usuario\Downloads\resultado.xlsx"
        #Escribir a Excel para revisar resultados
        #df.to_excel(ruta_salida, index=False)
        #print(f"Archivo guardado en: {ruta_salida}")
        
        #conectar a SQL y subir datos
        #probar que la conexión sea exitosa e insertar datos
        #también verifica si los datos con la fecha ya existen
        with motor.begin() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexión exitosa:", result.scalar())

            # ✓ Obtener columnas reales de SQL, EXCLUYENDO LA COLUMNA ID
            sql_column_query = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'PowerStreet' 
                AND TABLE_NAME = 'UX'
                AND COLUMNPROPERTY(OBJECT_ID('PowerStreet.UX'), COLUMN_NAME, 'IsIdentity') = 0
                ORDER BY ORDINAL_POSITION;
            """)
            sql_column_result = conn.execute(sql_column_query).fetchall()
            sql_columns = [row[0] for row in sql_column_result]

            if len(df.columns) != len(sql_columns):
                raise ValueError(f"❌ El DataFrame tiene {len(df.columns)} columnas "
                                f"pero la tabla SQL tiene {len(sql_columns)}.")

            df.columns = sql_columns
            print("✅ Columnas renombradas correctamente.")

            #eliminar clientes duplicados
            sql_delete_duplicados_ux = text("""
                DELETE FROM PowerStreet.UX
                WHERE Codigo_GLN IN (
                    SELECT Codigo_GLN
                    FROM (
                        SELECT Codigo_GLN,
                            ROW_NUMBER() OVER (PARTITION BY Codigo_GLN ORDER BY (SELECT NULL)) AS rn
                        FROM PowerStreet.UX
                    ) AS sub
                    WHERE sub.rn >= 1
                )
            """)
            # Ejecutar la eliminación
            result = conn.execute(sql_delete_duplicados_ux)
            print(f"✅ Se eliminaron {result.rowcount if result.rowcount != -1 else 'un número desconocido de'} registros duplicados por Codigo_GLN.")
            conn.execute(text("TRUNCATE TABLE PowerStreet.UX"))#reiniciar conteo de columna id 
            df.to_sql(
                name='UX',
                con=conn,
                schema='PowerStreet',
                if_exists='append',
                index=False,
                chunksize=500
            )
            print("✅ Datos insertados correctamente.")