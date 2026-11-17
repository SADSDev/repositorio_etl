#----------------------------------------
#LIBRERIAS
#----------------------------------------
import asyncio
from datetime import datetime
import time as time_module
from playwright.async_api import async_playwright

#----------------------------------------
#IMPORTS
#----------------------------------------
#configuraciones
import PowerStreet_ETL.configuraciones.entorno


from PowerStreet_ETL.configuraciones.parametros import schema
from PowerStreet_ETL.core.navegador import carga_pagina

from PowerStreet_ETL.diario.diarios_por_dia.procesos.libros import (
    libros_descarga,
    libros_carga_sql
)

from PowerStreet_ETL.diario.diarios_por_dia.procesos.universo_clientes import (
    universo_descarga,
    universo_carga_sql
)

from PowerStreet_ETL.core.logger import (
    configurar_logger,
    obtener_error_resumido
)
#-------------------------------------------
# INCIALIZACIONES
#------------------------------------------
logger=configurar_logger()

#-----------------------------------
#PROCESO
#-----------------------------------

async def main(fecha_hoy):
    #descarga de datos de PowerStreet
    logger.info(f"\n>>> DESCARGANDO datos al día "f"para {fecha_hoy}")
    async with async_playwright() as p:
        new_page, browser, context = await carga_pagina(p,headless=True)
        try:

            logger.info("Descargando Libro de rutas...")
            df_libros = await libros_descarga(new_page,fecha_hoy)

            logger.info("Descargando Universo de Clientes...")
            df_universo = await universo_descarga(new_page,fecha_hoy)
        finally:
            await browser.close()
    logger.info("\n>>> DESCARGA de archivos completa.")

    #carga de datos a SQL
    logger.info("\n>>> CARGANDO datos en SQL...")
    libros_carga_sql(df=df_libros,schema=schema,tabla="POWERSTREET_Libros")
    universo_carga_sql(df=df_universo,schema=schema,tabla="POWERSTREET_Universo_Clientes")
    logger.info("\n>>> CARGA terminada correctamente.")
    logger.info(f">>> PROCESO FINALIZADO | Fecha: {fecha_hoy}")


if __name__ == "__main__":
    max_intentos=3
    intento=1
    segundos_para_reintento=60
    fecha_hoy = datetime.today().strftime("%d-%m-%Y")
    while intento <= max_intentos:
        try:
            asyncio.run(main(fecha_hoy))
        
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
