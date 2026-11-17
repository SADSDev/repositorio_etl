#----------------------------------------
#LIBRERIAS
#----------------------------------------
import asyncio
import time as time_module
from datetime import datetime, timedelta, time
from playwright.async_api import async_playwright
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from PowerStreet_ETL.configuraciones.conexion_sql import motor
from PowerStreet_ETL.configuraciones.parametros import schema
import PowerStreet_ETL.configuraciones.entorno
from PowerStreet_ETL.core.logger import (
    configurar_logger,
    obtener_error_resumido
)

from PowerStreet_ETL.core.navegador import carga_pagina
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.ventas_diarias import(
    ventas_descarga, ventas_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.seguimiento_indicadores import(
    indicadores_descarga, indicadores_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.combos_por_cliente import(
    combos_por_cliente_descarga, combos_por_cliente_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.fullfillment_pedidos_pmm import(
    fullfillment_pedidos_descarga, fullfillment_pedidos_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.ito_consolidado import(
    ito_consolidado_descarga, ito_consolidado_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.ito_detallado import(
    ito_detallado_descarga, ito_detallado_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.pdv_por_agencia import(
    pdv_agencia_descarga, pdv_agencia_carga_sql
)
from PowerStreet_ETL.diario.diarios_frecuentes.procesos.encuestas_supervisor import(
    encuestas_supervisor_descarga, encuestas_supervisor_carga_sql
)
#---------------------------------------------
# INICIALIZACIONES
#---------------------------------------------
logger = configurar_logger()

#-----------------------------------
#PROCESO
#-----------------------------------

#definicion de main
async def main(fecha_hoy):

    logger.info(f"\n>>> DESCARGANDO datos "f"para {fecha_hoy}")

    async with async_playwright() as p:

        new_page, browser, context = await carga_pagina(p,headless=True)
        try:

            logger.info("decargando venta diaria...")
            df_venta=await ventas_descarga(new_page, fecha_hoy)

            logger.info("descargando indicadores...")
            df_indicadores=await indicadores_descarga(new_page,fecha_hoy)

            logger.info("descargando combos por Clciente")
            df_combos=await combos_por_cliente_descarga(new_page, fecha_hoy)

            logger.info("ejecuntando pedidos pmm...")
            df_pedidos=await fullfillment_pedidos_descarga(new_page, fecha_hoy)

            logger.info("descargando ito consolidado...")
            df_ito_conso=await ito_consolidado_descarga(new_page, fecha_hoy)

            logger.info("descargando ito detallado...")
            df_ito_detalle=await ito_detallado_descarga(new_page, fecha_hoy)

            logger.info("descargado pdv por agencia...")
            df_pdv_agencia=await pdv_agencia_descarga(new_page, fecha_hoy)

            logger.info("descargando encustas de supervisores...")
            df_encuestas_supervisor=await encuestas_supervisor_descarga(new_page, fecha_hoy)

        finally:
            await browser.close()
    logger.info("\n>>> DESCARGA de archivos completa.")
    
    #subida de datos 
    logger.info("\n>>> CARGANDO datos en SQL...")
    lista_reportes=[
        {"carga_sql":ventas_carga_sql, "df":df_venta, "tabla":"POWERSTREET_Venta_Diaria"},
        {"carga_sql":indicadores_carga_sql, "df":df_indicadores, "tabla":"POWERSTREET_Seguimiento_Indicadores"},
        {"carga_sql":combos_por_cliente_carga_sql, "df":df_combos, "tabla":"POWERSTREET_Combos_Por_Cliente"},
        {"carga_sql":fullfillment_pedidos_carga_sql, "df":df_pedidos, "tabla":"POWERSTREET_Fullfillment_Pedidos_PMM"},
        {"carga_sql":ito_consolidado_carga_sql, "df":df_ito_conso, "tabla":"POWERSTREET_ITO_Consolidado"},
        {"carga_sql":ito_detallado_carga_sql, "df":df_ito_detalle, "tabla":"POWERSTREET_ITO_Detallado"},
        {"carga_sql":pdv_agencia_carga_sql, "df":df_pdv_agencia, "tabla":"POWERSTREET_PDV_PorAgencia"},
        {"carga_sql":encuestas_supervisor_carga_sql, "df":df_encuestas_supervisor, "tabla":"POWERSTREET_Encuestas_Supervisores"}
    ]
    for reporte in lista_reportes:
        carga_sql = reporte["carga_sql"]
        df = reporte["df"]
        tabla = reporte["tabla"]

        if df is None or df.empty:
            logger.info(f"{tabla}: sin datos, continuando con el siguiente proceso...")
            continue

        logger.info(f"Cargando {tabla} a SQL...")
        carga_sql(df=df,schema=schema,tabla=tabla)
        logger.info("Datos cargados")

    

# obtener la ultima fecha con registros en sql
def obtener_ultima_fecha_sql(schema:str):

    with motor.begin() as conn:
        ultima_fecha_texto = text(f"""
            SELECT MIN(Fecha_Maxima) AS Menor_Fecha_Reciente
            FROM (
                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Venta_Diaria

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Seguimiento_Indicadores

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Combos_Por_Cliente

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Fullfillment_Pedidos_PMM

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_ITO_Consolidado

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_ITO_Detallado

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_PDV_PorAgencia

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Encuestas_Supervisores
                
            ) AS fechas_maximas;
        """)

        resultado = conn.execute(ultima_fecha_texto)

        return resultado.scalar()
    
#ejecución del programa principal
if __name__ == "__main__":
    segundos_para_reintento=60 #segundos para reintentar entre fallos
    intento=1
    max_intentos=3


    #3 intentos maximo en total contando el incial
    while intento <= max_intentos:
        try:
            ultima_fecha_sql = obtener_ultima_fecha_sql(schema=schema)

            logger.info(
                f"La última fecha de registro en SQL fue el "
                f"{ultima_fecha_sql}"
            )

            fecha_hoy_obj = datetime.today().date()
            if (ultima_fecha_sql and fecha_hoy_obj > ultima_fecha_sql):

                logger.info(
                    f"Hoy es {fecha_hoy_obj} y el último registro "
                    f"en SQL es del {ultima_fecha_sql}"
                )

                logger.info(
                    f"Se iniciará carga de datos desde "
                    f"{ultima_fecha_sql} hasta {fecha_hoy_obj}"
                )

                current_date = ultima_fecha_sql

                while current_date <= fecha_hoy_obj:

                    fecha_formateada = current_date.strftime(
                        "%d-%m-%Y"
                    )

                    print(
                        f"\nProcesando fecha: "
                        f"{fecha_formateada}"
                    )

                    asyncio.run(
                        main(fecha_formateada)
                    )

                    current_date += timedelta(days=1)

            else:
                
                logger.info("No hay fechas nuevas para procesar")
                fecha_hoy_str = (fecha_hoy_obj.strftime("%d-%m-%Y"))
                asyncio.run(main(fecha_hoy_str))
            
            logger.info("Proceso finalizado correctamente")
            break

            
        except Exception as error:

            if intento == max_intentos:
                logger.critical(
                    f"Se alcanzó el máximo de {max_intentos} intentos. "
                    "Proceso terminado con errores."
                )
                raise

            logger.error(
                "Intento %s/%s fallido. Reintentando en %s segundos: %s",
                intento,
                max_intentos,
                segundos_para_reintento,
                obtener_error_resumido(error),
                exc_info=True
            )

            intento += 1
            time_module.sleep(segundos_para_reintento)

   
